from dataclasses import dataclass, field
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


@dataclass
class VoiceSessionService:
    sessions: dict[str, VoiceSession] = field(default_factory=dict)

    def start_session(self, tenant_id: str, session_id: str | None = None) -> VoiceSession:
        resolved_session_id = session_id or str(uuid4())
        existing_session = self.sessions.get(resolved_session_id)
        if existing_session is not None:
            if existing_session.tenant_id != tenant_id:
                raise InvalidVoiceTransition("voice session tenant_id does not match")
            return existing_session

        session = VoiceSession(tenant_id=tenant_id, session_id=resolved_session_id)
        started_session = apply_voice_event(
            session,
            VoiceSessionEvent(tenant_id=tenant_id, event=VoiceEvent.START_CALL),
        )
        self.sessions[started_session.session_id] = started_session
        return started_session

    def apply_event(self, session_id: str, event: VoiceSessionEvent) -> VoiceSession:
        session = self.sessions[session_id]
        updated_session = apply_voice_event(session, event)
        self.sessions[session_id] = updated_session
        return updated_session

    def get_session(self, tenant_id: str, session_id: str) -> VoiceSession | None:
        session = self.sessions.get(session_id)
        if session is None or session.tenant_id != tenant_id:
            return None
        return session

    def get_or_start_session(self, tenant_id: str, session_id: str) -> VoiceSession:
        session = self.get_session(tenant_id, session_id)
        if session is not None:
            return session
        return self.start_session(tenant_id, session_id=session_id)

    def record_voice_turn(
        self,
        *,
        tenant_id: str,
        session_id: str,
        customer_text: str,
        assistant_text: str,
        finish_tts: bool = True,
    ) -> VoiceSession:
        session = self.get_or_start_session(tenant_id, session_id)
        if session.state == VoiceState.SPEAKING:
            session = self.apply_event(
                session.session_id,
                VoiceSessionEvent(tenant_id=tenant_id, event=VoiceEvent.TTS_FINISHED),
            )

        if session.state != VoiceState.LISTENING:
            raise InvalidVoiceTransition(
                f"cannot record voice turn while session is {session.state}"
            )

        thinking_session = self.apply_event(
            session.session_id,
            VoiceSessionEvent(
                tenant_id=tenant_id,
                event=VoiceEvent.USER_UTTERANCE,
                turn=VoiceTurn(speaker="customer", text=customer_text),
            ),
        )
        speaking_session = self.apply_event(
            thinking_session.session_id,
            VoiceSessionEvent(
                tenant_id=tenant_id,
                event=VoiceEvent.ASSISTANT_RESPONSE,
                turn=VoiceTurn(speaker="assistant", text=assistant_text),
            ),
        )

        if not finish_tts:
            return speaking_session

        return self.apply_event(
            speaking_session.session_id,
            VoiceSessionEvent(tenant_id=tenant_id, event=VoiceEvent.TTS_FINISHED),
        )
