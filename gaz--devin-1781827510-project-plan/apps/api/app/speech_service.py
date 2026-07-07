import io
from collections.abc import AsyncGenerator
from typing import Literal, cast
import logging

from app.settings import get_settings

logger = logging.getLogger(__name__)

OpenAITTSResponseFormat = Literal["mp3", "opus", "aac", "flac", "wav", "pcm"]


class SpeechService:
    def __init__(self) -> None:
        pass

    async def speech_to_text(self, audio_bytes: bytes, filename: str = "audio.wav") -> str:
        """Convert audio to text using OpenAI Whisper."""
        settings = get_settings()
        if not settings.openai_api_key:
            return "[STT Mock: Cannot process audio without OpenAI API Key]"

        import openai

        client = openai.AsyncClient(api_key=settings.openai_api_key)

        # Whisper requires a file-like object with a name
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = filename

        try:
            response = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ru",
            )
            return response.text
        except Exception as e:
            logger.error(f"STT Error: {e}")
            return f"[STT Error: {e}]"

    async def text_to_speech(self, text: str, voice: str = "alloy") -> bytes:
        """Convert text to speech audio bytes using OpenAI TTS."""
        settings = get_settings()
        if not settings.openai_api_key:
            # Return an empty mock audio
            return b""

        import openai

        client = openai.AsyncClient(api_key=settings.openai_api_key)

        try:
            response = await client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text,
            )
            return response.content
        except Exception as e:
            logger.error(f"TTS Error: {e}")
            return b""


class StreamingSTT:
    """Abstract interface for streaming Speech-to-Text."""
    async def connect(self) -> None:
        pass
        
    async def disconnect(self) -> None:
        pass
        
    async def send_audio(self, audio_chunk: bytes) -> None:
        raise NotImplementedError
        
    async def receive_transcript(self) -> tuple[bool, str]:
        """Returns (is_final, text)"""
        raise NotImplementedError

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()


class MockStreamingSTT(StreamingSTT):
    """A mock implementation for local MVP testing."""
    def __init__(self) -> None:
        self.buffer = bytearray()
        import asyncio
        self.queue = asyncio.Queue()
        
    async def send_audio(self, audio_chunk: bytes) -> None:
        self.buffer.extend(audio_chunk)
        if len(self.buffer) > 16000:
            await self.queue.put((True, "Привет, я хочу заказать пиццу"))
            self.buffer.clear()
            
    async def receive_transcript(self) -> tuple[bool, str]:
        return await self.queue.get()


class DeepgramStreamingSTT(StreamingSTT):
    def __init__(self, api_key: str):
        self.api_key = api_key
        import websockets
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._url = "wss://api.deepgram.com/v1/listen?encoding=mulaw&sample_rate=8000&channels=1&language=ru&interim_results=true&endpointing=300"
        import asyncio
        self._queue = asyncio.Queue()
        self._receive_task: asyncio.Task | None = None

    async def connect(self) -> None:
        import websockets
        import asyncio
        import logging
        self._ws = await websockets.connect(
            self._url,
            extra_headers={"Authorization": f"Token {self.api_key}"}
        )
        
        async def receiver():
            import json
            try:
                async for message in self._ws:
                    data = json.loads(message)
                    if data.get("type") == "Results":
                        is_final = data["is_final"]
                        transcript = data["channel"]["alternatives"][0]["transcript"]
                        if transcript:
                            await self._queue.put((is_final, transcript))
            except Exception as e:
                logging.getLogger(__name__).warning("Deepgram socket closed: %s", e)
                
        self._receive_task = asyncio.create_task(receiver())

    async def disconnect(self) -> None:
        if self._receive_task:
            self._receive_task.cancel()
        if self._ws:
            await self._ws.close()

    async def send_audio(self, audio_chunk: bytes) -> None:
        if self._ws:
            await self._ws.send(audio_chunk)

    async def receive_transcript(self) -> tuple[bool, str]:
        return await self._queue.get()


