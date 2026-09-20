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
from app.schemas.voice import VoiceQueryResponse
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

        # 4. Deterministic safety check on prescription status
        # If prescription requires review or failed, refuse to disclose posology facts
        if prescription.status != PrescriptionStatus.COMPLETED:
            logger.warning(
                "Prescription %s has status %s - refusing voice query disclosure.",
                prescription_id,
                prescription.status,
                extra={"request_id": request_id},
            )
            review_msg = self.localization.get_review_required_message(language)

            audio_b64 = None
            try:
                tts_res = await self.tts.synthesize(text=review_msg, language=language)
                audio_b64 = base64.b64encode(tts_res.audio_bytes).decode("ascii")
            except Exception as e:
                logger.error("TTS synthesis failed for review message: %s", str(e))

            return VoiceQueryResponse(
                success=False,
                request_id=request_id,
                prescription_id=prescription_id,
                transcript=transcript_text,
                intent=VoiceIntentType.UNKNOWN,
                target_drug=None,
                response_text=review_msg,
                audio_base64=audio_b64,
                language=language,
                requires_review=True,
                safety_reasons=[f"Prescription status is {prescription.status} (requires review)"],
            )

        # 5. Classify intent
        intent_res = self.intent_service.classify_intent(
            query_text=transcript_text,
            known_drug_names=known_drug_names,
        )

        # 6. Map medications to CanonicalMedicationFact
        facts: list[CanonicalMedicationFact] = []
        for m in prescription.medications:
            if not m.drug_name or not m.is_verified_safe:
                continue
            facts.append(
                CanonicalMedicationFact(
                    drug_name=m.drug_name,
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
                    is_verified_safe=m.is_verified_safe,
                )
            )

        # 7. Generate localized response text
        response_text = self.localization.format_intent_response(
            intent=intent_res.intent,
            facts=facts,
            language=language,
            target_drug=intent_res.target_drug,
        )

        # 8. Synthesize speech (gracefully fall back if TTS fails)
        audio_b64 = None
        try:
            tts_res = await self.tts.synthesize(text=response_text, language=language)
            audio_b64 = base64.b64encode(tts_res.audio_bytes).decode("ascii")
        except Exception as e:
            logger.error("TTS synthesis failed for query response: %s", str(e))

        return VoiceQueryResponse(
            success=True,
            request_id=request_id,
            prescription_id=prescription_id,
            transcript=transcript_text,
            intent=intent_res.intent,
            target_drug=intent_res.target_drug,
            response_text=response_text,
            audio_base64=audio_b64,
            language=language,
            requires_review=False,
            safety_reasons=[],
        )
