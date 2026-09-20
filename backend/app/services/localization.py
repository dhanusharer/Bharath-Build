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
            return "There are no verified medications found in this prescription."

        if intent == VoiceIntentType.NIGHT_MEDICINE:
            night_meds = [f for f in facts if f.night is True]
            if not night_meds:
                return "You do not have any medications scheduled for the night."
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
                return "You do not have any medications scheduled for the morning."
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
                return "There are no medications marked to be taken before food."
            items = [f.drug_name for f in bf_meds]
            return f"Take before food: {', '.join(items)}."

        if intent == VoiceIntentType.AFTER_FOOD:
            af_meds = [f for f in facts if f.after_meal is True]
            if not af_meds:
                return "There are no medications marked to be taken after food."
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
                return "रात के समय लेने के लिए कोई दवा निर्धारित नहीं है।"
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
                return "सुबह लेने के लिए कोई दवा निर्धारित नहीं है।"
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
                return "खाली पेट या खाने से पहले लेने वाली कोई दवा नहीं है।"
            items = [f.drug_name for f in bf_meds]
            return f"खाने से पहले लें: {', '.join(items)}।"

        if intent == VoiceIntentType.AFTER_FOOD:
            af_meds = [f for f in facts if f.after_meal is True]
            if not af_meds:
                return "खाने के बाद लेने वाली कोई दवा नहीं है।"
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
            return "ಈ ಚೀಟಿಯಲ್ಲಿ ಯಾವುದೇ ಔಷಧಗಳು ಕಂಡುಬಂದಿಲ್ಲ."

        if intent == VoiceIntentType.NIGHT_MEDICINE:
            night_meds = [f for f in facts if f.night is True]
            if not night_meds:
                return "ರಾತ್ರಿ ತೆಗೆದುಕೊಳ್ಳಲು ಯಾವುದೇ ಔಷಧಿ ನಿಗದಿಪಡಿಸಿಲ್ಲ."
            items = []
            for f in night_meds:
                meal = " ಊಟದ ನಂತರ" if f.after_meal else (" ಊಟಕ್ಕೆ ಮುಂಚೆ" if f.before_meal else "")
                items.append(f"{f.drug_name}{meal}")
            return f"ರಾತ್ರಿ ತೆಗೆದುಕೊಳ್ಳಿ: {', '.join(items)}."

        if intent == VoiceIntentType.MORNING_MEDICINE:
            morn_meds = [f for f in facts if f.morning is True]
            if not morn_meds:
                return "ಬೆಳಿಗ್ಗೆ ತೆಗೆದುಕೊಳ್ಳಲು ಯಾವುದೇ ಔಷಧಿ ನಿಗದಿಪಡಿಸಿಲ್ಲ."
            items = []
            for f in morn_meds:
                meal = " ಊಟದ ನಂತರ" if f.after_meal else (" ಊಟಕ್ಕೆ ಮುಂಚೆ" if f.before_meal else "")
                items.append(f"{f.drug_name}{meal}")
            return f"ಬೆಳಿಗ್ಗೆ ತೆಗೆದುಕೊಳ್ಳಿ: {', '.join(items)}."

        if intent == VoiceIntentType.LIST_MEDICATIONS:
            items = [f.drug_name for f in facts]
            return f"ನಿಮ್ಮ ಔಷಧಿಗಳು: {', '.join(items)}."

        return self.get_unsupported_intent_message("kn-IN")
