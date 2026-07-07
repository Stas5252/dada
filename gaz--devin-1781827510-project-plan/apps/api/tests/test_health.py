from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import get_settings


def test_health_endpoint_returns_service_status() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "callforce-api"
    assert payload["version"] == "v1"
    assert "checked_at" in payload


def test_readiness_reports_local_stubs(monkeypatch) -> None:
    monkeypatch.setenv("STORE_BACKEND", "memory")
    get_settings.cache_clear()
    try:
        client = TestClient(create_app())
        response = client.get("/api/v1/readiness")
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "mock_only"
    assert payload["store_backend"] == "memory"
    assert {provider["provider"] for provider in payload["providers"]} == {
        "llm",
        "telegram",
        "yookassa",
        "iiko",
        "twilio_voice",
        "speech_stt_tts",
        "asterisk_ari",
    }
    assert all(provider["status"] == "local_stub" for provider in payload["providers"])


def test_readiness_reports_local_llm_when_vllm_is_configured(monkeypatch) -> None:
    monkeypatch.setenv("VLLM_BASE_URL", "http://localhost:8001/v1")
    monkeypatch.setenv("VLLM_MODEL", "local-test-model")
    get_settings.cache_clear()
    try:
        client = TestClient(create_app())
        response = client.get("/api/v1/readiness")
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
    llm = next(
        provider
        for provider in response.json()["providers"]
        if provider["provider"] == "llm"
    )
    assert llm["status"] == "configured"
    assert "local-test-model" in llm["detail"]
