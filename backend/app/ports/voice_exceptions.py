"""Domain exceptions for Speech-to-Text and Text-to-Speech operations."""


class VoiceError(Exception):
    """Base exception for voice domain operations."""

    def __init__(self, message: str, code: str = "VOICE_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class TranscribeError(VoiceError):
    """Raised when transcription service fails."""

    def __init__(self, message: str, code: str = "TRANSCRIBE_ERROR") -> None:
        super().__init__(message, code=code)


class UnsupportedLanguageError(VoiceError):
    """Raised when the specified language is not supported by the provider."""

    def __init__(self, message: str, code: str = "UNSUPPORTED_LANGUAGE") -> None:
        super().__init__(message, code=code)


class EmptyAudioError(VoiceError):
    """Raised when uploaded audio is empty or corrupt."""

    def __init__(self, message: str, code: str = "EMPTY_AUDIO_PAYLOAD") -> None:
        super().__init__(message, code=code)


class TTSError(VoiceError):
    """Raised when speech synthesis fails."""

    def __init__(self, message: str, code: str = "TTS_SYNTHESIS_ERROR") -> None:
        super().__init__(message, code=code)
