"""Audio transcription using OpenAI Whisper (local model)."""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_AUDIO_FORMATS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".webm"}
WHISPER_MODEL = "base"  # tiny, base, small, medium, large


def is_supported_format(filename: str) -> bool:
    """Check if file extension is a supported audio format."""
    return Path(filename).suffix.lower() in SUPPORTED_AUDIO_FORMATS


async def transcribe_audio(audio_path: str, language: str = "ja") -> str | None:
    """Transcribe audio file to text using Whisper.

    Args:
        audio_path: Path to audio file
        language: Language code (default: Japanese)
    Returns:
        Transcribed text or None on failure
    """
    try:
        import whisper
        model = whisper.load_model(WHISPER_MODEL)
        result = model.transcribe(audio_path, language=language)
        text = result.get("text", "")
        logger.info(f"Transcribed {audio_path}: {len(text)} chars")
        return text
    except ImportError:
        logger.error("openai-whisper not installed. Run: uv add openai-whisper")
        return None
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return None
