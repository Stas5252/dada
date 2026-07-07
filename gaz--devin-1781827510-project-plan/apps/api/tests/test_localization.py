import pytest
from app.store.in_memory import _normalize_suppression_value

def test_russian_phone_normalization():
    # Regular international format
    assert _normalize_suppression_value("phone", "+79123456789") == "+79123456789"
    assert _normalize_suppression_value("phone", "79123456789") == "+79123456789"
    
    # Russian 8 (9xx) format
    assert _normalize_suppression_value("phone", "8 (912) 345-67-89") == "+79123456789"
    assert _normalize_suppression_value("phone", "89123456789") == "+79123456789"
    
    # Just 10 digits starting with 9
    assert _normalize_suppression_value("phone", "9123456789") == "+79123456789"
    
    # Another country code (should not be altered to +7)
    assert _normalize_suppression_value("phone", "+1 (555) 123-4567") == "+15551234567"
    assert _normalize_suppression_value("phone", "15551234567") == "+15551234567"
    
    # Edge case: short numbers
    with pytest.raises(ValueError):
        _normalize_suppression_value("phone", "123")
        
    with pytest.raises(ValueError):
        _normalize_suppression_value("phone", "")

def test_other_contact_type_normalization():
    assert _normalize_suppression_value("external_id", " Some_ID-123 ") == "some_id-123"

def test_speech_service_factories_yandex(monkeypatch):
    from app.speech_service import get_streaming_stt, get_streaming_tts
    from app.settings import get_settings
    
    settings = get_settings()
    monkeypatch.setattr(settings, "yandex_api_key", "test-yandex-key")
    monkeypatch.setattr(settings, "openai_api_key", "test-openai-key")
    monkeypatch.setattr(settings, "deepgram_api_key", "test-deepgram-key")
    
    stt = get_streaming_stt()
    tts = get_streaming_tts()
    
    assert stt.__class__.__name__ == "YandexStreamingSTT"
    assert tts.__class__.__name__ == "YandexStreamingTTS"
