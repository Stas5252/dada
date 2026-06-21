import io

from app.settings import get_settings


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
    def __init__(self):
        self.buffer = bytearray()
        
    async def process_audio_stream(self, audio_chunk: bytes) -> tuple[bool, str]:
        self.buffer.extend(audio_chunk)
        # Simulate final text when enough data is collected
        if len(self.buffer) > 32000:  # arbitrary size
            self.buffer.clear()
            return True, "Привет, я хочу заказать пиццу"
        return False, ""


class StreamingTTS:
    """Abstract interface for streaming Text-to-Speech (e.g. Kokoro / XTTS)."""
    async def generate_audio_stream(self, text: str, voice: str = "alloy"):
        """
        Asynchronous generator yielding audio chunks.
        """
        raise NotImplementedError


class MockStreamingTTS(StreamingTTS):
    """A mock implementation for local MVP testing."""
    async def generate_audio_stream(self, text: str, voice: str = "alloy"):
        import asyncio
        # Yield 3 fake chunks
        for _ in range(3):
            await asyncio.sleep(0.1)
            yield b"\x00" * 1024


def get_speech_service() -> SpeechService:
    return SpeechService()


def get_streaming_stt() -> StreamingSTT:
    return MockStreamingSTT()


def get_streaming_tts() -> StreamingTTS:
    return MockStreamingTTS()