def add_wav_header_mulaw(audio_bytes: bytes, sample_rate: int = 8000) -> bytes:
    """
    Prepends a 44-byte WAV header specifying G.711 mu-law format (format code 7)
    to a raw mu-law audio byte stream.
    """
    n_channels = 1
    sample_width = 1 # 8-bit log-compressed mulaw
    
    header = bytearray(44)
    
    # RIFF chunk
    header[0:4] = b'RIFF'
    file_size = 36 + len(audio_bytes)
    header[4:8] = file_size.to_bytes(4, 'little')
    header[8:12] = b'WAVE'
    
    # fmt chunk
    header[12:16] = b'fmt '
    header[16:20] = (16).to_bytes(4, 'little') # Subchunk1Size
    header[20:22] = (7).to_bytes(2, 'little')  # WAVE_FORMAT_MULAW (7)
    header[22:24] = n_channels.to_bytes(2, 'little')
    header[24:28] = sample_rate.to_bytes(4, 'little')
    byte_rate = sample_rate * n_channels * sample_width
    header[28:32] = byte_rate.to_bytes(4, 'little')
    block_align = n_channels * sample_width
    header[32:34] = block_align.to_bytes(2, 'little')
    bits_per_sample = 8
    header[34:36] = bits_per_sample.to_bytes(2, 'little')
    
    # data chunk
    header[36:40] = b'data'
    header[40:44] = len(audio_bytes).to_bytes(4, 'little')
    
    return bytes(header) + audio_bytes


class OpenAIStreamingSTT(StreamingSTT):
    """An implementation that buffers audio and uses OpenAI Whisper."""
    def __init__(self) -> None:
        self.buffer = bytearray()
        self.speech_service = get_speech_service()
        
    async def process_audio_stream(self, audio_chunk: bytes) -> tuple[bool, str]:
        self.buffer.extend(audio_chunk)
        # Simulate simple VAD by waiting for 3 seconds of audio (approx 24000 bytes at 8kHz 8-bit mulaw)
        if len(self.buffer) > 24000:
            audio_data = add_wav_header_mulaw(bytes(self.buffer))
            self.buffer.clear()
            # Send to Whisper
            text = await self.speech_service.speech_to_text(audio_data)
            return True, text
        return False, ""


class StreamingTTS:
    """Abstract interface for streaming Text-to-Speech."""
    async def generate_audio_stream(self, text: str, voice: str = "alloy", response_format: str = "wav") -> AsyncGenerator[bytes, None]:
        raise NotImplementedError
        yield b""


class MockStreamingTTS(StreamingTTS):
    """A mock implementation for local MVP testing."""
    async def generate_audio_stream(self, text: str, voice: str = "alloy", response_format: str = "wav") -> AsyncGenerator[bytes, None]:
        import asyncio
        for _ in range(3):
            await asyncio.sleep(0.1)
            yield b"\x00" * 1024


