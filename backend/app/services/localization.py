"""Deterministic Template-Based Localization Service.

Implements LocalizationPort. Formats canonical medication facts into
localized clinical responses for English, Hindi, and Kannada without LLM hallucinations.
"""

from app.ports.localization import CanonicalMedicationFact, LocalizationPort
from app.services.voice_intent import VoiceIntentType


def _format_dose_str(val: float | None, unit: str | None, default: str = "") -> str:
    if val is None:
        return default
    val_str = f"{val:g}"
    if unit:
        return f"{val_str} {unit}"
    return val_str


def _format_strength_str(val: float | None, unit: str | None) -> str:
    if val is None:
        return ""
    val_str = f"{val:g}"
    if unit:
        return f"{val_str}{unit}"
    return val_str


def _get_slot_phrase(intent: VoiceIntentType, lang: str) -> str:
    if "hi" in lang:
        if intent == VoiceIntentType.NIGHT_MEDICINE:
            return "रात के लिए"
        if intent == VoiceIntentType.MORNING_MEDICINE:
            return "सुबह के लिए"
        if intent == VoiceIntentType.BEFORE_FOOD:
            return "खाने से पहले के लिए"
        if intent == VoiceIntentType.AFTER_FOOD:
            return "खाने के बाद के लिए"
        return "इस समय के लिए"
    if "kn" in lang:
        if intent == VoiceIntentType.NIGHT_MEDICINE:
            return "ರಾತ್ರಿಗೆ"
        if intent == VoiceIntentType.MORNING_MEDICINE:
            return "ಬೆಳಿಗ್ಗೆಗೆ"
        if intent == VoiceIntentType.BEFORE_FOOD:
            return "ಊಟಕ್ಕೆ ಮುಂಚೆ"
        if intent == VoiceIntentType.AFTER_FOOD:
            return "ಊಟದ ನಂತರ"
        return "ಈ ವೇಳಾಪಟ್ಟಿಗೆ"
    if intent == VoiceIntentType.NIGHT_MEDICINE:
        return "for the night"
    if intent == VoiceIntentType.MORNING_MEDICINE:
        return "for the morning"
    if intent == VoiceIntentType.BEFORE_FOOD:
        return "before food"
    if intent == VoiceIntentType.AFTER_FOOD:
        return "after food"
    return "for this schedule"


