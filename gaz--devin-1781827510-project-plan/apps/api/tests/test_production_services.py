import json
from pathlib import Path

import pytest

from app.billing_service import BillingService
from app.contracts.integrations import (
    IikoMenuItem,
    IikoOrderDraft,
    IikoOrderLine,
    IikoOrderStatus,
    WebhookSigningConfig,
)
from app.contracts.voice import VoiceEvent, VoiceSessionEvent, VoiceTurn
from app.integration_services import (
    LocalIikoAdapter,
    LocalTelegramAdapter,
    LocalWebhookSigner,
    LocalYooKassaAdapter,
    TelegramOutboundMessage,
    YooKassaPaymentDraft,
)
from app.settings import get_settings
from app.twilio_service import trigger_outbound_call
from app.voice_service import VoiceSessionService


@pytest.mark.asyncio
async def test_local_integration_adapters_are_idempotent() -> None:
    iiko = LocalIikoAdapter(
        menus={
            "tenant-1": [
                IikoMenuItem(
                    tenant_id="tenant-1",
                    external_id="pizza-1",
                    name="Pizza",
                    price_minor=99000,
                    available=True,
                )
            ]
        }
    )
    menu = await iiko.fetch_menu(tenant_id="tenant-1")
    assert menu[0].name == "Pizza"

    draft = IikoOrderDraft(
        tenant_id="tenant-1",
        customer_phone="+79990000000",
        delivery_address="Moscow",
        lines=[IikoOrderLine(menu_item_external_id="pizza-1", quantity=1)],
        idempotency_key="order-1",
    )
    order = await iiko.create_order(draft=draft, dry_run=False)
    replayed_order = await iiko.create_order(draft=draft, dry_run=False)
    assert replayed_order == order
    assert (
        await iiko.get_order_status(
            tenant_id="tenant-1",
            external_order_id=order.external_order_id,
        )
        == IikoOrderStatus.ACCEPTED
    )

    telegram = LocalTelegramAdapter()
    telegram_message = TelegramOutboundMessage(
        tenant_id="tenant-1",
        chat_id="chat-1",
        text="Hello",
        idempotency_key="telegram-1",
    )
    sent_message = await telegram.send_message(telegram_message)
    duplicate_message = await telegram.send_message(telegram_message)
    assert sent_message.external_message_id == duplicate_message.external_message_id
    assert duplicate_message.duplicate is True

    yookassa = LocalYooKassaAdapter()
    payment = YooKassaPaymentDraft(
        tenant_id="tenant-1",
        subject_id="invoice-1",
        amount_minor=150000,
        currency="RUB",
        description="Subscription",
        idempotency_key="payment-1",
    )
    created_payment = await yookassa.create_payment(payment)
    duplicate_payment = await yookassa.create_payment(payment)
    assert duplicate_payment.payment_id == created_payment.payment_id
    assert duplicate_payment.duplicate is True


def test_local_webhook_signer_roundtrip() -> None:
    signer = LocalWebhookSigner(
        config=WebhookSigningConfig(tenant_id="tenant-1", key_id="key-1"),
        signing_key=b"local-secret",
    )
    signature = signer.sign(body={"event": "order.created"}, timestamp=1, nonce="n")
    assert signer.verify(body={"event": "order.created"}, signature=signature)
    assert not signer.verify(body={"event": "order.cancelled"}, signature=signature)


def test_voice_session_service_tracks_call_turns() -> None:
    service = VoiceSessionService()
    session = service.start_session("tenant-1")
    assert session.state == "listening"

    thinking_session = service.apply_event(
        session.session_id,
        VoiceSessionEvent(
            tenant_id="tenant-1",
            event=VoiceEvent.USER_UTTERANCE,
            turn=VoiceTurn(speaker="customer", text="Where is my order?"),
        ),
    )
    assert thinking_session.state == "thinking"
    assert thinking_session.transcript[0].text == "Where is my order?"
    assert service.get_session("tenant-2", session.session_id) is None

    completed_turn = service.record_voice_turn(
        tenant_id="tenant-1",
        session_id="call-2",
        customer_text="Can I book a table?",
        assistant_text="Yes, I can help with that.",
    )
    assert completed_turn.state == "listening"
    assert [turn.speaker for turn in completed_turn.transcript] == ["customer", "assistant"]


@pytest.mark.asyncio
async def test_twilio_outbound_simulator_uses_voice_webhook_url(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("API_PUBLIC_URL", "https://api.example.com/")
    get_settings.cache_clear()
    try:
        call_sid = await trigger_outbound_call(
            tenant_id="tenant-1",
            agent_id="agent-1",
            to_number="+79990000000",
            tenant_settings={},
        )
    finally:
        get_settings.cache_clear()

    assert call_sid.startswith("CA")
    log_payload = json.loads(Path("tmp/outbound_calls_log.json").read_text(encoding="utf-8"))
    assert (
        log_payload[0]["webhook_url"]
        == "https://api.example.com/api/v1/voice/webhooks/twilio/voice/agent-1?tenant_id=tenant-1"
    )


@pytest.mark.asyncio
async def test_billing_service_deduplicates_usage_charges() -> None:
    service = BillingService()
    first_entry = await service.apply_usage_charge(
        tenant_id="tenant-1",
        subject_id="call-1",
        amount_minor=2500,
        currency="RUB",
        payload={"minutes": 1},
    )
    replayed_entry = await service.apply_usage_charge(
        tenant_id="tenant-1",
        subject_id="call-1",
        amount_minor=2500,
        currency="RUB",
        payload={"minutes": 1},
    )
    assert first_entry.status == "applied"
    assert replayed_entry.status == "duplicate"
    assert replayed_entry.idempotency_key.storage_key == first_entry.idempotency_key.storage_key
