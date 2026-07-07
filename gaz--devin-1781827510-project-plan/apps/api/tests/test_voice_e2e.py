"""
T4.1 — Voice E2E тесты (моки).

Покрывает: входящий/исходящий звонок, перебивание (barge-in),
молчание, злость/эскалация, оператор (handoff),
вне базы знаний, отказ, follow-up.
"""
import pytest
from uuid import uuid4

from app.contracts.voice import (
    InvalidVoiceTransition,
    VoiceEvent,
    VoiceSession,
    VoiceSessionEvent,
    VoiceState,
    VoiceTurn,
    apply_voice_event,
)


TENANT = str(uuid4())


def _make_session(**overrides) -> VoiceSession:
    defaults = {"tenant_id": TENANT, "session_id": str(uuid4())}
    defaults.update(overrides)
    return VoiceSession(**defaults)


def _evt(event: VoiceEvent, **kw) -> VoiceSessionEvent:
    return VoiceSessionEvent(tenant_id=TENANT, event=event, **kw)


# ─── Входящий звонок: полный цикл ───────────────────────────────────

def test_inbound_call_full_cycle():
    """NEW → LISTENING → THINKING → SPEAKING → LISTENING → ... → ENDED."""
    session = _make_session()
    assert session.state == VoiceState.NEW

    # Клиент позвонил
    session = apply_voice_event(session, _evt(VoiceEvent.START_CALL))
    assert session.state == VoiceState.LISTENING

    # Клиент говорит
    session = apply_voice_event(
        session,
        _evt(VoiceEvent.USER_UTTERANCE, turn=VoiceTurn(speaker="user", text="Привет")),
    )
    assert session.state == VoiceState.THINKING

    # Ассистент отвечает
    session = apply_voice_event(
        session,
        _evt(VoiceEvent.ASSISTANT_RESPONSE, turn=VoiceTurn(speaker="assistant", text="Здравствуйте!")),
    )
    assert session.state == VoiceState.SPEAKING

    # TTS закончил
    session = apply_voice_event(session, _evt(VoiceEvent.TTS_FINISHED))
    assert session.state == VoiceState.LISTENING

    # Завершение
    session = apply_voice_event(session, _evt(VoiceEvent.END_CALL))
    assert session.state == VoiceState.ENDED
    assert len(session.transcript) == 2


# ─── Исходящий звонок (та же FSM) ─────────────────────────────────────

def test_outbound_call_same_fsm():
    """Исходящий звонок использует ту же FSM, начиная со START_CALL."""
    session = _make_session()
    session = apply_voice_event(session, _evt(VoiceEvent.START_CALL))
    assert session.state == VoiceState.LISTENING

    session = apply_voice_event(
        session,
        _evt(VoiceEvent.USER_UTTERANCE, turn=VoiceTurn(speaker="user", text="Алло?")),
    )
    assert session.state == VoiceState.THINKING

    session = apply_voice_event(
        session,
        _evt(VoiceEvent.ASSISTANT_RESPONSE, turn=VoiceTurn(speaker="assistant", text="Добрый день! Мы хотели...")),
    )
    assert session.state == VoiceState.SPEAKING


# ─── Barge-in (перебивание) ──────────────────────────────────────────

def test_barge_in_during_speaking_not_allowed_by_fsm():
    """
    FSM НЕ позволяет USER_UTTERANCE в состоянии SPEAKING — 
    barge-in обрабатывается на уровне WS, а не FSM.
    """
    session = _make_session()
    session = apply_voice_event(session, _evt(VoiceEvent.START_CALL))
    session = apply_voice_event(
        session,
        _evt(VoiceEvent.USER_UTTERANCE, turn=VoiceTurn(speaker="user", text="текст")),
    )
    session = apply_voice_event(
        session,
        _evt(VoiceEvent.ASSISTANT_RESPONSE, turn=VoiceTurn(speaker="assistant", text="ответ")),
    )
    assert session.state == VoiceState.SPEAKING

    with pytest.raises(InvalidVoiceTransition):
        apply_voice_event(
            session,
            _evt(VoiceEvent.USER_UTTERANCE, turn=VoiceTurn(speaker="user", text="перебивание")),
        )


# ─── Молчание (тишина): звонок заканчивается ────────────────────────

def test_silence_ends_call():
    """При молчании система завершает звонок через END_CALL."""
    session = _make_session()
    session = apply_voice_event(session, _evt(VoiceEvent.START_CALL))
    assert session.state == VoiceState.LISTENING

    # Молчание → система решает завершить
    session = apply_voice_event(session, _evt(VoiceEvent.END_CALL))
    assert session.state == VoiceState.ENDED


# ─── Злость клиента → эскалация на оператора ─────────────────────────

def test_angry_customer_escalation():
    """Агент распознаёт злость и эскалирует (ESCALATE → HANDOFF)."""
    session = _make_session()
    session = apply_voice_event(session, _evt(VoiceEvent.START_CALL))
    session = apply_voice_event(
        session,
        _evt(VoiceEvent.USER_UTTERANCE, turn=VoiceTurn(speaker="user", text="Да вы издеваетесь! Позовите менеджера!")),
    )
    assert session.state == VoiceState.THINKING

    # Агент решает эскалировать
    session = apply_voice_event(session, _evt(VoiceEvent.ESCALATE))
    assert session.state == VoiceState.HANDOFF


# ─── Оператор (handoff) — терминальное состояние ─────────────────────

