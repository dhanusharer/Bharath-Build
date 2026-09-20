"""Localization Port Abstraction.

Defines formatting interface for converting verified prescription medication posology
into deterministic, localized presentation text for English, Hindi, and Kannada.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.services.voice_intent import VoiceIntentType


@dataclass(frozen=True)
class CanonicalMedicationFact:
    """Language-independent clinical posology fact."""

    drug_name: str
    strength_value: float | None
    strength_unit: str | None
    dose_value: float | None
    dose_unit: str | None
    morning: bool | None
    afternoon: bool | None
    evening: bool | None
    night: bool | None
    is_as_needed_sos: bool
    before_meal: bool | None
    after_meal: bool | None
    duration_value: int | None
    duration_unit: str | None
    is_verified_safe: bool = True


class LocalizationPort(ABC):
    """Port for generating localized text from canonical medication facts."""

    @abstractmethod
    def format_intent_response(
        self,
        intent: VoiceIntentType,
        facts: list[CanonicalMedicationFact],
        language: str = "en-IN",
        target_drug: str | None = None,
    ) -> str:
        """Format a spoken response for a given clinical intent and medication facts.

        Args:
            intent: The parsed VoiceIntentType.
            facts: List of validated medication facts from DB.
            language: Target language (en-IN, hi-IN, kn-IN).
            target_drug: Specific drug name if filtered.

        Returns:
            Deterministic localized text response.
        """
        raise NotImplementedError

    @abstractmethod
    def get_review_required_message(self, language: str = "en-IN") -> str:
        """Return safe message when prescription requires pharmacist review."""
        raise NotImplementedError

    @abstractmethod
    def get_unsupported_intent_message(self, language: str = "en-IN") -> str:
        """Return safe refusal message when question cannot be answered from prescription facts."""
        raise NotImplementedError
