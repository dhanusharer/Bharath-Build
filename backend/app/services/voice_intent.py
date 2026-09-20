"""Voice Intent Classification Service.

Deterministically maps user speech transcripts to supported clinical inquiry intents.
Does not invent intent facts or execute LLM hallucinations.
"""

import re
from dataclasses import dataclass
from enum import StrEnum


class VoiceIntentType(StrEnum):
    """Supported voice query intent categories."""

    SCHEDULE = "SCHEDULE"
    MORNING_MEDICINE = "MORNING_MEDICINE"
    AFTERNOON_MEDICINE = "AFTERNOON_MEDICINE"
    EVENING_MEDICINE = "EVENING_MEDICINE"
    NIGHT_MEDICINE = "NIGHT_MEDICINE"
    BEFORE_FOOD = "BEFORE_FOOD"
    AFTER_FOOD = "AFTER_FOOD"
    DURATION = "DURATION"
    LIST_MEDICATIONS = "LIST_MEDICATIONS"
    SPECIFIC_DRUG = "SPECIFIC_DRUG"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class VoiceIntentResult:
    """Represents the parsed intent from a spoken query."""

    intent: VoiceIntentType
    target_drug: str | None = None
    raw_query: str = ""
    is_supported: bool = True


# Multilingual intent pattern dictionaries (English, Hindi, Kannada romanized & native)
INTENT_PATTERNS: list[tuple[VoiceIntentType, list[str]]] = [
    (
        VoiceIntentType.NIGHT_MEDICINE,
        [
            r"\bnight\b",
            r"\bbedtime\b",
            r"\bsleep\b",
            r"\braat\b",
            r"\brathri\b",
            r"रात",
            r"सोते समय",
            r"ರಾತ್ರಿ",
            r"ಮಲಗುವಾಗ",
        ],
    ),
    (
        VoiceIntentType.MORNING_MEDICINE,
        [
            r"\bmorning\b",
            r"\bbreakfast\b",
            r"\bsubah\b",
            r"\bbelledh\b",
            r"\bbellagge\b",
            r"सुबह",
            r"नाश्ता",
            r"ಬೆಳಿಗ್ಗೆ",
            r"ಬೆಳಗ್ಗೆ",
        ],
    ),
    (
        VoiceIntentType.AFTERNOON_MEDICINE,
        [
            r"\bafternoon\b",
            r"\blunch\b",
            r"\bdopahar\b",
            r"\bmadhyahna\b",
            r"दोपहर",
            r"मध्याह्न",
        ],
    ),
    (
        VoiceIntentType.EVENING_MEDICINE,
        [
            r"\bevening\b",
            r"\bshaam\b",
            r"\bsanje\b",
            r"शाम",
            r"ಸಂಜೆ",
        ],
    ),
    (
        VoiceIntentType.BEFORE_FOOD,
        [
            r"\bbefore\s+(food|meal|eating)\b",
            r"\bempty\s+stomach\b",
            r"\bkhana\s+khane\s+se\s+pehle\b",
            r"\bpehle\b",
            r"\boota\s+munche\b",
            r"खाने से पहले",
            r"खाली पेट",
            r"ಊಟಕ್ಕೆ ಮುಂಚೆ",
        ],
    ),
    (
        VoiceIntentType.AFTER_FOOD,
        [
            r"\bafter\s+(food|meal|eating)\b",
            r"\bkhana\s+khane\s+ke\s+baad\b",
            r"\bbaad\b",
            r"\boota\s+aada\s+mele\b",
            r"खाने के बाद",
            r"ಊಟದ ನಂತರ",
        ],
    ),
    (
        VoiceIntentType.DURATION,
        [
            r"\bhow\s+long\b",
            r"\bhow\s+many\s+days\b",
            r"\bduration\b",
            r"\bkitne\s+din\b",
            r"\bkitna\s+samay\b",
            r"\beshtu\s+dina\b",
            r"कितने दिन",
            r"कितने समय",
            r"ಎಷ್ಟು ದಿನ",
        ],
    ),
    (
        VoiceIntentType.LIST_MEDICATIONS,
        [
            r"\blist\b",
            r"\bwhich\s+medicines?\b",
            r"\ball\s+medicines?\b",
            r"\bwhat\s+medicines?\b",
            r"\bkaun\s+si\s+dawai\b",
            r"\bdawa\s+ke\s+naam\b",
            r"\byaava\s+aushadhi\b",
            r"कौन सी दवा",
            r"दवाइयों के नाम",
            r"ಯಾವ ಔಷಧಿ",
        ],
    ),
    (
        VoiceIntentType.SCHEDULE,
        [
            r"\bschedule\b",
            r"\btiming\b",
            r"\bwhen\s+should\s+i\s+take\b",
            r"\bhow\s+to\s+take\b",
            r"\bkab\s+lena\s+hai\b",
            r"\bkab\s+khana\s+hai\b",
            r"\byaavaga\s+tegedukollabeku\b",
            r"कब लेना है",
            r"समय सारणी",
            r"ಹೇಗೆ ತೆಗೆದುಕೊಳ್ಳಬೇಕು",
        ],
    ),
]


class VoiceIntentService:
    """Deterministic voice intent classifier without LLM hallucinations."""

    def classify_intent(
        self,
        query_text: str,
        known_drug_names: list[str] | None = None,
    ) -> VoiceIntentResult:
        """Classify speech query into a clinical query intent."""
        clean_text = query_text.lower().strip()
        if not clean_text:
            return VoiceIntentResult(
                intent=VoiceIntentType.UNKNOWN,
                raw_query="",
                is_supported=False,
            )

        # 1. Check for specific known drug lookup
        matched_drug = None
        if known_drug_names:
            for drug in known_drug_names:
                if drug.lower() in clean_text:
                    matched_drug = drug
                    break

        # 2. Check keyword pattern matches
        for intent_type, patterns in INTENT_PATTERNS:
            for pat in patterns:
                if re.search(pat, clean_text, re.IGNORECASE):
                    return VoiceIntentResult(
                        intent=intent_type,
                        target_drug=matched_drug,
                        raw_query=query_text,
                        is_supported=True,
                    )

        # 3. If a specific drug was mentioned without explicit slot, treat as SPECIFIC_DRUG
        if matched_drug:
            return VoiceIntentResult(
                intent=VoiceIntentType.SPECIFIC_DRUG,
                target_drug=matched_drug,
                raw_query=query_text,
                is_supported=True,
            )

        # 4. Fallback: UNKNOWN intent
        return VoiceIntentResult(
            intent=VoiceIntentType.UNKNOWN,
            target_drug=None,
            raw_query=query_text,
            is_supported=False,
        )
