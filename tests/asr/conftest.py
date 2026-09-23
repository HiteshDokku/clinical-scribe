import pytest
import numpy as np

@pytest.fixture
def fixture_wav_bytes():
    # 10s of 16kHz mono, mostly silence with a sine wave burst
    sample_rate = 16000
    duration = 10
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    
    # Silence
    audio = np.zeros_like(t)
    
    # 2s pseudo-speech burst at t=4s (150Hz fundamental + formants + 4Hz syllable modulation)
    burst_start = int(4 * sample_rate)
    burst_end = int(6 * sample_rate)
    t_burst = t[burst_start:burst_end]
    burst = (
        np.sin(2 * np.pi * 150 * t_burst) +
        0.5 * np.sin(2 * np.pi * 500 * t_burst) +
        0.2 * np.sin(2 * np.pi * 1500 * t_burst)
    )
    burst = burst * (0.5 + 0.5 * np.sin(2 * np.pi * 4 * t_burst))  # amplitude modulation
    
    # Normalize and scale
    burst = burst / np.max(np.abs(burst)) * 0.5
    audio[burst_start:burst_end] = burst
    
    # Convert to PCM16
    audio_int16 = (audio * 32767).astype(np.int16)
    return audio_int16.tobytes()
