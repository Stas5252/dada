import asyncio
import logging
from typing import Any
from uuid import UUID

from app.contracts.voice import VoiceEvent, VoiceSessionEvent
from app.orchestrator import AgentOrchestrator
from app.settings import get_settings
from app.speech_service import get_streaming_stt, get_streaming_tts
from app.store_factory import get_app_store
from app.service_factory import get_voice_service

logger = logging.getLogger(__name__)


class AsteriskARIService:
    """
    Service to interact with Asterisk via ARI (Asterisk REST Interface) 
    and WebSocket for events. This manages the full lifecycle of a SIP call.
    """
    def __init__(self):
        self.settings = get_settings()
        self.app_store = get_app_store()
        self.voice_service = get_voice_service()
        self.stt = get_streaming_stt()
        self.tts = get_streaming_tts()

    async def connect_websocket(self):
        """Connects to the Asterisk ARI WebSocket to listen for Stasis events."""
        logger.info("Connecting to Asterisk ARI WebSocket (Mock)...")
        # In a real implementation, we would use aiohttp to connect to:
        # ws://<asterisk_host>:<port>/ari/events?api_key=<key>&app=<app>
        await asyncio.sleep(1)
        logger.info("Connected to Asterisk ARI WebSocket (Mock).")

    async def _handle_stasis_start(self, channel_id: str, caller_number: str, tenant_id: str, agent_id: str):
        """Handles an incoming SIP call directed to the Stasis application."""
        logger.info(f"[ARI] Incoming call on channel {channel_id} from {caller_number}")
        
        # 1. Answer the call via ARI REST API
        # ari.channels.answer(channelId=channel_id)
        
        # 2. Setup Voice Session
        session_id = channel_id
        try:
            self.voice_service.get_or_start_session(tenant_id, session_id)
        except Exception as e:
            logger.error(f"Failed to start voice session: {e}")
            # ari.channels.hangup(channelId=channel_id)
            return

        tenant_uuid = UUID(tenant_id)
        agent_uuid = UUID(agent_id)
        conversation_uuid = UUID(int=0)  # Use a consistent mock conversation ID for now

        # 3. Initial Greeting
        orchestrator = AgentOrchestrator(store=self.app_store, settings=self.settings)
        # Mocking an initial event if needed, or we just rely on first text
        
        greeting = "Здравствуйте! Я ИИ-ассистент. Чем я могу помочь?"
        await self._stream_tts_to_channel(channel_id, greeting)

        # 4. Start processing incoming audio stream (RTP -> WebSocket)
        # In real ARI, we would establish an ExternalMedia channel to receive RTP
        # Here we mock the stream loop.
        try:
            # Fake receiving audio chunks
            for _ in range(10):
                await asyncio.sleep(0.5) # simulate audio chunk arrival
                audio_chunk = b"\x00" * 4096
                is_final, text = await self.stt.process_audio_stream(audio_chunk)
                
                if is_final and text:
                    logger.info(f"[ARI] Final STT detected: {text}")
                    
                    # 5. Process through LLM Orchestrator
                    orchestrator_result = await orchestrator.process_message(
                        tenant_id=tenant_uuid,
                        agent_id=agent_uuid,
                        conversation_id=conversation_uuid,
                        customer_message=text,
                        channel="voice",
                    )
                    response_text = orchestrator_result.response_text
                    
                    # Record turn
                    self.app_store.record_chat_turn(
                        tenant_id=tenant_uuid,
                        agent_id=agent_uuid,
                        conversation_id=conversation_uuid,
                        channel="voice",
                        customer_text=text,
                        agent_response_text=response_text,
                        confidence_score=orchestrator_result.confidence_score,
                    )
                    
                    self.voice_service.record_voice_turn(
                        tenant_id=tenant_id,
                        session_id=session_id,
                        customer_text=text,
                        assistant_text=response_text,
                    )

                    # 6. Stream TTS back to Asterisk
                    await self._stream_tts_to_channel(channel_id, response_text)

        except Exception as e:
            logger.error(f"Error in stream loop: {e}")
        finally:
            logger.info(f"[ARI] Call ended for channel {channel_id}")
            # ari.channels.hangup(channelId=channel_id)
            try:
                self.voice_service.apply_event(session_id, VoiceSessionEvent(
                    tenant_id=tenant_id,
                    event=VoiceEvent.END_CALL
                ))
            except Exception:
                pass

    async def _stream_tts_to_channel(self, channel_id: str, text: str):
        """Generates TTS stream and pipes it to Asterisk channel playback."""
        logger.info(f"[ARI] Streaming TTS for: '{text}' to channel {channel_id}")
        async for audio_chunk in self.tts.generate_audio_stream(text):
            # In a real implementation: write to the ExternalMedia socket
            # or use ARI play with media URI
            pass
        logger.info(f"[ARI] TTS streaming complete for channel {channel_id}")

    async def run(self):
        """Main event loop for ARI service."""
        await self.connect_websocket()
        while True:
            # Listen for ARI events (Mock)
            await asyncio.sleep(3600)


def get_asterisk_ari_service() -> AsteriskARIService:
    return AsteriskARIService()