class OpenAIStreamingTTS(StreamingTTS):
    """An implementation that uses OpenAI TTS API with streaming response."""
    async def generate_audio_stream(self, text: str, voice: str = "alloy", response_format: str = "wav") -> AsyncGenerator[bytes, None]:
        settings = get_settings()
        if not settings.openai_api_key:
            yield b""
            return
            
        import audioop

        import openai
        
        client = openai.AsyncClient(api_key=settings.openai_api_key)
        allowed_formats = {"mp3", "opus", "aac", "flac", "wav", "pcm"}
        openai_format: OpenAITTSResponseFormat
        if response_format == "mulaw":
            openai_format = "pcm"
        elif response_format in allowed_formats:
            openai_format = cast(OpenAITTSResponseFormat, response_format)
        else:
            openai_format = "wav"
        
        try:
            # We use the raw client to stream the response chunks
            async with client.audio.speech.with_streaming_response.create(
                model="tts-1",
                voice=voice,
                input=text,
                response_format=openai_format
            ) as response:
                chunk_size = 6000 if response_format == "mulaw" else 4096
                leftover = b""
                async for chunk in response.iter_bytes(chunk_size=chunk_size):
                    if response_format == "mulaw":
                        data_to_process = leftover + chunk
                        length = len(data_to_process)
                        process_len = (length // 6) * 6
                        if process_len > 0:
                            chunk_to_convert = data_to_process[:process_len]
                            leftover = data_to_process[process_len:]
                            pcm_8k, _ = audioop.ratecv(chunk_to_convert, 2, 1, 24000, 8000, None)
                            mulaw_chunk = audioop.lin2ulaw(pcm_8k, 2)
                            yield mulaw_chunk
                        else:
                            leftover = data_to_process
                    else:
                        yield chunk
                if response_format == "mulaw" and leftover:
                    pad_len = 6 - len(leftover)
                    padded_leftover = leftover + (b"\x00" * pad_len)
                    pcm_8k, _ = audioop.ratecv(padded_leftover, 2, 1, 24000, 8000, None)
                    mulaw_chunk = audioop.lin2ulaw(pcm_8k, 2)
                    yield mulaw_chunk
        except Exception as e:
            logger.error(f"Streaming TTS Error: {e}")
            yield b""



class YandexStreamingSTT(StreamingSTT):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.buffer = bytearray()
        import asyncio
        self.queue = asyncio.Queue()
        self.url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize?lang=ru-RU&format=lpcm&sampleRateHertz=8000"
        
    async def send_audio(self, audio_chunk: bytes) -> None:
        self.buffer.extend(audio_chunk)
        if len(self.buffer) > 24000:
            import httpx
            import audioop
            pcm_8k, _ = audioop.ulaw2lin(bytes(self.buffer), 2)
            self.buffer.clear()
            
            from app.security import SSRFTransport
            async with httpx.AsyncClient(transport=SSRFTransport()) as client:
                try:
                    resp = await client.post(
                        self.url,
                        headers={"Authorization": f"Api-Key {self.api_key}"},
                        content=pcm_8k
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    text = data.get("result", "")
                    if text:
                        await self.queue.put((True, text))
                except Exception as e:
                    logger.error(f"Yandex STT Error: {e}")

    async def receive_transcript(self) -> tuple[bool, str]:
        return await self.queue.get()


class YandexStreamingTTS(StreamingTTS):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
        
    async def generate_audio_stream(self, text: str, voice: str = "alena", response_format: str = "wav") -> AsyncGenerator[bytes, None]:
        import httpx
        import audioop
        
        data = {
            "text": text,
            "lang": "ru-RU",
            "voice": voice,
            "format": "lpcm",
            "sampleRateHertz": "8000"
        }
        
        from app.security import SSRFTransport
        async with httpx.AsyncClient(transport=SSRFTransport()) as client:
            try:
                async with client.stream(
                    "POST",
                    self.url,
                    headers={"Authorization": f"Api-Key {self.api_key}"},
                    data=data
                ) as response:
                    response.raise_for_status()
                    
                    leftover = b""
                    async for chunk in response.aiter_bytes(chunk_size=4096):
                        data_to_process = leftover + chunk
                        length = len(data_to_process)
                        process_len = (length // 2) * 2
                        if process_len > 0:
                            chunk_to_convert = data_to_process[:process_len]
                            leftover = data_to_process[process_len:]
                            
                            mulaw_chunk = audioop.lin2ulaw(chunk_to_convert, 2)
                            yield mulaw_chunk
                        else:
                            leftover = data_to_process
                            
                    if leftover:
                        pad_len = 2 - len(leftover)
                        padded_leftover = leftover + (b"\x00" * pad_len)
                        mulaw_chunk = audioop.lin2ulaw(padded_leftover, 2)
                        yield mulaw_chunk
            except Exception as e:
                logger.error(f"Yandex TTS Error: {e}")
                yield b""

def get_speech_service() -> SpeechService:
    return SpeechService()


def get_streaming_stt() -> StreamingSTT:
    settings = get_settings()
    if settings.yandex_api_key:
        return YandexStreamingSTT(settings.yandex_api_key)
    if settings.deepgram_api_key:
        return DeepgramStreamingSTT(settings.deepgram_api_key)
    # Fallback to mock
    return MockStreamingSTT()


def get_streaming_tts() -> StreamingTTS:
    settings = get_settings()
    if settings.yandex_api_key:
        return YandexStreamingTTS(settings.yandex_api_key)
    if settings.openai_api_key:
        return OpenAIStreamingTTS()
    return MockStreamingTTS()