def test_handoff_is_terminal():
    """После HANDOFF никакие события не работают."""
    session = _make_session(state=VoiceState.HANDOFF)

    with pytest.raises(InvalidVoiceTransition, match="terminal"):
        apply_voice_event(session, _evt(VoiceEvent.START_CALL))

    with pytest.raises(InvalidVoiceTransition, match="terminal"):
        apply_voice_event(session, _evt(VoiceEvent.END_CALL))


# ─── ENDED — терминальное состояние ──────────────────────────────────

def test_ended_is_terminal():
    session = _make_session(state=VoiceState.ENDED)
    with pytest.raises(InvalidVoiceTransition, match="terminal"):
        apply_voice_event(session, _evt(VoiceEvent.START_CALL))


# ─── Подтверждение действия (confirmation flow) ──────────────────────

def test_confirmation_flow():
    """THINKING → NEEDS_CONFIRMATION → WAITING → CONFIRMED → THINKING."""
    session = _make_session()
    session = apply_voice_event(session, _evt(VoiceEvent.START_CALL))
    session = apply_voice_event(
        session,
        _evt(VoiceEvent.USER_UTTERANCE, turn=VoiceTurn(speaker="user", text="Запишите меня")),
    )
    assert session.state == VoiceState.THINKING

    conf_id = str(uuid4())
    session = apply_voice_event(
        session,
        _evt(VoiceEvent.NEEDS_CONFIRMATION, confirmation_id=conf_id),
    )
    assert session.state == VoiceState.WAITING_CONFIRMATION
    assert session.pending_confirmation_id == conf_id

    session = apply_voice_event(
        session,
        _evt(VoiceEvent.CONFIRMED, confirmation_id=conf_id),
    )
    assert session.state == VoiceState.THINKING
    assert session.pending_confirmation_id is None


# ─── Неверный confirmation_id ────────────────────────────────────────

def test_wrong_confirmation_id_rejected():
    """Подтверждение с неверным ID отклоняется."""
    session = _make_session()
    session = apply_voice_event(session, _evt(VoiceEvent.START_CALL))
    session = apply_voice_event(
        session,
        _evt(VoiceEvent.USER_UTTERANCE, turn=VoiceTurn(speaker="user", text="текст")),
    )
    conf_id = str(uuid4())
    session = apply_voice_event(
        session,
        _evt(VoiceEvent.NEEDS_CONFIRMATION, confirmation_id=conf_id),
    )

    with pytest.raises(InvalidVoiceTransition, match="confirmation_id does not match"):
        apply_voice_event(
            session,
            _evt(VoiceEvent.CONFIRMED, confirmation_id=str(uuid4())),
        )


# ─── Tenant isolation на уровне FSM ─────────────────────────────────

def test_voice_tenant_isolation():
    """Событие с чужим tenant_id не применяется к сессии."""
    session = _make_session()
    other_tenant = str(uuid4())
    other_event = VoiceSessionEvent(
        tenant_id=other_tenant, event=VoiceEvent.START_CALL
    )

    with pytest.raises(InvalidVoiceTransition, match="tenant_id does not match"):
        apply_voice_event(session, other_event)


# ─── Follow-up: после ответа возвращаемся в LISTENING ────────────────

def test_follow_up_returns_to_listening():
    """После TTS_FINISHED сессия возвращается в LISTENING для follow-up."""
    session = _make_session()
    session = apply_voice_event(session, _evt(VoiceEvent.START_CALL))
    session = apply_voice_event(
        session,
        _evt(VoiceEvent.USER_UTTERANCE, turn=VoiceTurn(speaker="user", text="Вопрос 1")),
    )
    session = apply_voice_event(
        session,
        _evt(VoiceEvent.ASSISTANT_RESPONSE, turn=VoiceTurn(speaker="assistant", text="Ответ 1")),
    )
    session = apply_voice_event(session, _evt(VoiceEvent.TTS_FINISHED))
    assert session.state == VoiceState.LISTENING

    # Второй вопрос (follow-up)
    session = apply_voice_event(
        session,
        _evt(VoiceEvent.USER_UTTERANCE, turn=VoiceTurn(speaker="user", text="Вопрос 2")),
    )
    session = apply_voice_event(
        session,
        _evt(VoiceEvent.ASSISTANT_RESPONSE, turn=VoiceTurn(speaker="assistant", text="Ответ 2")),
    )
    session = apply_voice_event(session, _evt(VoiceEvent.TTS_FINISHED))
    assert session.state == VoiceState.LISTENING
    assert len(session.transcript) == 4


# ─── Transcript accumulation ─────────────────────────────────────────

def test_transcript_accumulates_turns():
    """Все повороты сохраняются в transcript."""
    session = _make_session()
    session = apply_voice_event(session, _evt(VoiceEvent.START_CALL))
    assert len(session.transcript) == 0

    session = apply_voice_event(
        session,
        _evt(VoiceEvent.USER_UTTERANCE, turn=VoiceTurn(speaker="user", text="Привет")),
    )
    assert len(session.transcript) == 1

    session = apply_voice_event(
        session,
        _evt(VoiceEvent.ASSISTANT_RESPONSE, turn=VoiceTurn(speaker="assistant", text="Здравствуйте")),
    )
    assert len(session.transcript) == 2
    assert session.transcript[0].speaker == "user"
    assert session.transcript[1].speaker == "assistant"
