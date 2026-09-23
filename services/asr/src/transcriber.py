import os
import io
import numpy as np
from faster_whisper import WhisperModel
from .schemas import TranscriptEvent

class Transcriber:
    def __init__(self):
        model_size = os.getenv("WHISPER_MODEL", "tiny")
        # faster-whisper uses CTranslate2
        # Load once into memory
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def transcribe(self, audio_bytes: bytes, is_final: bool = False) -> list[TranscriptEvent]:
        """
        Transcribes PCM16-LE 16kHz audio bytes and yields a single combined event.
        """
        if not audio_bytes:
            return []
            
        # Convert PCM16 to float32 numpy array normalized to [-1, 1] for Whisper
        audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0

        segments_gen, _ = self.model.transcribe(
            audio_float32, 
            beam_size=1, 
            word_timestamps=False, 
            vad_filter=False,
            language="en"
        )
        segments = list(segments_gen)
        
        if not segments:
            return []
            
        full_text = " ".join([s.text.strip() for s in segments]).strip()
        if not full_text:
            return []
            
        start_ms = int(segments[0].start * 1000)
        end_ms = int(segments[-1].end * 1000)
        
        conf = sum([1.0 - getattr(s, 'no_speech_prob', 0.0) for s in segments]) / len(segments)
        
        event = TranscriptEvent(
            type="final" if is_final else "partial",
            text=full_text,
            start_ms=start_ms,
            end_ms=end_ms,
            confidence=conf,
            speaker=None
        )
        return [event]
