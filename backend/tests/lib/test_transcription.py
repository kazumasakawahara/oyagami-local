"""Tests for audio transcription module."""
from app.lib.transcription import SUPPORTED_AUDIO_FORMATS, is_supported_format


def test_supported_formats():
    assert ".mp3" in SUPPORTED_AUDIO_FORMATS
    assert ".wav" in SUPPORTED_AUDIO_FORMATS
    assert ".m4a" in SUPPORTED_AUDIO_FORMATS
    assert ".ogg" in SUPPORTED_AUDIO_FORMATS
    assert ".webm" in SUPPORTED_AUDIO_FORMATS


def test_is_supported_format_valid():
    assert is_supported_format("test.mp3")
    assert is_supported_format("meeting.wav")
    assert is_supported_format("record.m4a")


def test_is_supported_format_invalid():
    assert not is_supported_format("document.pdf")
    assert not is_supported_format("image.png")
    assert not is_supported_format("data.json")


def test_is_supported_format_case_insensitive():
    assert is_supported_format("test.MP3")
    assert is_supported_format("test.WAV")
