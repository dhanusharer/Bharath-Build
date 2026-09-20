"""Schemas for Voice Accessibility Endpoints."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class TranscribeResponse(BaseModel):
    """Response payload for audio speech-to-text conversion."""

    success: bool = Field(description="Whether transcription was successful")
    transcript: str = Field(description="Recognized spoken text")
    language: str = Field(description="Identified or requested language code")
    confidence: float | None = Field(default=None, description="Average transcription confidence")
    request_id: str = Field(description="Tracking correlation ID")


class VoiceQueryResponse(BaseModel):
    """Response payload for end-to-end conversational voice posology inquiry."""

    success: bool = Field(description="Whether query was answered safely")
    request_id: str = Field(description="Tracking correlation ID")
    prescription_id: str = Field(description="Target prescription identifier")
    transcript: str = Field(description="Recognized spoken text from patient")
    intent: str = Field(description="Resolved clinical intent category")
    target_drug: str | None = Field(default=None, description="Specific matched medication name")
    response_text: str = Field(description="Deterministic localized response text")
    audio_base64: str | None = Field(
        default=None,
        description="Base64-encoded synthesized speech audio (MP3)",
    )
    audio_content_type: str | None = Field(default="audio/mpeg", description="Audio MIME format")
    language: str = Field(description="Response language code")
    requires_review: bool = Field(description="Whether prescription requires human review")
    safety_reasons: list[str] = Field(
        default_factory=list,
        description="Safety or refusal triggers",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
