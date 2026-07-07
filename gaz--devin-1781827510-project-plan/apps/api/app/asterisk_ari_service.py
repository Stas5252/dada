import asyncio
import contextlib
import json
import logging
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

import aiohttp

from app.contracts.voice import VoiceEvent, VoiceSessionEvent
from app.orchestrator import AgentOrchestrator
from app.service_factory import get_voice_service
from app.settings import get_settings
from app.speech_service import get_streaming_stt, get_streaming_tts
from app.store_factory import get_app_store

logger = logging.getLogger(__name__)


class AsteriskARIService:
    """
    Service to interact with Asterisk via ARI (Asterisk REST Interface) 
    and WebSocket for events. This manages the full lifecycle of a SIP call.
    """
    def __init__(self) -> None:
        self.settings = get_settings()
        self.app_store = get_app_store()
        self.voice_service = get_voice_service()
        self.session: aiohttp.ClientSession | None = None
        self.ari_base_url = "http://localhost:8088/ari"
        self.app_name = "callforce"


    async def _api_post(self, path: str, params: dict[str, str] | None = None) -> None:
        if not self.session:
            return
        auth = aiohttp.BasicAuth(
            self.settings.asterisk_ari_username, self.settings.asterisk_ari_password
        )
        url = f"{self.ari_base_url}{path}"
        try:
            async with self.session.post(url, auth=auth, params=params) as resp:
                resp.raise_for_status()
        except Exception as e:
            logger.error(f"ARI API Error on POST {path}: {e}")

    async def connect_websocket(self) -> None:
        """Connects to the Asterisk ARI WebSocket to listen for Stasis events."""
        if not self.settings.asterisk_ari_username:
            logger.warning("Asterisk ARI credentials missing, running in mock mode.")
            await asyncio.sleep(1)
            return

        self.session = aiohttp.ClientSession()
        ws_url = f"ws://localhost:8088/ari/events?api_key={self.settings.asterisk_ari_username}:{self.settings.asterisk_ari_password}&app={self.app_name}"
        
        while True:
            try:
                logger.info("Connecting to Asterisk ARI WebSocket...")
                async with self.session.ws_connect(ws_url) as ws:
                    logger.info("Connected to Asterisk ARI WebSocket.")
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            await self._handle_event(data)
                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            logger.error(f"ARI WebSocket closed or error: {msg}")
                            break
            except Exception as e:
                logger.error(f"Failed to connect to Asterisk ARI WebSocket: {e}")
            
            logger.info("Reconnecting to ARI in 5 seconds...")
            await asyncio.sleep(5)

    async def _handle_event(self, event: dict[str, Any]) -> None:
        event_type = event.get("type")
        if event_type == "StasisStart":
            channel = event.get("channel", {})
            channel_id = channel.get("id")
            caller_number = channel.get("caller", {}).get("number", "Unknown")
            
            # Use demo tenant for now if not provided via SIP headers
            tenant_id = self.settings.demo_tenant_id
            
            # Find published SIP agent
            agents = self.app_store.list_agents(UUID(tenant_id))
            sip_agent = next((a for a in agents if a.status == "published" and a.channel == "sip"), None)
            agent_id = str(sip_agent.id) if sip_agent else str(UUID(int=0))

            asyncio.create_task(self._handle_stasis_start(channel_id, caller_number, tenant_id, agent_id))
            
        elif event_type == "StasisEnd":
            channel = event.get("channel", {})
            channel_id = channel.get("id")
            logger.info(f"[ARI] Call ended for channel {channel_id}")

    async def _handle_stasis_start(self, channel_id: str, caller_number: str, tenant_id: str, agent_id: str) -> None:
        """Handles an incoming SIP call directed to the Stasis application."""
        logger.info(f"[ARI] Incoming call on channel {channel_id} from {caller_number}")
        
        if self.session:
            await self._api_post(f"/channels/{channel_id}/answer")
        
        session_id = channel_id
        try:
            self.voice_service.get_or_start_session(tenant_id, session_id)
        except Exception as e:
            logger.error(f"Failed to start voice session: {e}")
            if self.session:
                await self._api_post(f"/channels/{channel_id}", params={"reason": "busy"})
            return

        tenant_uuid = UUID(tenant_id)
        agent_uuid = UUID(agent_id)
        conversation_uuid = uuid5(NAMESPACE_URL, f"asterisk_ari:{channel_id}")

        orchestrator = AgentOrchestrator(store=self.app_store, settings=self.settings)
        stt = get_streaming_stt()
        tts = get_streaming_tts()
        
        greeting = "Здравствуйте! Я ИИ-ассистент. Чем я могу помочь?"
        await self._stream_tts_to_channel(channel_id, greeting, tts)

        try:
            # We mock the stream loop since reading RTP requires ExternalMedia channels
            for _ in range(10):
                await asyncio.sleep(0.5) 
                audio_chunk = b"\x00" * 4096
                is_final, text = await stt.process_audio_stream(audio_chunk)
                
                if is_final and text:
                    logger.info(f"[ARI] Final STT detected: {text}")
                    
                    orchestrator_result = await orchestrator.process_message(
                        tenant_id=tenant_uuid,
                        agent_id=agent_uuid,
                        conversation_id=conversation_uuid,
                        customer_message=text,
                        channel="voice",
                    )
                    response_text = orchestrator_result.response_text
                    
                    self.app_store.record_chat_turn(
                        tenant_id=tenant_uuid,
                        agent_id=agent_uuid,
                        conversation_id=conversation_uuid,
                        channel="voice",
                        customer_text=text,
                        agent_response_text=response_text,
                        confidence_score=orchestrator_result.confidence_score,
                        forced_status=orchestrator_result.forced_status,
                        forced_resolution_status=orchestrator_result.forced_resolution_status,
                    )
                    
                    self.voice_service.record_voice_turn(
                        tenant_id=tenant_id,
                        session_id=session_id,
                        customer_text=text,
                        assistant_text=response_text,
                    )

                    await self._stream_tts_to_channel(channel_id, response_text, tts)

        except Exception as e:
            logger.error(f"Error in stream loop: {e}")
        finally:
            if self.session:
                await self._api_post(f"/channels/{channel_id}", params={"reason": "normal"})
                
            with contextlib.suppress(Exception):
                self.voice_service.apply_event(session_id, VoiceSessionEvent(
                    tenant_id=tenant_id,
                    event=VoiceEvent.END_CALL
                ))

    async def _stream_tts_to_channel(self, channel_id: str, text: str, tts: object) -> None:
        """Generates TTS stream and pipes it to Asterisk channel playback."""
        logger.info(f"[ARI] Streaming TTS for: '{text}' to channel {channel_id}")
        if self.session:
            # Tell Asterisk to play a specific URI or media
            # This is a simplification for the real playback command.
            pass
            
        # We cast object to any or use getattr to avoid type checking issues
        from typing import Any, cast
        async for _audio_chunk in cast(Any, tts).generate_audio_stream(text):
            pass
        logger.info(f"[ARI] TTS streaming complete for channel {channel_id}")


    async def run(self) -> None:
        """Main event loop for ARI service."""
        await self.connect_websocket()


def get_asterisk_ari_service() -> AsteriskARIService:
    return AsteriskARIService()
