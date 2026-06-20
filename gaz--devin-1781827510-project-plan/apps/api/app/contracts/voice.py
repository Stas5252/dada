from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class VoiceState(StrEnum):
    NEW = "new"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    WAITING_CONFIRMATION = "waiting_confirmation"
    HANDOFF = "handoff"
    ENDED = "ended"


class VoiceEvent(StrEnum):
    START_CALL = "start_call"
    USER_UTTERANCE = "user_utterance"
    ASSISTANT_RESPONSE = "assistant_response"
    TTS_FINISHED = "tts_finished"
    NEEDS_CONFIRMATION = "needs_confirmation"
    CONFIRMED = "confirmed"
    ESCALATE = "escalate"
    END_CALL = "end_call"


class InvalidVoiceTransition(ValueError):
    """Raised when a voice event is not valid for the current state."""


class VoiceTurn(BaseModel):
    speaker: str = Field(min_length=1)
    text: str = Field(min_length=1)


class VoiceSession(BaseModel):
    tenant_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    state: VoiceState = VoiceState.NEW
    pending_confirmation_id: str | None = None
    transcript: tuple[VoiceTurn, ...] = ()


class VoiceSessionEvent(BaseModel):
    tenant_id: str = Field(min_length=1)
    event: VoiceEvent
    turn: VoiceTurn | None = None
    confirmation_id: str | None = None


TRANSITIONS: dict[tuple[VoiceState, VoiceEvent], VoiceState] = {
    (VoiceState.NEW, VoiceEvent.START_CALL): VoiceState.LISTENING,
    (VoiceState.LISTENING, VoiceEvent.USER_UTTERANCE): VoiceState.THINKING,
    (VoiceState.THINKING, VoiceEvent.ASSISTANT_RESPONSE): VoiceState.SPEAKING,
    (VoiceState.SPEAKING, VoiceEvent.TTS_FINISHED): VoiceState.LISTENING,
    (VoiceState.THINKING, VoiceEvent.NEEDS_CONFIRMATION): VoiceState.WAITING_CONFIRMATION,
    (VoiceState.WAITING_CONFIRMATION, VoiceEvent.CONFIRMED): VoiceState.THINKING,
}
TERMINAL_TRANSITIONS = {
    VoiceEvent.ESCALATE: VoiceState.HANDOFF,
    VoiceEvent.END_CALL: VoiceState.ENDED,
}


def apply_voice_event(session: VoiceSession, event: VoiceSessionEvent) -> VoiceSession:
    if event.tenant_id != session.tenant_id:
        raise InvalidVoiceTransition("voice event tenant_id does not match session tenant_id")
    if session.state in {VoiceState.HANDOFF, VoiceState.ENDED}:
        raise InvalidVoiceTransition("terminal voice sessions cannot transition")

    next_state = TERMINAL_TRANSITIONS.get(event.event)
    if next_state is None:
        next_state = TRANSITIONS.get((session.state, event.event))
    if next_state is None:
        raise InvalidVoiceTransition(f"cannot apply {event.event} from {session.state}")

    pending_confirmation_id = session.pending_confirmation_id
    if event.event == VoiceEvent.NEEDS_CONFIRMATION:
        if event.confirmation_id is None:
            raise InvalidVoiceTransition("confirmation_id is required")
        pending_confirmation_id = event.confirmation_id
    elif event.event == VoiceEvent.CONFIRMED:
        if event.confirmation_id != session.pending_confirmation_id:
            raise InvalidVoiceTransition("confirmation_id does not match pending confirmation")
        pending_confirmation_id = None

    transcript = session.transcript
    if event.turn is not None:
        transcript = (*transcript, event.turn)

    return session.model_copy(
        update={
            "state": next_state,
            "pending_confirmation_id": pending_confirmation_id,
            "transcript": transcript,
        }
    )
