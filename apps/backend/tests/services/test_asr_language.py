"""Unit tests for ASR language utilities."""
from common.config import get_settings
from services.asr.language import detect_language, is_urdu_text
from services.asr.translation import translate_to_english


def test_detect_language_urdu():
    assert is_urdu_text("یہ ایک ٹیسٹ ہے") is True
    assert detect_language("یہ ایک ٹیسٹ ہے") == "ur"


def test_detect_language_english():
    assert is_urdu_text("Find apartments in Lahore") is False
    assert detect_language("Find apartments in Lahore") == "en"


def test_translate_without_api_key(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "")
    get_settings.cache_clear()
    text = "یہ ایک ٹیسٹ ہے"
    translated, did_translate, error = translate_to_english(text)
    assert translated == text
    assert did_translate is False
    assert error is not None
