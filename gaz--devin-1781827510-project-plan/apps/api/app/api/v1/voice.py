import json
import logging
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.api.v1.dependencies import require_tenant_permission
from app.contracts.voice import (
    InvalidVoiceTransition,
    VoiceSession,
    VoiceSessionEvent,
    VoiceState,
)
from app.limiter import limiter
from app.orchestrator import AgentOrchestrator
from app.rbac import Permission
from app.service_factory import get_voice_service
from app.settings import Settings, get_settings
from app.speech_service import SpeechService, get_speech_service
from app.store_factory import AppStore, get_app_store
from app.twilio_service import trigger_outbound_call, trigger_sms_send
from app.voice_service import VoiceSessionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])
MANAGE_VOICE = require_tenant_permission(Permission.MANAGE_CHAT)


class VoicePreviewTurnRequest(BaseModel):
    agent_id: UUID
    text: str = Field(min_length=1, max_length=4000)


class VoicePreviewTurnResponse(BaseModel):
    session: VoiceSession
    conversation_id: UUID
    customer_text: str
    assistant_text: str
    tts_status: Literal["not_requested", "not_configured"]


@router.post("/sessions", response_model=VoiceSession, status_code=status.HTTP_201_CREATED)
async def start_voice_session(
    tenant_id: str = Depends(MANAGE_VOICE),
    service: VoiceSessionService = Depends(get_voice_service),
) -> VoiceSession:
    return service.start_session(tenant_id)


@router.get("/sessions/{session_id}", response_model=VoiceSession)
async def get_voice_session(
    session_id: str,
    tenant_id: str = Depends(MANAGE_VOICE),
    service: VoiceSessionService = Depends(get_voice_service),
) -> VoiceSession:
    session = service.get_session(tenant_id, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice session not found")
    return session


@router.post("/sessions/{session_id}/events", response_model=VoiceSession)
async def apply_voice_session_event(
    session_id: str,
    event: VoiceSessionEvent,
    tenant_id: str = Depends(MANAGE_VOICE),
    service: VoiceSessionService = Depends(get_voice_service),
) -> VoiceSession:
    if event.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")
    try:
        return service.apply_event(session_id, event)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice session not found",
        ) from exc


@router.post("/sessions/{session_id}/preview-turn", response_model=VoicePreviewTurnResponse)
@limiter.limit("30/minute")
async def preview_voice_turn(
    request: Request,
    session_id: str,
    payload: VoicePreviewTurnRequest,
    tenant_id: str = Depends(MANAGE_VOICE),
    service: VoiceSessionService = Depends(get_voice_service),
    app_store: AppStore = Depends(get_app_store),
    settings: Settings = Depends(get_settings),
) -> VoicePreviewTurnResponse:
    from app.api.v1.dependencies import check_billing_limit

    tenant_uuid = UUID(tenant_id)
    agent = app_store.get_agent(tenant_uuid, payload.agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    session = service.get_or_start_session(tenant_id, session_id)
    if session.state not in {VoiceState.LISTENING, VoiceState.SPEAKING}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Voice session is not ready for a new turn: {session.state}",
        )

    check_billing_limit(tenant_uuid, app_store)

    conversation_uuid = uuid5(NAMESPACE_URL, f"voice_session:{session_id}")
    orchestrator = AgentOrchestrator(store=app_store, settings=settings)
    orchestrator_result = await orchestrator.process_message(
        tenant_id=tenant_uuid,
        agent_id=payload.agent_id,
        conversation_id=conversation_uuid,
        customer_message=payload.text,
        channel="voice",
    )
    response_text = orchestrator_result.response_text

    try:
        session = service.record_voice_turn(
            tenant_id=tenant_id,
            session_id=session_id,
            customer_text=payload.text,
            assistant_text=response_text,
        )
    except InvalidVoiceTransition as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    app_store.record_chat_turn(
        tenant_id=tenant_uuid,
        agent_id=payload.agent_id,
        conversation_id=conversation_uuid,
        channel="voice",
        customer_text=payload.text,
        agent_response_text=response_text,
        confidence_score=orchestrator_result.confidence_score,
    )

    return VoicePreviewTurnResponse(
        session=session,
        conversation_id=conversation_uuid,
        customer_text=payload.text,
        assistant_text=response_text,
        tts_status="not_requested",
    )


