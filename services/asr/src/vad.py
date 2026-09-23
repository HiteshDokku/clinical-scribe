import numpy as np
import torch
from silero_vad import load_silero_vad

class VADGater:
    def __init__(self):
        # Using silero-vad >= 5.1
        self.model = load_silero_vad()
        
    def is_speech(self, chunk_bytes: bytes, sample_rate: int = 16000, threshold: float = 0.5) -> bool:
        """
        Takes raw PCM16-LE 16kHz mono bytes, converts to f32 float tensor,
        and returns True if speech is detected above threshold.
        Handles arbitrary sized inputs by chunking into 512-sample frames.
        """
        if not chunk_bytes:
            return False
            
        # Convert PCM16 to float32 numpy array normalized to [-1, 1]
        audio_int16 = np.frombuffer(chunk_bytes, dtype=np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        
        # Silero VAD expects chunks of exactly 512 samples for 16kHz
        frame_size = 512
        max_prob = 0.0
        
        # Process in windows
        for i in range(0, len(audio_float32), frame_size):
            frame = audio_float32[i:i + frame_size]
            
            # If the last frame is smaller than 512, pad it with zeros
            if len(frame) < frame_size:
                padded = np.zeros(frame_size, dtype=np.float32)
                padded[:len(frame)] = frame
                frame = padded
                
            audio_tensor = torch.from_numpy(frame)
            prob = self.model(audio_tensor, sample_rate).item()
            if prob > max_prob:
                max_prob = prob
                
        return max_prob > threshold
