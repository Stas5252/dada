import json
import logging
import os
from collections.abc import Mapping
from uuid import uuid4

from app.settings import get_settings

logger = logging.getLogger(__name__)

# Outbound simulation log paths
OUTBOUND_CALLS_LOG = "tmp/outbound_calls_log.json"
SMS_LOG = "tmp/sms_log.json"


def ensure_log_dir() -> None:
    os.makedirs("tmp", exist_ok=True)


def _setting_value(tenant_settings: Mapping[str, object], key: str, fallback: str) -> str:
    value = tenant_settings.get(key)
    return value if isinstance(value, str) and value else fallback


def generate_voice_twiml(text: str, gather_action_url: str | None = None) -> str:
    """
    Generate TwiML XML for incoming/outgoing calls.
    If gather_action_url is provided, gathers user speech response in Russian.
    """
    twiml = '<?xml version="1.0" encoding="UTF-8"?>\n<Response>\n'
    if gather_action_url:
        twiml += (
            '  <Gather input="speech" language="ru-RU" '
            f'action="{gather_action_url}" method="POST" speechTimeout="auto">\n'
        )
        twiml += f'    <Say language="ru-RU">{text}</Say>\n'
        twiml += "  </Gather>\n"
        twiml += '  <Say language="ru-RU">Я не услышал вашего ответа. Всего доброго!</Say>\n'
        twiml += "  <Hangup/>\n"
    else:
        twiml += f'  <Say language="ru-RU">{text}</Say>\n'
        twiml += "  <Hangup/>\n"
    twiml += "</Response>"
    return twiml


async def trigger_outbound_call(
    tenant_id: str,
    agent_id: str,
    to_number: str,
    tenant_settings: Mapping[str, object],
) -> str:
    """
    Triggers an outbound call using Twilio API.
    If keys are missing, simulates the call by writing to a local JSON file.
    """
    settings = get_settings()
    account_sid = _setting_value(tenant_settings, "twilio_account_sid", settings.twilio_account_sid)
    auth_token = _setting_value(tenant_settings, "twilio_auth_token", settings.twilio_auth_token)
    from_number = _setting_value(
        tenant_settings,
        "twilio_phone_number",
        settings.twilio_phone_number,
    )

    api_url = _setting_value(tenant_settings, "api_public_url", settings.api_public_url).rstrip("/")
    webhook_url = f"{api_url}/api/v1/voice/webhooks/twilio/voice/{agent_id}?tenant_id={tenant_id}"

    if not account_sid or not auth_token or not from_number:
        # Simulation Mode
        call_sid = f"CA{uuid4().hex[:32]}"
        logger.info(
            "[Twilio Outbound Call Simulator] Calling %s from %s webhook: %s",
            to_number,
            from_number,
            webhook_url,
        )
        ensure_log_dir()

        # Load existing simulation logs
        log_data = []
        if os.path.exists(OUTBOUND_CALLS_LOG):
            try:
                with open(OUTBOUND_CALLS_LOG, encoding="utf-8") as f:
                    log_data = json.load(f)
            except Exception:
                pass

        log_data.append(
            {
                "call_sid": call_sid,
                "tenant_id": tenant_id,
                "agent_id": agent_id,
                "to_number": to_number,
                "from_number": from_number or "+15005550006 (mock)",
                "webhook_url": webhook_url,
                "status": "queued",
            }
        )

        with open(OUTBOUND_CALLS_LOG, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

        return call_sid

    # Real Twilio API integration
    try:
        from twilio.rest import Client  # type: ignore[import-untyped]

        client = Client(account_sid, auth_token)
        call = client.calls.create(to=to_number, from_=from_number, url=webhook_url)
        return str(call.sid)
    except ImportError:
        logger.warning("twilio SDK is not installed. Falling back to simulation.")
        return f"CA_MOCK_IMPORT_{uuid4().hex[:20]}"
    except Exception as e:
        logger.error(f"Failed to initiate Twilio call: {e}")
        raise e


async def trigger_sms_send(
    tenant_id: str,
    to_number: str,
    body: str,
    tenant_settings: Mapping[str, object],
) -> bool:
    """
    Sends an SMS using Twilio.
    Falls back to sandbox simulation if credentials are empty.
    """
    settings = get_settings()
    account_sid = _setting_value(tenant_settings, "twilio_account_sid", settings.twilio_account_sid)
    auth_token = _setting_value(tenant_settings, "twilio_auth_token", settings.twilio_auth_token)
    from_number = _setting_value(
        tenant_settings,
        "twilio_phone_number",
        settings.twilio_phone_number,
    )

    if not account_sid or not auth_token or not from_number:
        # Simulation Mode
        logger.info(f"[Twilio SMS Simulator] Sending SMS to {to_number}: {body}")
        ensure_log_dir()

        log_data = []
        if os.path.exists(SMS_LOG):
            try:
                with open(SMS_LOG, encoding="utf-8") as f:
                    log_data = json.load(f)
            except Exception:
                pass

        log_data.append(
            {"tenant_id": tenant_id, "to_number": to_number, "body": body, "status": "sent"}
        )

        with open(SMS_LOG, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

        return True

    # Real Twilio SMS send
    try:
        from twilio.rest import Client

        client = Client(account_sid, auth_token)
        client.messages.create(to=to_number, from_=from_number, body=body)
        return True
    except ImportError:
        logger.warning("twilio SDK is not installed. SMS simulated.")
        return True
    except Exception as e:
        logger.error(f"Failed to send Twilio SMS: {e}")
        return False