@router.post("/sessions/{session_id}/audio")
@limiter.limit("10/minute")
async def process_voice_audio(
    request: Request,
    session_id: str,
    agent_id: str,
    audio: UploadFile = File(...),
    tenant_id: str = Depends(MANAGE_VOICE),
    speech_service: SpeechService = Depends(get_speech_service),
    service: VoiceSessionService = Depends(get_voice_service),
    app_store: AppStore = Depends(get_app_store),
    settings: Settings = Depends(get_settings),
) -> Response:
    """
    Process an audio file:
    1. STT: audio -> text
    2. LLM: text -> text
    3. TTS: text -> audio
    """
    audio_bytes = await audio.read()

    # 1. STT
    customer_text = await speech_service.speech_to_text(
        audio_bytes, filename=audio.filename or "audio.wav"
    )

    if customer_text.startswith("[STT Error"):
        raise HTTPException(status_code=500, detail=customer_text)

    # 2. LLM via Orchestrator
    orchestrator = AgentOrchestrator(store=app_store, settings=settings)
    tenant_uuid = UUID(tenant_id)
    agent_uuid = UUID(agent_id)

    conversation_uuid = uuid5(NAMESPACE_URL, f"voice_session:{session_id}")

    agent = app_store.get_agent(tenant_uuid, agent_uuid)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    voice_id = agent.voice_id

    orchestrator_result = await orchestrator.process_message(
        tenant_id=tenant_uuid,
        agent_id=agent_uuid,
        conversation_id=conversation_uuid,
        customer_message=customer_text,
        channel="voice",
    )
    response_text = orchestrator_result.response_text

    try:
        service.record_voice_turn(
            tenant_id=tenant_id,
            session_id=session_id,
            customer_text=customer_text,
            assistant_text=response_text,
        )
    except InvalidVoiceTransition as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    app_store.record_chat_turn(
        tenant_id=tenant_uuid,
        agent_id=agent_uuid,
        conversation_id=conversation_uuid,
        channel="voice",
        customer_text=customer_text,
        agent_response_text=response_text,
        confidence_score=orchestrator_result.confidence_score,
    )

    # 3. TTS
    audio_response_bytes = await speech_service.text_to_speech(response_text, voice=voice_id)

    return Response(
        content=audio_response_bytes,
        media_type="audio/mpeg",
        headers={
            "X-Conversation-Id": str(conversation_uuid),
            "X-Voice-Session-Id": session_id,
        },
    )


class OutboundCallRequest(BaseModel):
    agent_id: str
    to_number: str


@router.post("/calls/outbound")
async def initiate_call(
    payload: OutboundCallRequest,
    tenant_id: str = Depends(MANAGE_VOICE),
    app_store: AppStore = Depends(get_app_store),
) -> dict[str, str]:
    """Start an outbound phone call to a customer."""
    tenant_uuid = UUID(tenant_id)
    tenant = app_store.get_tenant(tenant_uuid)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    from app.api.v1.dependencies import check_billing_limit

    check_billing_limit(tenant_uuid, app_store)

    call_sid = await trigger_outbound_call(
        tenant_id=tenant_id,
        agent_id=payload.agent_id,
        to_number=payload.to_number,
        tenant_settings=tenant.settings,
    )
    return {"call_sid": call_sid, "status": "initiated"}


