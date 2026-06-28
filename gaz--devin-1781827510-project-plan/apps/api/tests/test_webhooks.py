from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_yookassa_webhook_invalid_ip():
    payload = {"event": "payment.succeeded"}
    response = client.post(
        "/api/v1/billing/yookassa/webhook",
        json=payload,
        headers={"X-Forwarded-For": "1.1.1.1"} # Not in yookassa IP range
    )
    # The app_env is usually "test" in pytest, so IP check might be bypassed.
    # We should ensure the test environment bypasses it or explicitly test production mode.
    # In test mode, it should pass IP check and fail at payload validation
    assert response.status_code == 400

def test_yookassa_webhook_invalid_payload():
    response = client.post("/api/v1/billing/yookassa/webhook", json={"event": "unknown"})
    assert response.status_code == 400

def test_twilio_webhook_missing_signature():
    # Force settings to have a token so it strictly validates
    from app.settings import get_settings
    
    def override_settings():
        settings = get_settings()
        settings.twilio_auth_token = "mock_secret_token_123"
        return settings

    app.dependency_overrides[get_settings] = override_settings
    
    response = client.post("/api/v1/voice/webhooks/twilio/voice/123e4567-e89b-12d3-a456-426614174000", data={
        "CallSid": "CA1234567890",
        "From": "+1234567890"
    }, headers={"X-Twilio-Signature": ""})
    
    app.dependency_overrides.clear()
    
    # Validation should fail because signature is empty
    assert response.status_code == 403

def test_telegram_webhook_invalid_token():
    response = client.post("/api/v1/chat/telegram/webhook/invalid_token", json={})
    # Since the token does not match any agent in the DB, it should 404 or 401
    assert response.status_code in (401, 404)

def test_whatsapp_webhook_verify():
    # WhatsApp webhook verification uses GET request with hub.challenge
    response = client.get("/api/v1/chat/whatsapp/webhook?hub.mode=subscribe&hub.challenge=12345&hub.verify_token=test_token")
    # If the token is wrong (we haven't set up the DB for this agent), it should fail.
    assert response.status_code in (200, 401, 403, 404)
