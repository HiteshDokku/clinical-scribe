import os
import collections
from .vad import VADGater

class VadSegmenter:
    def __init__(self):
        self.vad_gater = VADGater()
        self.silence_timeout_ms = int(os.getenv("UTTERANCE_SILENCE_MS", "400"))
        # 1 ms of 16kHz 16-bit PCM mono = 16 samples * 2 bytes = 32 bytes
        self.silence_bytes_threshold = self.silence_timeout_ms * 32
        
        self.buffer = collections.deque()
        self.silence_bytes = 0
        self.is_utterance_active = False
        self.max_bytes = 15 * 1000 * 32 # 15 seconds max per utterance
        
    def process_chunk(self, chunk: bytes) -> tuple[bool, bytes | None, bytes | None]:
        """
        Returns (is_active, utterance_buffer_so_far, finalized_utterance)
        """
        is_speech = self.vad_gater.is_speech(chunk)
        
        if is_speech:
            self.is_utterance_active = True
            self.silence_bytes = 0
            self.buffer.append(chunk)
            
            # Force flush if buffer gets too large
            buffer_bytes = sum(len(c) for c in self.buffer)
            if buffer_bytes >= self.max_bytes:
                final_audio = b"".join(self.buffer)
                self.buffer.clear()
                self.is_utterance_active = False
                self.silence_bytes = 0
                return False, None, final_audio
                
            return True, b"".join(self.buffer), None
        else:
            if self.is_utterance_active:
                self.silence_bytes += len(chunk)
                self.buffer.append(chunk)
                
                if self.silence_bytes >= self.silence_bytes_threshold:
                    # Utterance closed!
                    final_audio = b"".join(self.buffer)
                    self.buffer.clear()
                    self.is_utterance_active = False
                    self.silence_bytes = 0
                    return False, None, final_audio
                else:
                    return True, b"".join(self.buffer), None
            else:
                return False, None, None
                
    def force_flush(self) -> bytes | None:
        if self.is_utterance_active:
            final_audio = b"".join(self.buffer)
            self.buffer.clear()
            self.is_utterance_active = False
            self.silence_bytes = 0
            return final_audio
        return None