@router.post("/webhooks/twilio/voice/{agent_id}")
async def twilio_voice_webhook(
    agent_id: str,
    tenant_id: str | None = None,
    CallSid: str = Form(...),
    SpeechResult: str | None = Form(None),
    app_store: AppStore = Depends(get_app_store),
    settings: Settings = Depends(get_settings),
    service: VoiceSessionService = Depends(get_voice_service),
) -> Response:
    """Handle incoming call webhook from Twilio."""
    # Fallback to demo tenant if none provided
    if not tenant_id:
        tenant_id = settings.demo_tenant_id

    tenant_uuid = UUID(tenant_id)
    agent_uuid = UUID(agent_id)

    tenant = app_store.get_tenant(tenant_uuid)

    from app.api.v1.dependencies import check_billing_limit

    try:
        check_billing_limit(tenant_uuid, app_store)
    except HTTPException as e:
        if e.status_code == 402:
            from app.twilio_service import generate_voice_twiml

            limit_message = (
                "Уведомление: Лимит минут и сообщений для этого голосового ассистента "
                "исчерпан. Пожалуйста, обновите тарифный план. Всего доброго!"
            )
            twiml_xml = generate_voice_twiml(limit_message)
            return Response(content=twiml_xml, media_type="application/xml")
        raise e

    conversation_uuid = uuid5(NAMESPACE_URL, f"twilio_call:{CallSid}")
    service.get_or_start_session(tenant_id, CallSid)

    # Retrieve agent
    agent = app_store.get_agent(tenant_uuid, agent_uuid)
    if not agent:
        return Response(
            content=generate_voice_twiml("Простите, агент не найден. Всего доброго!"),
            media_type="application/xml",
        )

    # Calculate action webhook URL for next gather turn
    next_action_url = f"/api/v1/voice/webhooks/twilio/voice/{agent_id}?tenant_id={tenant_id}"

    if not SpeechResult:
        # Start of call greeting
        company_name = tenant.name if tenant else ""
        greeting = (
            f"Здравствуйте! Я ИИ-ассистент компании {company_name}. " "Чем я могу вам помочь?"
        )
        twiml_xml = generate_voice_twiml(greeting, gather_action_url=next_action_url)
        return Response(content=twiml_xml, media_type="application/xml")

    # SpeechResult exists: run orchestrator
    orchestrator = AgentOrchestrator(store=app_store, settings=settings)
    orchestrator_result = await orchestrator.process_message(
        tenant_id=tenant_uuid,
        agent_id=agent_uuid,
        conversation_id=conversation_uuid,
        customer_message=SpeechResult,
        channel="sip",
    )
    response_text = orchestrator_result.response_text

    app_store.record_chat_turn(
        tenant_id=tenant_uuid,
        agent_id=agent_uuid,
        conversation_id=conversation_uuid,
        channel="sip",
        customer_text=SpeechResult,
        agent_response_text=response_text,
        confidence_score=orchestrator_result.confidence_score,
    )
    try:
        service.record_voice_turn(
            tenant_id=tenant_id,
            session_id=CallSid,
            customer_text=SpeechResult,
            assistant_text=response_text,
        )
    except InvalidVoiceTransition as exc:
        logger.warning("Could not record Twilio voice session turn: %s", exc)

    twiml_xml = generate_voice_twiml(response_text, gather_action_url=next_action_url)
    return Response(content=twiml_xml, media_type="application/xml")