class TemplateLocalizationService(LocalizationPort):
    """Deterministic template localization engine."""

    def get_review_required_message(self, language: str = "en-IN") -> str:
        lang = language.lower().strip()
        if "hi" in lang:
            return (
                "इस पर्चे में कुछ जानकारी स्पष्ट नहीं है। "
                "कृपया सुरक्षित उपयोग के लिए अपने फार्मासिस्ट या डॉक्टर से संपर्क करें।"
            )
        if "kn" in lang:
            return "ಈ ಚೀಟಿಯಲ್ಲಿರುವ ಕೆಲವು ಮಾಹಿತಿಗಳು ಅಸ್ಪಷ್ಟವಾಗಿವೆ. ದಯವಿಟ್ಟು ನಿಮ್ಮ ವೈದ್ಯರು ಅಥವಾ ಔಷಧ ತಜ್ಞರನ್ನು ಸಂಪರ್ಕಿಸಿ."
        return (
            "This prescription contains unclear details. "
            "Please consult your pharmacist or doctor for verified guidance."
        )

    def get_intent_safety_refusal_message(
        self,
        intent: VoiceIntentType,
        language: str = "en-IN",
    ) -> str:
        lang = language.lower().strip()
        if "hi" in lang:
            if intent == VoiceIntentType.NIGHT_MEDICINE:
                return (
                    "मैं इस पर्चे से रात की दवा की सुरक्षित पुष्टि नहीं कर सकता। "
                    "कृपया फार्मासिस्ट से इसकी पुष्टि करें।"
                )
            if intent == VoiceIntentType.MORNING_MEDICINE:
                return (
                    "मैं इस पर्चे से सुबह की दवा की सुरक्षित पुष्टि नहीं कर सकता। "
                    "कृपया फार्मासिस्ट से इसकी पुष्टि करें।"
                )
            if intent == VoiceIntentType.BEFORE_FOOD:
                return (
                    "मैं इस पर्चे से खाने से पहले की दवा की सुरक्षित पुष्टि नहीं कर सकता। "
                    "कृपया फार्मासिस्ट से इसकी पुष्टि करें।"
                )
            if intent == VoiceIntentType.AFTER_FOOD:
                return (
                    "मैं इस पर्चे से खाने के बाद की दवा की सुरक्षित पुष्टि नहीं कर सकता। "
                    "कृपया फार्मासिस्ट से इसकी पुष्टि करें।"
                )
            if intent == VoiceIntentType.DURATION:
                return (
                    "मैं इस पर्चे से दवा की अवधि की सुरक्षित पुष्टि नहीं कर सकता। "
                    "कृपया फार्मासिस्ट से इसकी पुष्टि करें।"
                )
            return "मैं इस पर्चे से दवाओं की सुरक्षित पुष्टि नहीं कर सकता। कृपया फार्मासिस्ट से इसकी पुष्टि करें।"

        if "kn" in lang:
            if intent == VoiceIntentType.NIGHT_MEDICINE:
                return (
                    "ಈ ಚೀಟಿಯಿಂದ ರಾತ್ರಿಯ ಔಷಧಿಯನ್ನು ನಾನು ಸುರಕ್ಷಿತವಾಗಿ ದೃಢೀಕರಿಸಲು ಸಾಧ್ಯವಿಲ್ಲ. "
                    "ದಯವಿಟ್ಟು ಔಷಧಿಕಾರರೊಂದಿಗೆ ಪರಿಶೀಲಿಸಿ."
                )
            if intent == VoiceIntentType.MORNING_MEDICINE:
                return (
                    "ಈ ಚೀಟಿಯಿಂದ ಬೆಳಗಿನ ಔಷಧಿಯನ್ನು ನಾನು ಸುರಕ್ಷಿತವಾಗಿ ದೃಢೀಕರಿಸಲು ಸಾಧ್ಯವಿಲ್ಲ. ದಯವಿಟ್ಟು ಔಷಧಿಕಾರರೊಂದಿಗೆ ಪರಿಶೀಲಿಸಿ."
                )
            if intent == VoiceIntentType.BEFORE_FOOD:
                return (
                    "ಈ ಚೀಟಿಯಿಂದ ಊಟಕ್ಕೆ ಮುಂಚಿನ ಔಷಧಿಯನ್ನು ನಾನು ಸುರಕ್ಷಿತವಾಗಿ ದೃಢೀಕರಿಸಲು ಸಾಧ್ಯವಿಲ್ಲ. "
                    "ದಯವಿಟ್ಟು ಔಷಧಿಕಾರರೊಂದಿಗೆ ಪರಿಶೀಲಿಸಿ."
                )
            if intent == VoiceIntentType.AFTER_FOOD:
                return (
                    "ಈ ಚೀಟಿಯಿಂದ ಊಟದ ನಂತರದ ಔಷಧಿಯನ್ನು ನಾನು ಸುರಕ್ಷಿತವಾಗಿ ದೃಢೀಕರಿಸಲು ಸಾಧ್ಯವಿಲ್ಲ. "
                    "ದಯವಿಟ್ಟು ಔಷಧಿಕಾರರೊಂದಿಗೆ ಪರಿಶೀಲಿಸಿ."
                )
            if intent == VoiceIntentType.DURATION:
                return (
                    "ಈ ಚೀಟಿಯಿಂದ ಔಷಧಿಯ ಅವಧಿಯನ್ನು ನಾನು ಸುರಕ್ಷಿತವಾಗಿ ದೃಢೀಕರಿಸಲು ಸಾಧ್ಯವಿಲ್ಲ. ದಯವಿಟ್ಟು ಔಷಧಿಕಾರರೊಂದಿಗೆ ಪರಿಶೀಲಿಸಿ."
                )
            return "ಈ ಚೀಟಿಯಿಂದ ಔಷಧಿಗಳನ್ನು ನಾನು ಸುರಕ್ಷಿತವಾಗಿ ದೃಢೀಕರಿಸಲು ಸಾಧ್ಯವಿಲ್ಲ. ದಯವಿಟ್ಟು ಔಷಧಿಕಾರರೊಂದಿಗೆ ಪರಿಶೀಲಿಸಿ."

        # Default: English
        if intent == VoiceIntentType.NIGHT_MEDICINE:
            return (
                "I can't safely confirm the nighttime medicine from this prescription. "
                "Please verify it with a pharmacist."
            )
        if intent == VoiceIntentType.MORNING_MEDICINE:
            return (
                "I can't safely confirm the morning medicine from this prescription. "
                "Please verify it with a pharmacist."
            )
        if intent == VoiceIntentType.BEFORE_FOOD:
            return (
                "I can't safely confirm before-food medicine from this prescription. "
                "Please verify it with a pharmacist."
            )
        if intent == VoiceIntentType.AFTER_FOOD:
            return (
                "I can't safely confirm after-food medicine from this prescription. "
                "Please verify it with a pharmacist."
            )
        if intent == VoiceIntentType.DURATION:
            return (
                "I can't safely confirm the treatment duration from this prescription. "
                "Please verify it with a pharmacist."
            )
        return (
            "I can't safely confirm the medications from this prescription. "
            "Please verify them with a pharmacist."
        )

    def get_unsupported_intent_message(self, language: str = "en-IN") -> str:
        lang = language.lower().strip()
        if "hi" in lang:
            return "माफ़ कीजिये, आपके पर्चे में इस बारे में कोई निर्देश नहीं है। कृपया डॉक्टर से सलाह लें।"
        if "kn" in lang:
            return "ಕ್ಷಮಿಸಿ, ಈ ಬಗ್ಗೆ ವೈದ್ಯರ ಚೀಟಿಯಲ್ಲಿ ಯಾವುದೇ ಸೂಚನೆಗಳಿಲ್ಲ. ದಯವಿಟ್ಟು ವೈದ್ಯರನ್ನು ಸಂಪರ್ಕಿಸಿ."
        return (
            "I'm sorry, there are no specific instructions for that in your prescription. "
            "Please consult your doctor."
        )

    def format_granular_intent_response(
        self,
        intent: VoiceIntentType,
        verified_facts: list[CanonicalMedicationFact],
        unverified_facts: list[CanonicalMedicationFact],
        language: str = "en-IN",
        target_drug: str | None = None,
    ) -> str:
        lang = language.lower().strip()
        has_verified = len(verified_facts) > 0
        has_unverified = len(unverified_facts) > 0

        # Scenario 1: Both verified and unverified match (PARTIAL)
        if has_verified and has_unverified:
            if "hi" in lang:
                verified_text = self._format_hindi(intent, verified_facts, target_drug)
                unv_names = ", ".join(f.drug_name for f in unverified_facts)
                return (
                    f"{verified_text} ध्यान दें: {unv_names} भी लिखी है, "
                    "लेकिन इसके विवरण की पुष्टि नहीं हुई है; कृपया लेने से पहले फार्मासिस्ट से जांच कराएं।"
                )
            if "kn" in lang:
                verified_text = self._format_kannada(intent, verified_facts, target_drug)
                unv_names = ", ".join(f.drug_name for f in unverified_facts)
                return (
                    f"{verified_text} ಸೂಚನೆ: {unv_names} ಸಹ ನಿಗದಿಯಾಗಿದೆ, "
                    "ಆದರೆ ವಿವರಗಳು ದೃಢಪಟ್ಟಿಲ್ಲ; ತೆಗೆದುಕೊಳ್ಳುವ ಮುನ್ನ ಔಷಧಿಕಾರರೊಂದಿಗೆ ಪರಿಶೀಲಿಸಿ."
                )
            # Default English
            verified_text = self._format_english(intent, verified_facts, target_drug)
            unv_names = ", ".join(f.drug_name for f in unverified_facts)
            verb = "is" if len(unverified_facts) == 1 else "are"
            return (
                f"{verified_text} Note: {unv_names} {verb} also listed, "
                "but details are unverified—please confirm with a pharmacist before taking."
            )

        # Scenario 2: Verified only
        if has_verified and not has_unverified:
            return self.format_intent_response(intent, verified_facts, language, target_drug)

        # Scenario 3: Unverified only
        if not has_verified and has_unverified:
            unv_names = ", ".join(f.drug_name for f in unverified_facts)
            if "hi" in lang:
                slot = _get_slot_phrase(intent, "hi")
                return (
                    f"पर्चे में {slot} {unv_names} लिखी है, लेकिन इसके विवरण की पुष्टि नहीं हुई है। "
                    "कृपया लेने से पहले फार्मासिस्ट से जांच कराएं।"
                )
            if "kn" in lang:
                slot = _get_slot_phrase(intent, "kn")
                return (
                    f"ಚೀಟಿಯಲ್ಲಿ {slot} {unv_names} ಉಲ್ಲೇಖಿಸಲಾಗಿದೆ, ಆದರೆ ವಿವರಗಳು ದೃಢಪಟ್ಟಿಲ್ಲ. "
                    "ತೆಗೆದುಕೊಳ್ಳುವ ಮುನ್ನ ದಯವಿಟ್ಟು ಔಷಧಿಕಾರರೊಂದಿಗೆ ಪರಿಶೀಲಿಸಿ."
                )
            # Default English
            slot = _get_slot_phrase(intent, "en")
            return (
                f"The prescription lists {unv_names} {slot}, but posology details are unverified. "
                "Please verify with a pharmacist before taking."
            )

        # Scenario 4: Neither (No Match)
        if "hi" in lang:
            if intent == VoiceIntentType.NIGHT_MEDICINE:
                return "इस पर्चे पर रात के लिए कोई सत्यापित दवा निर्धारित नहीं है।"
            if intent == VoiceIntentType.MORNING_MEDICINE:
                return "इस पर्चे पर सुबह के लिए कोई सत्यापित दवा निर्धारित नहीं है।"
            if intent == VoiceIntentType.BEFORE_FOOD:
                return "इस पर्चे पर खाने से पहले लेने के लिए कोई सत्यापित दवा निर्धारित नहीं है।"
            if intent == VoiceIntentType.AFTER_FOOD:
                return "इस पर्चे पर खाने के बाद लेने के लिए कोई सत्यापित दवा निर्धारित नहीं है।"
            return "इस पर्चे में कोई सत्यापित दवा नहीं मिली।"

        if "kn" in lang:
            if intent == VoiceIntentType.NIGHT_MEDICINE:
                return "ಈ ಚೀಟಿಯಲ್ಲಿ ರಾತ್ರಿ ತೆಗೆದುಕೊಳ್ಳಲು ಯಾವುದೇ ದೃಢಪಡಿಸಿದ ಔಷಧಿ ನಿಗದಿಪಡಿಸಿಲ್ಲ."
            if intent == VoiceIntentType.MORNING_MEDICINE:
                return "ಈ ಚೀಟಿಯಲ್ಲಿ ಬೆಳಿಗ್ಗೆ ತೆಗೆದುಕೊಳ್ಳಲು ಯಾವುದೇ ದೃಢಪಡಿಸಿದ ಔಷಧಿ ನಿಗದಿಪಡಿಸಿಲ್ಲ."
            if intent == VoiceIntentType.BEFORE_FOOD:
                return "ಈ ಚೀಟಿಯಲ್ಲಿ ಊಟಕ್ಕೆ ಮುಂಚೆ ತೆಗೆದುಕೊಳ್ಳಲು ಯಾವುದೇ ದೃಢಪಡಿಸಿದ ಔಷಧಿ ನಿಗದಿಪಡಿಸಿಲ್ಲ."
            if intent == VoiceIntentType.AFTER_FOOD:
                return "ಈ ಚೀಟಿಯಲ್ಲಿ ಊಟದ ನಂತರ ತೆಗೆದುಕೊಳ್ಳಲು ಯಾವುದೇ ದೃಢಪಡಿಸಿದ ಔಷಧಿ ನಿಗದಿಪಡಿಸಿಲ್ಲ."
            return "ಈ ಚೀಟಿಯಲ್ಲಿ ಯಾವುದೇ ದೃಢಪಡಿಸಿದ ಔಷಧಿಗಳು ಕಂಡುಬಂದಿಲ್ಲ."

        # Default English
        if intent == VoiceIntentType.NIGHT_MEDICINE:
            return (
                "There are no confirmed medications scheduled for the night on this prescription."
            )
        if intent == VoiceIntentType.MORNING_MEDICINE:
            return (
                "There are no confirmed medications scheduled for the morning on this prescription."
            )
        if intent == VoiceIntentType.BEFORE_FOOD:
            return (
                "There are no confirmed medications marked to be taken before food "
                "on this prescription."
            )
        if intent == VoiceIntentType.AFTER_FOOD:
            return (
                "There are no confirmed medications marked to be taken after food "
                "on this prescription."
            )
        return "There are no confirmed medications found in this prescription."

    def format_intent_response(
        self,
        intent: VoiceIntentType,
        facts: list[CanonicalMedicationFact],
        language: str = "en-IN",
        target_drug: str | None = None,
    ) -> str:
        lang = language.lower().strip()
        if "hi" in lang:
            return self._format_hindi(intent, facts, target_drug)
        if "kn" in lang:
            return self._format_kannada(intent, facts, target_drug)
        return self._format_english(intent, facts, target_drug)

    # --------------------------------------------------------------------------
    # English Formatter
    # --------------------------------------------------------------------------
    def _format_english(
        self,
        intent: VoiceIntentType,
        facts: list[CanonicalMedicationFact],
        target_drug: str | None,
    ) -> str:
        if not facts:
            return "There are no confirmed medications found in this prescription."

        if intent == VoiceIntentType.NIGHT_MEDICINE:
            night_meds = [f for f in facts if f.night is True]
            if not night_meds:
                return (
                    "There are no confirmed medications scheduled for the night "
                    "on this prescription."
                )
            items = []
            for f in night_meds:
                dose = _format_dose_str(f.dose_value, f.dose_unit, "1 dose")
                meal = ""
                if f.after_meal:
                    meal = " after food"
                elif f.before_meal:
                    meal = " on an empty stomach"
                items.append(f"{f.drug_name} ({dose}{meal})")
            return f"At night, take: {', '.join(items)}."

        if intent == VoiceIntentType.MORNING_MEDICINE:
            morn_meds = [f for f in facts if f.morning is True]
            if not morn_meds:
                return (
                    "There are no confirmed medications scheduled for the morning "
                    "on this prescription."
                )
            items = []
            for f in morn_meds:
                dose = _format_dose_str(f.dose_value, f.dose_unit, "1 dose")
                meal = ""
                if f.after_meal:
                    meal = " after food"
                elif f.before_meal:
                    meal = " on an empty stomach"
                items.append(f"{f.drug_name} ({dose}{meal})")
            return f"In the morning, take: {', '.join(items)}."

        if intent == VoiceIntentType.BEFORE_FOOD:
            bf_meds = [f for f in facts if f.before_meal is True]
            if not bf_meds:
                return (
                    "There are no confirmed medications marked to be taken before food "
                    "on this prescription."
                )
            items = [f.drug_name for f in bf_meds]
            return f"Take before food: {', '.join(items)}."

        if intent == VoiceIntentType.AFTER_FOOD:
            af_meds = [f for f in facts if f.after_meal is True]
            if not af_meds:
                return (
                    "There are no confirmed medications marked to be taken after food "
                    "on this prescription."
                )
            items = [f.drug_name for f in af_meds]
            return f"Take after food: {', '.join(items)}."

        if intent == VoiceIntentType.DURATION:
            items = []
            for f in facts:
                if f.duration_value and f.duration_unit:
                    items.append(f"{f.drug_name} for {f.duration_value} {f.duration_unit}")
                else:
                    items.append(f"{f.drug_name} (duration unstated)")
            return f"Course duration: {', '.join(items)}."

        if intent == VoiceIntentType.LIST_MEDICATIONS:
            items = []
            for f in facts:
                strn = ""
                if f.strength_value:
                    strn = f" {_format_strength_str(f.strength_value, f.strength_unit)}"
                items.append(f"{f.drug_name}{strn}")
            return f"Your prescribed medications are: {', '.join(items)}."

        if intent in (VoiceIntentType.SPECIFIC_DRUG, VoiceIntentType.SCHEDULE):
            filtered = facts
            if target_drug:
                filtered = [f for f in facts if f.drug_name.lower() == target_drug.lower()]
                if not filtered:
                    return f"No instructions found for {target_drug} in this prescription."

            items = []
            for f in filtered:
                times = []
                if f.morning:
                    times.append("Morning")
                if f.afternoon:
                    times.append("Afternoon")
                if f.evening:
                    times.append("Evening")
                if f.night:
                    times.append("Night")
                time_str = "/".join(times) if times else "as directed"
                meal = ""
                if f.after_meal:
                    meal = " after food"
                elif f.before_meal:
                    meal = " before food"
                dur = ""
                if f.duration_value and f.duration_unit:
                    dur = f" for {f.duration_value} {f.duration_unit}"
                items.append(f"{f.drug_name}: Take in the {time_str}{meal}{dur}")
            return "; ".join(items) + "."

        return self.get_unsupported_intent_message("en-IN")

    # --------------------------------------------------------------------------
    # Hindi Formatter
    # --------------------------------------------------------------------------
    def _format_hindi(
        self,
        intent: VoiceIntentType,
        facts: list[CanonicalMedicationFact],
        target_drug: str | None,
    ) -> str:
        if not facts:
            return "इस पर्चे में कोई सत्यापित दवा नहीं मिली।"

        if intent == VoiceIntentType.NIGHT_MEDICINE:
            night_meds = [f for f in facts if f.night is True]
            if not night_meds:
                return "इस पर्चे पर रात के लिए कोई सत्यापित दवा निर्धारित नहीं है।"
            items = []
            for f in night_meds:
                dose = _format_dose_str(f.dose_value, f.dose_unit, "1 खुराक")
                meal = ""
                if f.after_meal:
                    meal = " खाने के बाद"
                elif f.before_meal:
                    meal = " खाली पेट"
                items.append(f"{f.drug_name} ({dose}{meal})")
            return f"रात को लें: {', '.join(items)}।"

        if intent == VoiceIntentType.MORNING_MEDICINE:
            morn_meds = [f for f in facts if f.morning is True]
            if not morn_meds:
                return "इस पर्चे पर सुबह के लिए कोई सत्यापित दवा निर्धारित नहीं है।"
            items = []
            for f in morn_meds:
                dose = _format_dose_str(f.dose_value, f.dose_unit, "1 खुराक")
                meal = ""
                if f.after_meal:
                    meal = " खाने के बाद"
                elif f.before_meal:
                    meal = " खाली पेट"
                items.append(f"{f.drug_name} ({dose}{meal})")
            return f"सुबह लें: {', '.join(items)}।"

        if intent == VoiceIntentType.BEFORE_FOOD:
            bf_meds = [f for f in facts if f.before_meal is True]
            if not bf_meds:
                return "इस पर्चे पर खाने से पहले लेने के लिए कोई सत्यापित दवा निर्धारित नहीं है।"
            items = [f.drug_name for f in bf_meds]
            return f"खाने से पहले लें: {', '.join(items)}।"

        if intent == VoiceIntentType.AFTER_FOOD:
            af_meds = [f for f in facts if f.after_meal is True]
            if not af_meds:
                return "इस पर्चे पर खाने के बाद लेने के लिए कोई सत्यापित दवा निर्धारित नहीं है।"
            items = [f.drug_name for f in af_meds]
            return f"खाने के बाद लें: {', '.join(items)}।"

        if intent == VoiceIntentType.DURATION:
            items = []
            for f in facts:
                if f.duration_value and f.duration_unit:
                    unit = "महीने" if "month" in f.duration_unit else "दिन"
                    items.append(f"{f.drug_name} ({f.duration_value} {unit})")
                else:
                    items.append(f"{f.drug_name}")
            return f"दवा लेने की अवधि: {', '.join(items)}।"

        if intent == VoiceIntentType.LIST_MEDICATIONS:
            items = [f.drug_name for f in facts]
            return f"आपके पर्चे में लिखी दवाइयाँ हैं: {', '.join(items)}।"

        if intent in (VoiceIntentType.SPECIFIC_DRUG, VoiceIntentType.SCHEDULE):
            filtered = facts
            if target_drug:
                filtered = [f for f in facts if f.drug_name.lower() == target_drug.lower()]
                if not filtered:
                    return f"{target_drug} के लिए कोई निर्देश नहीं मिला।"

            items = []
            for f in filtered:
                times = []
                if f.morning:
                    times.append("सुबह")
                if f.afternoon:
                    times.append("दोपहर")
                if f.evening:
                    times.append("शाम")
                if f.night:
                    times.append("रात")
                time_str = " और ".join(times) if times else "निर्देशानुसार"
                meal = " खाने के बाद" if f.after_meal else (" खाली पेट" if f.before_meal else "")
                dur = ""
                if f.duration_value and "day" in str(f.duration_unit):
                    dur = f" {f.duration_value} दिनों के लिए"
                items.append(f"{f.drug_name}: {time_str}{meal}{dur} लें")
            return "। ".join(items) + "।"

        return self.get_unsupported_intent_message("hi-IN")

    # --------------------------------------------------------------------------
    # Kannada Formatter
    # --------------------------------------------------------------------------
    def _format_kannada(
        self,
        intent: VoiceIntentType,
        facts: list[CanonicalMedicationFact],
        _target_drug: str | None,
    ) -> str:
        if not facts:
            return "ಈ ಚೀಟಿಯಲ್ಲಿ ಯಾವುದೇ ದೃಢಪಡಿಸಿದ ಔಷಧಿಗಳು ಕಂಡುಬಂದಿಲ್ಲ."

        if intent == VoiceIntentType.NIGHT_MEDICINE:
            night_meds = [f for f in facts if f.night is True]
            if not night_meds:
                return "ಈ ಚೀಟಿಯಲ್ಲಿ ರಾತ್ರಿ ತೆಗೆದುಕೊಳ್ಳಲು ಯಾವುದೇ ದೃಢಪಡಿಸಿದ ಔಷಧಿ ನಿಗದಿಪಡಿಸಿಲ್ಲ."
            items = []
            for f in night_meds:
                meal = " ಊಟದ ನಂತರ" if f.after_meal else (" ಊಟಕ್ಕೆ ಮುಂಚೆ" if f.before_meal else "")
                items.append(f"{f.drug_name}{meal}")
            return f"ರಾತ್ರಿ ತೆಗೆದುಕೊಳ್ಳಿ: {', '.join(items)}."

        if intent == VoiceIntentType.MORNING_MEDICINE:
            morn_meds = [f for f in facts if f.morning is True]
            if not morn_meds:
                return "ಈ ಚೀಟಿಯಲ್ಲಿ ಬೆಳಿಗ್ಗೆ ತೆಗೆದುಕೊಳ್ಳಲು ಯಾವುದೇ ದೃಢಪಡಿಸಿದ ಔಷಧಿ ನಿಗದಿಪಡಿಸಿಲ್ಲ."
            items = []
            for f in morn_meds:
                meal = " ಊಟದ ನಂತರ" if f.after_meal else (" ಊಟಕ್ಕೆ ಮುಂಚೆ" if f.before_meal else "")
                items.append(f"{f.drug_name}{meal}")
            return f"ಬೆಳಿಗ್ಗೆ ತೆಗೆದುಕೊಳ್ಳಿ: {', '.join(items)}."

        if intent == VoiceIntentType.BEFORE_FOOD:
            bf_meds = [f for f in facts if f.before_meal is True]
            if not bf_meds:
                return "ಈ ಚೀಟಿಯಲ್ಲಿ ಊಟಕ್ಕೆ ಮುಂಚೆ ತೆಗೆದುಕೊಳ್ಳಲು ಯಾವುದೇ ದೃಢಪಡಿಸಿದ ಔಷಧಿ ನಿಗದಿಪಡಿಸಿಲ್ಲ."
            items = [f.drug_name for f in bf_meds]
            return f"ಊಟಕ್ಕೆ ಮುಂಚೆ ತೆಗೆದುಕೊಳ್ಳಿ: {', '.join(items)}."

        if intent == VoiceIntentType.AFTER_FOOD:
            af_meds = [f for f in facts if f.after_meal is True]
            if not af_meds:
                return "ಈ ಚೀಟಿಯಲ್ಲಿ ಊಟದ ನಂತರ ತೆಗೆದುಕೊಳ್ಳಲು ಯಾವುದೇ ದೃಢಪಡಿಸಿದ ಔಷಧಿ ನಿಗದಿಪಡಿಸಿಲ್ಲ."
            items = [f.drug_name for f in af_meds]
            return f"ಊಟದ ನಂತರ ತೆಗೆದುಕೊಳ್ಳಿ: {', '.join(items)}."

        if intent == VoiceIntentType.DURATION:
            items = []
            for f in facts:
                if f.duration_value and f.duration_unit:
                    unit_str = str(f.duration_unit)
                    unit = (
                        "ದಿನಗಳು"
                        if "day" in unit_str
                        else ("ವಾರಗಳು" if "week" in unit_str else "ತಿಂಗಳುಗಳು")
                    )
                    items.append(f"{f.drug_name} ({f.duration_value} {unit})")
                else:
                    items.append(f"{f.drug_name}")
            return f"ಔಷಧಿ ತೆಗೆದುಕೊಳ್ಳುವ ಅವಧಿ: {', '.join(items)}."

        if intent == VoiceIntentType.LIST_MEDICATIONS:
            items = [f.drug_name for f in facts]
            return f"ನಿಮ್ಮ ಔಷಧಿಗಳು: {', '.join(items)}."

        if intent in (VoiceIntentType.SPECIFIC_DRUG, VoiceIntentType.SCHEDULE):
            filtered = facts
            if _target_drug:
                filtered = [f for f in facts if f.drug_name.lower() == _target_drug.lower()]
                if not filtered:
                    return f"{_target_drug} ಬಗ್ಗೆ ಯಾವುದೇ ಸೂಚನೆಗಳು ಕಂಡುಬಂದಿಲ್ಲ."

            items = []
            for f in filtered:
                times = []
                if f.morning:
                    times.append("ಬೆಳಿಗ್ಗೆ")
                if f.afternoon:
                    times.append("ಮಧ್ಯಾಹ್ನ")
                if f.evening:
                    times.append("ಸಂಜೆ")
                if f.night:
                    times.append("ರಾತ್ರಿ")
                time_str = " ಮತ್ತು ".join(times) if times else "ಸೂಚಿಸಿದಂತೆ"
                meal = " ಊಟದ ನಂತರ" if f.after_meal else (" ಊಟಕ್ಕೆ ಮುಂಚೆ" if f.before_meal else "")
                dur = ""
                if f.duration_value and "day" in str(f.duration_unit):
                    dur = f" {f.duration_value} ದಿನಗಳವರೆಗೆ"
                items.append(f"{f.drug_name}: {time_str}{meal}{dur}")
            return "; ".join(items) + "."

        return self.get_unsupported_intent_message("kn-IN")


# Backward compatibility alias
LocalizationService = TemplateLocalizationService
