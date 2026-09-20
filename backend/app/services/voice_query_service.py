"""Voice Query Application Service.

Coordinates:
Audio input
→ Speech-to-Text (SpeechToTextPort)
→ Intent Classification (VoiceIntentService)
→ Presisted Prescription DB lookup (PrescriptionRepository)
→ Safety Evaluation (fail-closed if REQUIRES_REVIEW)
→ Deterministic Localization (LocalizationPort)
→ Text-to-Speech (TTSProvider)
→ Response Contract
"""

import base64
import logging

from app.db.models import PrescriptionStatus
from app.ports.localization import CanonicalMedicationFact, LocalizationPort
from app.ports.stt import SpeechToTextPort
from app.ports.tts import TTSProvider
from app.repositories.prescription_repository import PrescriptionRepository
from app.schemas.voice import VoiceQueryResponse, VoiceQueryResultState
from app.services.voice_intent import VoiceIntentService, VoiceIntentType

logger = logging.getLogger("medication_accessibility.voice_service")


class PrescriptionNotFoundError(Exception):
    """Raised when the specified prescription ID does not exist."""


class VoiceQueryService:
    """Orchestrates end-to-end voice posology inquiries."""

    def __init__(
        self,
        stt_port: SpeechToTextPort,
        intent_service: VoiceIntentService,
        localization_port: LocalizationPort,
        tts_provider: TTSProvider,
        repository: PrescriptionRepository,
    ) -> None:
        self.stt = stt_port
        self.intent_service = intent_service
        self.localization = localization_port
        self.tts = tts_provider
        self.repo = repository

    async def execute_voice_query(
        self,
        prescription_id: str,
        audio_bytes: bytes,
        mime_type: str,
        language: str = "en-IN",
        request_id: str = "",
    ) -> VoiceQueryResponse:
        """Process spoken patient audio query against persisted prescription record."""
        # 1. Fetch prescription from repository
        prescription = await self.repo.get_by_id(prescription_id)
        if not prescription:
            raise PrescriptionNotFoundError(f"Prescription '{prescription_id}' not found.")

        # 2. Extract drug names to inform intent recognition
        known_drug_names = [m.drug_name for m in prescription.medications if m.drug_name]

        # 3. Transcribe speech audio
        stt_result = await self.stt.transcribe_audio(
            audio_bytes=audio_bytes,
            mime_type=mime_type,
            language_code=language,
        )
        transcript_text = stt_result.text

        # 4. Classify intent to understand query semantics
        intent_res = self.intent_service.classify_intent(
            query_text=transcript_text,
            known_drug_names=known_drug_names,
        )

        # 5. Fail closed if prescription was explicitly marked as failed
        if prescription.status == PrescriptionStatus.FAILED:
            logger.warning(
                "Prescription %s is FAILED - refusing voice query disclosure.",
                prescription_id,
                extra={"request_id": request_id},
            )
            safety_refusal_msg = self.localization.get_intent_safety_refusal_message(
                intent=intent_res.intent,
                language=language,
            )
            audio_b64 = None
            try:
                tts_res = await self.tts.synthesize(text=safety_refusal_msg, language=language)
                audio_b64 = base64.b64encode(tts_res.audio_bytes).decode("ascii")
            except Exception as e:
                logger.error("TTS synthesis failed for review message: %s", str(e))

            return VoiceQueryResponse(
                success=False,
                request_id=request_id,
                prescription_id=prescription_id,
                transcript=transcript_text,
                intent=intent_res.intent.value,
                target_drug=intent_res.target_drug,
                response_text=safety_refusal_msg,
                audio_base64=audio_b64,
                language=language,
                requires_review=True,
                result_state=VoiceQueryResultState.PRESCRIPTION_REQUIRES_REVIEW,
                safety_reasons=["Prescription REJECTED_UNSAFE; posology withheld"],
            )

        # 6. Handle unsupported/unknown intent
        if intent_res.intent == VoiceIntentType.UNKNOWN:
            unsupported_msg = self.localization.get_unsupported_intent_message(language)
            audio_b64 = None
            try:
                tts_res = await self.tts.synthesize(text=unsupported_msg, language=language)
                audio_b64 = base64.b64encode(tts_res.audio_bytes).decode("ascii")
            except Exception as e:
                logger.error("TTS synthesis failed for unsupported intent: %s", str(e))

            return VoiceQueryResponse(
                success=False,
                request_id=request_id,
                prescription_id=prescription_id,
                transcript=transcript_text,
                intent=intent_res.intent.value,
                target_drug=intent_res.target_drug,
                response_text=unsupported_msg,
                audio_base64=audio_b64,
                language=language,
                requires_review=prescription.status == PrescriptionStatus.REQUIRES_REVIEW,
                result_state=VoiceQueryResultState.NO_CONFIRMED_MATCH,
                safety_reasons=["Unsupported voice query intent"],
            )

        # 7. Map all medications to CanonicalMedicationFact
        all_facts: list[CanonicalMedicationFact] = []
        for m in prescription.medications:
            name = m.drug_name or m.raw_drug_name
            if not name:
                continue
            is_safe = bool(m.is_verified_safe and not m.requires_review)
            needs_review = bool(m.requires_review or not m.is_verified_safe)
            all_facts.append(
                CanonicalMedicationFact(
                    drug_name=name,
                    strength_value=m.strength_value,
                    strength_unit=m.strength_unit,
                    dose_value=m.dose_value,
                    dose_unit=m.dose_unit,
                    morning=m.morning,
                    afternoon=m.afternoon,
                    evening=m.evening,
                    night=m.night,
                    is_as_needed_sos=m.is_as_needed_sos,
                    before_meal=m.before_meal,
                    after_meal=m.after_meal,
                    duration_value=m.duration_value,
                    duration_unit=m.duration_unit,
                    is_verified_safe=is_safe,
                    requires_review=needs_review,
                )
            )

        # 8. Filter facts matching the specific clinical intent
        def _matches_intent(f: CanonicalMedicationFact) -> bool:
            if intent_res.intent == VoiceIntentType.NIGHT_MEDICINE:
                return f.night is True
            if intent_res.intent == VoiceIntentType.MORNING_MEDICINE:
                return f.morning is True
            if intent_res.intent == VoiceIntentType.BEFORE_FOOD:
                return f.before_meal is True
            if intent_res.intent == VoiceIntentType.AFTER_FOOD:
                return f.after_meal is True
            if intent_res.intent in (
                VoiceIntentType.DURATION,
                VoiceIntentType.LIST_MEDICATIONS,
                VoiceIntentType.SCHEDULE,
            ):
                return True
            if intent_res.intent == VoiceIntentType.SPECIFIC_DRUG:
                if intent_res.target_drug:
                    return f.drug_name.lower() == intent_res.target_drug.lower()
                return True
            return False

        matching_facts = [f for f in all_facts if _matches_intent(f)]
        verified_matches = [
            f for f in matching_facts if f.is_verified_safe and not f.requires_review
        ]
        unverified_matches = [
            f for f in matching_facts if f.requires_review or not f.is_verified_safe
        ]

        # 9. Granular Safety Disclosure Classification (Option 3)
        has_only_unknown_names = bool(
            unverified_matches
            and all(
                f.drug_name.strip().lower() in ("unknowndrug", "unknown", "unknown medication")
                for f in unverified_matches
            )
        )

        if not verified_matches and (
            intent_res.intent == VoiceIntentType.LIST_MEDICATIONS or has_only_unknown_names
        ):
            result_state = VoiceQueryResultState.PRESCRIPTION_REQUIRES_REVIEW
            success = False
            requires_review = True
            safety_reasons = ["Prescription contains unverified posology; safety refusal enforced"]
            response_text = self.localization.get_intent_safety_refusal_message(
                intent=intent_res.intent,
                language=language,
            )
        elif verified_matches and not unverified_matches:
            result_state = VoiceQueryResultState.CONFIRMED_MATCH
            success = True
            requires_review = False
            safety_reasons = []
            response_text = self.localization.format_granular_intent_response(
                intent=intent_res.intent,
                verified_facts=verified_matches,
                unverified_facts=[],
                language=language,
                target_drug=intent_res.target_drug,
            )
        elif verified_matches and unverified_matches:
            result_state = VoiceQueryResultState.PARTIAL_CONFIRMED_MATCH
            success = True
            requires_review = True
            safety_reasons = [
                f"{f.drug_name}: posology unverified; pharmacist review required"
                for f in unverified_matches
            ]
            response_text = self.localization.format_granular_intent_response(
                intent=intent_res.intent,
                verified_facts=verified_matches,
                unverified_facts=unverified_matches,
                language=language,
                target_drug=intent_res.target_drug,
            )
        elif not verified_matches and unverified_matches:
            result_state = VoiceQueryResultState.PRESCRIPTION_REQUIRES_REVIEW
            success = False
            requires_review = True
            safety_reasons = [
                f"{f.drug_name}: posology unverified; pharmacist review required"
                for f in unverified_matches
            ]
            response_text = self.localization.format_granular_intent_response(
                intent=intent_res.intent,
                verified_facts=[],
                unverified_facts=unverified_matches,
                language=language,
                target_drug=intent_res.target_drug,
            )
        else:
            # Neither verified nor unverified matches for this specific intent
            if prescription.status == PrescriptionStatus.REQUIRES_REVIEW:
                result_state = VoiceQueryResultState.PRESCRIPTION_REQUIRES_REVIEW
                success = False
                requires_review = True
                safety_reasons = [
                    "Prescription contains unverified posology; safety refusal enforced"
                ]
                response_text = self.localization.get_intent_safety_refusal_message(
                    intent=intent_res.intent,
                    language=language,
                )
            else:
                result_state = VoiceQueryResultState.NO_CONFIRMED_MATCH
                success = True
                requires_review = False
                safety_reasons = []
                response_text = self.localization.format_granular_intent_response(
                    intent=intent_res.intent,
                    verified_facts=[],
                    unverified_facts=[],
                    language=language,
                    target_drug=intent_res.target_drug,
                )

        # 11. Synthesize speech (gracefully fall back if TTS fails)
        audio_b64 = None
        try:
            tts_res = await self.tts.synthesize(text=response_text, language=language)
            audio_b64 = base64.b64encode(tts_res.audio_bytes).decode("ascii")
        except Exception as e:
            logger.error("TTS synthesis failed for query response: %s", str(e))

        return VoiceQueryResponse(
            success=success,
            request_id=request_id,
            prescription_id=prescription_id,
            transcript=transcript_text,
            intent=intent_res.intent.value,
            target_drug=intent_res.target_drug,
            response_text=response_text,
            audio_base64=audio_b64,
            language=language,
            requires_review=requires_review,
            result_state=result_state,
            safety_reasons=safety_reasons,
        )
