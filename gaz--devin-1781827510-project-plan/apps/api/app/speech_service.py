import io
from collections.abc import AsyncGenerator
from typing import Literal, cast

from app.settings import get_settings

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
            print(f"STT Error: {e}")
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
            print(f"TTS Error: {e}")
            return b""


class StreamingSTT:
    """Abstract interface for streaming Speech-to-Text (e.g. Faster-Whisper)."""
    async def process_audio_stream(self, audio_chunk: bytes) -> tuple[bool, str]:
        """
        Processes an audio chunk.
        Returns (is_final, text). If is_final is True, the text is a completed utterance.
        """
        raise NotImplementedError


class MockStreamingSTT(StreamingSTT):
    """A mock implementation for local MVP testing."""
    def __init__(self) -> None:
        self.buffer = bytearray()
        
    async def process_audio_stream(self, audio_chunk: bytes) -> tuple[bool, str]:
        self.buffer.extend(audio_chunk)
        if len(self.buffer) > 32000:
            self.buffer.clear()
            return True, "Привет, я хочу заказать пиццу"
        return False, ""


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
            print(f"Streaming TTS Error: {e}")
            yield b""


def get_speech_service() -> SpeechService:
    return SpeechService()


def get_streaming_stt() -> StreamingSTT:
    settings = get_settings()
    if settings.openai_api_key:
        return OpenAIStreamingSTT()
    return MockStreamingSTT()


def get_streaming_tts() -> StreamingTTS:
    settings = get_settings()
    if settings.openai_api_key:
        return OpenAIStreamingTTS()
    return MockStreamingTTS()

