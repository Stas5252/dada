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


def get_speech_service() -> SpeechService:
    return SpeechService()
