from __future__ import annotations

import pytest

from app.contracts.voice import (
    InvalidVoiceTransition,
    VoiceEvent,
    VoiceSession,
    VoiceSessionEvent,
    VoiceState,
    VoiceTurn,
    apply_voice_event,
)


def test_voice_session_requires_confirmation_before_returning_to_thinking() -> None:
    session = VoiceSession(tenant_id="tenant-a", session_id="call-1")
    session = apply_voice_event(
        session,
        VoiceSessionEvent(tenant_id="tenant-a", event=VoiceEvent.START_CALL),
    )
    session = apply_voice_event(
        session,
        VoiceSessionEvent(
            tenant_id="tenant-a",
            event=VoiceEvent.USER_UTTERANCE,
            turn=VoiceTurn(speaker="customer", text="Order a pizza"),
        ),
    )
    session = apply_voice_event(
        session,
        VoiceSessionEvent(
            tenant_id="tenant-a",
            event=VoiceEvent.NEEDS_CONFIRMATION,
            confirmation_id="confirm-order-1",
        ),
    )

    assert session.state == VoiceState.WAITING_CONFIRMATION
    assert session.pending_confirmation_id == "confirm-order-1"

    with pytest.raises(InvalidVoiceTransition):
        apply_voice_event(
            session,
            VoiceSessionEvent(
                tenant_id="tenant-a",
                event=VoiceEvent.CONFIRMED,
                confirmation_id="other-confirmation",
            ),
        )

    confirmed = apply_voice_event(
        session,
        VoiceSessionEvent(
            tenant_id="tenant-a",
            event=VoiceEvent.CONFIRMED,
            confirmation_id="confirm-order-1",
        ),
    )

    assert confirmed.state == VoiceState.THINKING
    assert confirmed.pending_confirmation_id is None


def test_voice_session_rejects_cross_tenant_events() -> None:
    session = VoiceSession(tenant_id="tenant-a", session_id="call-1")

    with pytest.raises(InvalidVoiceTransition):
        apply_voice_event(
            session,
            VoiceSessionEvent(tenant_id="tenant-b", event=VoiceEvent.START_CALL),
        )