@router.post("/webhooks/twilio/sms/{agent_id}")
async def twilio_sms_webhook(
    agent_id: str,
    tenant_id: str | None = None,
    From: str = Form(...),
    Body: str = Form(...),
    MessageSid: str = Form(...),
    app_store: AppStore = Depends(get_app_store),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Handle incoming SMS from Twilio."""
    if not tenant_id:
        tenant_id = settings.demo_tenant_id

    tenant_uuid = UUID(tenant_id)
    agent_uuid = UUID(agent_id)

    tenant = app_store.get_tenant(tenant_uuid)
    tenant_settings = tenant.settings if tenant else {}

    from app.api.v1.dependencies import check_billing_limit

    try:
        check_billing_limit(tenant_uuid, app_store)
    except HTTPException as e:
        if e.status_code == 402:
            await trigger_sms_send(
                tenant_id=tenant_id,
                to_number=From,
                body=(
                    "CallForce: Лимит сообщений для этого ассистента исчерпан. "
                    "Пожалуйста, обновите тарифный план."
                ),
                tenant_settings=tenant_settings,
            )
            return Response(content="<Response/>", media_type="application/xml")
        raise e

    conversation_uuid = uuid5(NAMESPACE_URL, f"twilio_sms:{From}:{agent_id}")

    orchestrator = AgentOrchestrator(store=app_store, settings=settings)
    orchestrator_result = await orchestrator.process_message(
        tenant_id=tenant_uuid,
        agent_id=agent_uuid,
        conversation_id=conversation_uuid,
        customer_message=Body,
        channel="telegram",  # Normalizing to text chat
    )
    response_text = orchestrator_result.response_text

    app_store.record_chat_turn(
        tenant_id=tenant_uuid,
        agent_id=agent_uuid,
        conversation_id=conversation_uuid,
        channel="telegram",
        customer_text=Body,
        agent_response_text=response_text,
        confidence_score=orchestrator_result.confidence_score,
    )

    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<Response>\n"
        f"  <Message>{response_text}</Message>\n"
        "</Response>"
    )
    return Response(content=twiml, media_type="application/xml")


@router.websocket("/stream/{agent_id}")
async def voice_websocket_stream(
    websocket: WebSocket,
    agent_id: str,
    tenant_id: str | None = None,
    app_store: AppStore = Depends(get_app_store),
    settings: Settings = Depends(get_settings),
    speech_service: SpeechService = Depends(get_speech_service),
    service: VoiceSessionService = Depends(get_voice_service),
) -> None:
    """Real-time voice streaming WebSocket connection."""
    await websocket.accept()
    if not tenant_id:
        tenant_id = settings.demo_tenant_id

    tenant_uuid = UUID(tenant_id)

    from app.api.v1.dependencies import check_billing_limit

    try:
        check_billing_limit(tenant_uuid, app_store)
    except HTTPException:
        error_payload = {
            "event": "error",
            "message": "Лимит тарифа исчерпан. Пожалуйста, обновите тарифный план.",
        }
        await websocket.send_text(json.dumps(error_payload))
        await websocket.close()
        return

    agent_uuid = UUID(agent_id)
    session_id = str(uuid4())
    conversation_uuid = uuid5(NAMESPACE_URL, f"voice_stream:{session_id}")
    service.get_or_start_session(tenant_id, session_id)

    try:
        audio_buffer = bytearray()
        while True:
            data = await websocket.receive()
            if "bytes" in data:
                audio_buffer.extend(data["bytes"])
            elif "text" in data:
                text_msg = data["text"]
                if text_msg == "stop_record":
                    if len(audio_buffer) > 0:
                        # 1. Speech-to-Text
                        customer_text = await speech_service.speech_to_text(bytes(audio_buffer))
                        audio_buffer.clear()

                        if customer_text and not customer_text.startswith("[STT Error"):
                            await websocket.send_text(
                                json.dumps({"event": "stt", "text": customer_text})
                            )

                            # 2. Run Orchestrator
                            orchestrator = AgentOrchestrator(store=app_store, settings=settings)
                            orchestrator_result = await orchestrator.process_message(
                                tenant_id=tenant_uuid,
                                agent_id=agent_uuid,
                                conversation_id=conversation_uuid,
                                customer_message=customer_text,
                                channel="voice",
                            )
                            response_text = orchestrator_result.response_text
                            app_store.record_chat_turn(
                                tenant_id=tenant_uuid,
                                agent_id=agent_uuid,
                                conversation_id=conversation_uuid,
                                channel="voice",
                                customer_text=customer_text,
                                agent_response_text=response_text,
                                confidence_score=orchestrator_result.confidence_score,
                            )
                            try:
                                service.record_voice_turn(
                                    tenant_id=tenant_id,
                                    session_id=session_id,
                                    customer_text=customer_text,
                                    assistant_text=response_text,
                                )
                            except InvalidVoiceTransition as exc:
                                logger.warning(
                                    "Could not record WebSocket voice session turn: %s",
                                    exc,
                                )

                            await websocket.send_text(
                                json.dumps({"event": "llm", "text": response_text})
                            )

                            # 3. Text-to-Speech response
                            agent = app_store.get_agent(tenant_uuid, agent_uuid)
                            voice_id = agent.voice_id if agent else "alloy"
                            audio_response = await speech_service.text_to_speech(
                                response_text,
                                voice=voice_id,
                            )

                            if audio_response:
                                # Stream the audio chunks back to the client
                                chunk_size = 4096
                                for i in range(0, len(audio_response), chunk_size):
                                    await websocket.send_bytes(audio_response[i : i + chunk_size])

                            await websocket.send_text(json.dumps({"event": "done"}))
                        else:
                            await websocket.send_text(
                                json.dumps(
                                    {
                                        "event": "error",
                                        "message": "Could not recognize speech.",
                                    }
                                )
                            )
                    else:
                        await websocket.send_text(
                            json.dumps({"event": "error", "message": "No audio data received"})
                        )
    except WebSocketDisconnect:
        logger.info("WebSocket voice stream disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

import base64

@router.websocket("/webhooks/twilio/stream/{agent_id}")
async def twilio_media_stream_websocket(
    websocket: WebSocket,
    agent_id: str,
    tenant_id: str | None = None,
    app_store: AppStore = Depends(get_app_store),
    settings: Settings = Depends(get_settings),
    speech_service: SpeechService = Depends(get_speech_service),
    service: VoiceSessionService = Depends(get_voice_service),
) -> None:
    """Real-time Twilio Media Stream WebSocket connection."""
    await websocket.accept()
    if not tenant_id:
        tenant_id = settings.demo_tenant_id

    tenant_uuid = UUID(tenant_id)
    from app.api.v1.dependencies import check_billing_limit
    try:
        check_billing_limit(tenant_uuid, app_store)
    except HTTPException:
        logger.error("Billing limit reached for tenant %s", tenant_id)
        await websocket.close()
        return

    agent_uuid = UUID(agent_id)
    session_id = str(uuid4())
    conversation_uuid = uuid5(NAMESPACE_URL, f"twilio_stream:{session_id}")
    service.get_or_start_session(tenant_id, session_id)

    stream_sid = None
    try:
        audio_buffer = bytearray()
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg["event"] == "start":
                stream_sid = msg["start"]["streamSid"]
                logger.info(f"Twilio stream started: {stream_sid}")
            
            elif msg["event"] == "media":
                payload = msg["media"]["payload"]
                chunk = base64.b64decode(payload)
                audio_buffer.extend(chunk)
                
            elif msg["event"] == "stop":
                logger.info(f"Twilio stream stopped: {stream_sid}")
                if len(audio_buffer) > 0:
                    # 1. Speech-to-Text
                    # Save as raw mulaw or pass bytes to whisper
                    customer_text = await speech_service.speech_to_text(bytes(audio_buffer), filename="audio.ulaw")
                    audio_buffer.clear()

                    if customer_text and not customer_text.startswith("[STT Error"):
                        # 2. Run Orchestrator
                        orchestrator = AgentOrchestrator(store=app_store, settings=settings)
                        orchestrator_result = await orchestrator.process_message(
                            tenant_id=tenant_uuid,
                            agent_id=agent_uuid,
                            conversation_id=conversation_uuid,
                            customer_message=customer_text,
                            channel="sip",
                        )
                        response_text = orchestrator_result.response_text
                        app_store.record_chat_turn(
                            tenant_id=tenant_uuid,
                            agent_id=agent_uuid,
                            conversation_id=conversation_uuid,
                            channel="sip",
                            customer_text=customer_text,
                            agent_response_text=response_text,
                            confidence_score=orchestrator_result.confidence_score,
                        )
                        
                        # 3. TTS
                        agent = app_store.get_agent(tenant_uuid, agent_uuid)
                        voice_id = agent.voice_id if agent else "alloy"
                        audio_response = await speech_service.text_to_speech(response_text, voice=voice_id)

                        if audio_response and stream_sid:
                            # Send back Base64 audio payload
                            encoded_audio = base64.b64encode(audio_response).decode("utf-8")
                            await websocket.send_text(json.dumps({
                                "event": "media",
                                "streamSid": stream_sid,
                                "media": {
                                    "payload": encoded_audio
                                }
                            }))

    except WebSocketDisconnect:
        logger.info("Twilio WebSocket disconnected")
    except Exception as e:
        logger.error(f"Twilio WebSocket error: {e}")
