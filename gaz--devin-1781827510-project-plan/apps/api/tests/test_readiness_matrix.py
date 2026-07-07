"""Test readiness matrix structure and completeness."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///test_run.db")

from app.integration_readiness import build_integration_readiness
from app.schemas import IntegrationReadinessStatus
from app.settings import Settings, get_settings


def _make_settings(**overrides: str) -> Settings:
    get_settings.cache_clear()
    defaults = {
        "APP_ENV": "local",
        "DATABASE_URL": "sqlite:///test_run.db",
        "ACCESS_TOKEN_SECRET": "test-secret",
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


def test_readiness_response_has_all_required_providers():
    """All required providers must appear in the readiness matrix."""
    settings = _make_settings()
    response = build_integration_readiness(tenant_settings=None, settings=settings)
    
    keys = {item.key for item in response.items}
    required_keys = {
        "llm",
        "speech_stt_tts",
        "web_widget",
        "telegram",
        "vk",
        "whatsapp",
        "twilio_voice",
        "sip_asterisk",
        "yookassa",
        "iiko",
        "qdrant",
        "redis",
        "smtp",
    }
    missing = required_keys - keys
    assert not missing, f"Missing providers in readiness: {missing}"


def test_readiness_qdrant_local_stub_when_empty():
    """With no QDRANT_URL in local env, Qdrant should be local_stub."""
    settings = _make_settings(QDRANT_URL="")
    response = build_integration_readiness(tenant_settings=None, settings=settings)
    qdrant_item = next(item for item in response.items if item.key == "qdrant")
    assert qdrant_item.status == IntegrationReadinessStatus.local_stub


def test_readiness_qdrant_configured_with_url():
    """With a real QDRANT_URL, Qdrant should show configured."""
    settings = _make_settings(QDRANT_URL="http://qdrant:6333")
    response = build_integration_readiness(tenant_settings=None, settings=settings)
    qdrant_item = next(item for item in response.items if item.key == "qdrant")
    assert qdrant_item.status == IntegrationReadinessStatus.configured


def test_readiness_redis_local_stub_default():
    """Default redis URL should be local_stub."""
    settings = _make_settings()
    response = build_integration_readiness(tenant_settings=None, settings=settings)
    redis_item = next(item for item in response.items if item.key == "redis")
    assert redis_item.status == IntegrationReadinessStatus.local_stub


def test_readiness_smtp_local_stub_when_empty():
    """SMTP without host should be local_stub."""
    settings = _make_settings()
    response = build_integration_readiness(tenant_settings=None, settings=settings)
    smtp_item = next(item for item in response.items if item.key == "smtp")
    assert smtp_item.status == IntegrationReadinessStatus.local_stub


def test_readiness_all_items_have_required_fields():
    """Every readiness item must have key, label, category, status, summary."""
    settings = _make_settings()
    response = build_integration_readiness(tenant_settings=None, settings=settings)
    for item in response.items:
        assert item.key, f"Item missing key: {item}"
        assert item.label, f"Item missing label: {item}"
        assert item.category, f"Item missing category: {item}"
        assert item.status, f"Item missing status: {item}"
        assert item.summary, f"Item missing summary: {item}"


def test_qdrant_prod_validation_fails():
    """Production without QDRANT_URL must fail."""
    import pytest
    with pytest.raises(Exception):
        _make_settings(APP_ENV="production", QDRANT_URL="")
