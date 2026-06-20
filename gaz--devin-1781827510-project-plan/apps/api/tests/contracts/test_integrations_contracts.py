from __future__ import annotations

from app.contracts.integrations import (
    WebhookSigningConfig,
    sign_custom_webhook,
    verify_custom_webhook_signature,
)


def test_custom_webhook_signature_verifies_exact_body_and_key_id() -> None:
    config = WebhookSigningConfig(tenant_id="tenant-a", key_id="webhook-key-1")
    signing_key = b"fixture-signing-key"
    body = b'{"event":"order.created","tenant_id":"tenant-a"}'

    signature = sign_custom_webhook(
        config=config,
        body=body,
        timestamp=1_781_827_510,
        nonce="nonce-1",
        signing_key=signing_key,
    )

    assert verify_custom_webhook_signature(
        config=config,
        body=body,
        signing_key=signing_key,
        signature=signature,
    )
    assert not verify_custom_webhook_signature(
        config=config,
        body=b'{"event":"order.cancelled","tenant_id":"tenant-a"}',
        signing_key=signing_key,
        signature=signature,
    )


def test_custom_webhook_signature_is_tenant_key_scoped() -> None:
    config = WebhookSigningConfig(tenant_id="tenant-a", key_id="webhook-key-1")
    other_key_config = WebhookSigningConfig(tenant_id="tenant-a", key_id="webhook-key-2")
    signature = sign_custom_webhook(
        config=config,
        body=b"{}",
        timestamp=1_781_827_510,
        nonce="nonce-1",
        signing_key=b"fixture-signing-key",
    )

    assert not verify_custom_webhook_signature(
        config=other_key_config,
        body=b"{}",
        signing_key=b"fixture-signing-key",
        signature=signature,
    )
