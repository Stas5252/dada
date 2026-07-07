import audioop
import logging

logger = logging.getLogger(__name__)


class VoiceActivityDetector:
    def __init__(self, sample_rate: int = 8000, aggressiveness: int = 2) -> None:
        """
        :param sample_rate: The sample rate of the PCM audio (Twilio uses 8000)
        :param aggressiveness: Not used for RMS VAD, kept for compatibility.
        """
        self.sample_rate = sample_rate
        self.frame_duration_ms = 20
        self.frame_size_bytes = int(sample_rate * (self.frame_duration_ms / 1000.0) * 2)

        # Buffer for incoming audio that might not align with frame size
        self.pcm_buffer = bytearray()

        self.speech_frames_threshold = 15
        self.speech_frames_count = 0

        self.silence_frames_threshold = 30
        self.silence_frames_count = 0
        
        self.is_speaking = False
        
        # Energy threshold for 16-bit PCM (max is 32768)
        # 500 is a reasonable baseline for speech in Twilio streams
        self.energy_threshold = 500

    def process_ulaw_chunk(self, ulaw_chunk: bytes) -> tuple[bool, bool]:
        """
        Process a chunk of mu-law audio from Twilio.
        Returns a tuple: (barge_in_triggered, speech_stopped)
        """
        if not ulaw_chunk:
            return False, False

        # Decode mu-law to 16-bit linear PCM
        try:
            pcm_chunk = audioop.ulaw2lin(ulaw_chunk, 2)
        except Exception as e:
            logger.error("Failed to decode mu-law audio: %s", e)
            return False, False

        self.pcm_buffer.extend(pcm_chunk)

        barge_in_triggered = False
        speech_stopped = False

        # Process as many full frames as we have in the buffer
        while len(self.pcm_buffer) >= self.frame_size_bytes:
            frame = bytes(self.pcm_buffer[:self.frame_size_bytes])
            self.pcm_buffer = self.pcm_buffer[self.frame_size_bytes:]

            try:
                # Calculate RMS (Root Mean Square) energy of the frame
                energy = audioop.rms(frame, 2)
                is_speech = energy > self.energy_threshold
            except Exception as e:
                logger.warning("VAD RMS error on frame: %s", e)
                continue

            if is_speech:
                self.silence_frames_count = 0
                if not self.is_speaking:
                    self.speech_frames_count += 1
                    if self.speech_frames_count >= self.speech_frames_threshold:
                        self.is_speaking = True
                        barge_in_triggered = True
                        logger.info("VAD detected solid speech (barge-in triggered) with energy %d", energy)
            else:
                self.speech_frames_count = 0
                if self.is_speaking:
                    self.silence_frames_count += 1
                    if self.silence_frames_count >= self.silence_frames_threshold:
                        self.is_speaking = False
                        speech_stopped = True
                        logger.info("VAD detected end of speech")

        return barge_in_triggered, speech_stopped

    def reset(self) -> None:
        self.pcm_buffer.clear()
        self.speech_frames_count = 0
        self.silence_frames_count = 0
        self.is_speaking = False
