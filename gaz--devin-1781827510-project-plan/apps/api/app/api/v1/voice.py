import asyncio
import base64
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
from twilio.request_validator import RequestValidator

from app.api.v1.dependencies import require_tenant_permission
from app.channel_policy import (
    audit_channel_policy_consent_block,
    audit_channel_policy_outbound_block,
    channel_policy_for_settings,
)
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
from app.speech_service import (
    SpeechService,
    StreamingSTT,
    StreamingTTS,
    get_speech_service,
    get_streaming_stt,
    get_streaming_tts,
)
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
    from app.service_factory import get_agent_orchestrator
    orchestrator = get_agent_orchestrator()
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

    app_store.record_chat_turn_background(
        tenant_id=tenant_uuid,
        agent_id=payload.agent_id,
        conversation_id=conversation_uuid,
        channel="voice",
        customer_text=payload.text,
        agent_response_text=response_text,
        confidence_score=orchestrator_result.confidence_score,
        forced_status=orchestrator_result.forced_status,
        forced_resolution_status=orchestrator_result.forced_resolution_status,
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
    from app.service_factory import get_agent_orchestrator
    orchestrator = get_agent_orchestrator()
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

    app_store.record_chat_turn_background(
        tenant_id=tenant_uuid,
        agent_id=agent_uuid,
        conversation_id=conversation_uuid,
        channel="voice",
        customer_text=customer_text,
        agent_response_text=response_text,
        confidence_score=orchestrator_result.confidence_score,
        forced_status=orchestrator_result.forced_status,
        forced_resolution_status=orchestrator_result.forced_resolution_status,
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
    channel_policy = channel_policy_for_settings(tenant.settings, "voice")
    if not channel_policy.outbound_enabled:
        audit_channel_policy_outbound_block(
            app_store,
            tenant_id=tenant_uuid,
            channel="voice",
            conversation_id=uuid5(NAMESPACE_URL, f"outbound_call:{payload.agent_id}:{payload.to_number}"),
            source="outbound_call",
            policy=channel_policy,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Outbound calls are disabled by channel policy",
        )

    from app.api.v1.dependencies import check_billing_limit

    check_billing_limit(tenant_uuid, app_store)

    suppression = app_store.find_contact_suppression(
        tenant_uuid,
        "voice",
        phone=payload.to_number,
    )
    if suppression:
        app_store.create_audit_log(
            event_type="contact_suppression.outbound_blocked",
            tenant_id=tenant_uuid,
            details={
                "channel": "voice",
                "contact_type": suppression.contact_type,
                "source": "outbound_call",
                "suppression_id": str(suppression.id),
                "value": suppression.value,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Contact has opted out of outbound calls",
        )

    if channel_policy.require_contact_consent_for_outbound:
        consent = app_store.find_contact_consent(
            tenant_uuid,
            "voice",
            phone=payload.to_number,
        )
        if not consent:
            audit_channel_policy_consent_block(
                app_store,
                tenant_id=tenant_uuid,
                channel="voice",
                conversation_id=uuid5(
                    NAMESPACE_URL,
                    f"outbound_call:{payload.agent_id}:{payload.to_number}",
                ),
                source="outbound_call",
                policy=channel_policy,
                contact_type="phone",
                value=payload.to_number,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Outbound consent is required by channel policy",
            )

    call_sid = await trigger_outbound_call(
        tenant_id=tenant_id,
        agent_id=payload.agent_id,
        to_number=payload.to_number,
        tenant_settings=tenant.settings,
    )
    return {"call_sid": call_sid, "status": "initiated"}


async def _validate_twilio_request(request: Request, auth_token: str) -> None:
    if not auth_token:
        # Skip validation if token is not configured (e.g. local dev)
        return
    validator = RequestValidator(auth_token)
    signature = request.headers.get("X-Twilio-Signature", "")
    url = str(request.url)
    form_data = await request.form()
    post_params = {k: v for k, v in form_data.items()}
    if not validator.validate(url, post_params, signature):
        logger.warning("Invalid Twilio signature for URL: %s", url)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Twilio signature")


@router.post("/webhooks/twilio/voice/{agent_id}")
async def twilio_voice_webhook(
    request: Request,
    agent_id: str,
    tenant_id: str | None = None,
    CallSid: str = Form(...),
    SpeechResult: str | None = Form(None),
    app_store: AppStore = Depends(get_app_store),
    settings: Settings = Depends(get_settings),
    service: VoiceSessionService = Depends(get_voice_service),
) -> Response:
    """Handle incoming call webhook from Twilio."""
    await _validate_twilio_request(request, settings.twilio_auth_token)
    
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
        retry_val = request.query_params.get("retry", "")
        if retry_val == "1":
            greeting = "Извините, я вас не расслышал. Пожалуйста, повторите ваш вопрос."
            next_action_url += "&retry=1"
        elif retry_val == "2":
            greeting = "Я всё ещё вас не слышу. Пожалуйста, скажите что-нибудь."
            next_action_url += "&retry=2"
        else:
            company_name = tenant.name if tenant else ""
            greeting = (
                f"Здравствуйте! Я ИИ-ассистент компании {company_name}. " "Чем я могу вам помочь?"
            )
        twiml_xml = generate_voice_twiml(greeting, gather_action_url=next_action_url)
        return Response(content=twiml_xml, media_type="application/xml")

    # SpeechResult exists: run orchestrator
    from app.service_factory import get_agent_orchestrator
    orchestrator = get_agent_orchestrator()
    orchestrator_result = await orchestrator.process_message(
        tenant_id=tenant_uuid,
        agent_id=agent_uuid,
        conversation_id=conversation_uuid,
        customer_message=SpeechResult,
        channel="sip",
    )
    response_text = orchestrator_result.response_text

    app_store.record_chat_turn_background(
        tenant_id=tenant_uuid,
        agent_id=agent_uuid,
        conversation_id=conversation_uuid,
        channel="sip",
        customer_text=SpeechResult,
        agent_response_text=response_text,
        confidence_score=orchestrator_result.confidence_score,
        forced_status=orchestrator_result.forced_status,
        forced_resolution_status=orchestrator_result.forced_resolution_status,
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
    request: Request,
    agent_id: str,
    tenant_id: str | None = None,
    From: str = Form(...),
    Body: str = Form(...),
    MessageSid: str = Form(...),
    app_store: AppStore = Depends(get_app_store),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Handle incoming SMS from Twilio."""
    await _validate_twilio_request(request, settings.twilio_auth_token)
    
    if not tenant_id:
        tenant_id = settings.demo_tenant_id

    tenant_uuid = UUID(tenant_id)
    agent_uuid = UUID(agent_id)

    tenant = app_store.get_tenant(tenant_uuid)
    tenant_settings = tenant.settings if tenant else {}

    existing_suppression = app_store.find_contact_suppression(
        tenant_uuid,
        "sms",
        phone=From,
    )
    if existing_suppression:
        app_store.create_audit_log(
            event_type="contact_suppression.inbound_ignored",
            tenant_id=tenant_uuid,
            details={
                "channel": "sms",
                "contact_type": existing_suppression.contact_type,
                "source": "twilio_sms_webhook",
                "suppression_id": str(existing_suppression.id),
                "value": existing_suppression.value,
            },
        )
        return Response(content="<Response/>", media_type="application/xml")

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

    from app.service_factory import get_agent_orchestrator
    orchestrator = get_agent_orchestrator()
    orchestrator_result = await orchestrator.process_message(
        tenant_id=tenant_uuid,
        agent_id=agent_uuid,
        conversation_id=conversation_uuid,
        customer_message=Body,
        channel="sms",
    )
    response_text = orchestrator_result.response_text

    app_store.record_chat_turn_background(
        tenant_id=tenant_uuid,
        agent_id=agent_uuid,
        conversation_id=conversation_uuid,
        channel="sms",
        customer_text=Body,
        agent_response_text=response_text,
        confidence_score=orchestrator_result.confidence_score,
        forced_status=orchestrator_result.forced_status,
        forced_resolution_status=orchestrator_result.forced_resolution_status,
    )

    if orchestrator_result.guardrail_code == "opt_out_requested":
        app_store.record_contact_suppression(
            tenant_uuid,
            "sms",
            "phone",
            From,
            reason="opt_out_requested",
            source="twilio_sms_guardrail",
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
                            from app.service_factory import get_agent_orchestrator
                            orchestrator = get_agent_orchestrator()
                            orchestrator_result = await orchestrator.process_message(
                                tenant_id=tenant_uuid,
                                agent_id=agent_uuid,
                                conversation_id=conversation_uuid,
                                customer_message=customer_text,
                                channel="voice",
                            )
                            response_text = orchestrator_result.response_text
                            app_store.record_chat_turn_background(
                                tenant_id=tenant_uuid,
                                agent_id=agent_uuid,
                                conversation_id=conversation_uuid,
                                channel="voice",
                                customer_text=customer_text,
                                agent_response_text=response_text,
                                confidence_score=orchestrator_result.confidence_score,
                                forced_status=orchestrator_result.forced_status,
                                forced_resolution_status=orchestrator_result.forced_resolution_status,
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
        logger.error("WebSocket error: %s", e)

@router.websocket("/webhooks/twilio/stream/{agent_id}")
async def twilio_media_stream_websocket(
    websocket: WebSocket,
    agent_id: str,
    tenant_id: str | None = None,
    app_store: AppStore = Depends(get_app_store),
    settings: Settings = Depends(get_settings),
    speech_service: SpeechService = Depends(get_speech_service),
    service: VoiceSessionService = Depends(get_voice_service),
    streaming_stt: StreamingSTT = Depends(get_streaming_stt),
    streaming_tts: StreamingTTS = Depends(get_streaming_tts),
) -> None:
    """Real-time Twilio Media Stream WebSocket connection with Full-duplex and Barge-in."""
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
    tts_task = None
    stt_receive_task = None

    from app.vad import VoiceActivityDetector
    vad = VoiceActivityDetector()

    async def play_tts(text: str, voice_id: str) -> None:
        nonlocal stream_sid
        if not stream_sid:
            return
        try:
            async for chunk in streaming_tts.generate_audio_stream(text, voice=voice_id, response_format="mulaw"):
                encoded_chunk = base64.b64encode(chunk).decode("utf-8")
                await websocket.send_text(json.dumps({
                    "event": "media",
                    "streamSid": stream_sid,
                    "media": {
                        "payload": encoded_chunk
                    }
                }))
        except asyncio.CancelledError:
            logger.info("TTS playback cancelled due to barge-in")
            raise
        except Exception as e:
            logger.error("Error in play_tts: %s", e)

    async def stt_receiver():
        nonlocal tts_task, stream_sid
        try:
            while True:
                is_final, customer_text = await streaming_stt.receive_transcript()
                if is_final and customer_text:
                    logger.info("STT recognized: %s", customer_text)

                    # Barge-in: Cancel active playback (in case VAD missed it or it's just safer)
                    if tts_task and not tts_task.done():
                        tts_task.cancel()
                        if stream_sid:
                            await websocket.send_text(json.dumps({
                                "event": "clear",
                                "streamSid": stream_sid
                            }))

                    # Run Orchestrator
                    from app.service_factory import get_agent_orchestrator
                    orchestrator = get_agent_orchestrator()
                    orchestrator_result = await orchestrator.process_message(
                        tenant_id=tenant_uuid,
                        agent_id=agent_uuid,
                        conversation_id=conversation_uuid,
                        customer_message=customer_text,
                        channel="sip",
                    )
                    response_text = orchestrator_result.response_text

                    app_store.record_chat_turn_background(
                        tenant_id=tenant_uuid,
                        agent_id=agent_uuid,
                        conversation_id=conversation_uuid,
                        channel="sip",
                        customer_text=customer_text,
                        agent_response_text=response_text,
                        confidence_score=orchestrator_result.confidence_score,
                        forced_status=orchestrator_result.forced_status,
                        forced_resolution_status=orchestrator_result.forced_resolution_status,
                    )
                    try:
                        service.record_voice_turn(
                            tenant_id=tenant_id,
                            session_id=session_id,
                            customer_text=customer_text,
                            assistant_text=response_text,
                        )
                    except InvalidVoiceTransition as exc:
                        logger.warning("Could not record WebSocket voice session turn: %s", exc)

                    # Start playing TTS
                    agent = app_store.get_agent(tenant_uuid, agent_uuid)
                    voice_id = agent.voice_id if agent else "alloy"
                    tts_task = asyncio.create_task(play_tts(response_text, voice_id))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Error in stt_receiver: %s", e)

    try:
        async with streaming_stt:
            stt_receive_task = asyncio.create_task(stt_receiver())
            
            while True:
                data = await websocket.receive_text()
                msg = json.loads(data)

                if msg["event"] == "start":
                    stream_sid = msg["start"]["streamSid"]
                    logger.info("Twilio stream started: %s", stream_sid)

                elif msg["event"] == "media":
                    payload = msg["media"]["payload"]
                    chunk = base64.b64decode(payload)

                    # Process with VAD for instant barge-in detection
                    barge_in, _ = vad.process_ulaw_chunk(chunk)
                    if barge_in:
                        if tts_task and not tts_task.done():
                            logger.info("VAD Barge-in detected! Stopping TTS.")
                            tts_task.cancel()
                            if stream_sid:
                                await websocket.send_text(json.dumps({
                                    "event": "clear",
                                    "streamSid": stream_sid
                                }))

                    # Send to StreamingSTT
                    await streaming_stt.send_audio(chunk)

                elif msg["event"] == "stop":
                    logger.info("Twilio stream stopped: %s", stream_sid)
                    break

    except WebSocketDisconnect:
        logger.info("Twilio WebSocket disconnected")
    except Exception as e:
        logger.error("Twilio WebSocket error: %s", e)
    finally:
        if tts_task and not tts_task.done():
            tts_task.cancel()
        if stt_receive_task and not stt_receive_task.done():
            stt_receive_task.cancel()
