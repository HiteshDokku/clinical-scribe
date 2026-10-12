import os
import torch
import torchaudio
import numpy as np
from speechbrain.inference.speaker import EncoderClassifier

_SHARED_CLASSIFIER = None

def get_shared_classifier():
    global _SHARED_CLASSIFIER
    if _SHARED_CLASSIFIER is None:
        base_dir = os.path.dirname(__file__)
        model_dir = os.path.abspath(os.path.join(base_dir, "..", "models", "spkrec-ecapa-voxceleb"))
        os.environ["HF_HUB_OFFLINE"] = "1"
        _SHARED_CLASSIFIER = EncoderClassifier.from_hparams(
            source=model_dir,
            savedir=model_dir,
            run_opts={"device": "cpu"}
        )
    return _SHARED_CLASSIFIER

class SpeakerTracker:
    def __init__(self, classifier=None):
        self.c1 = None
        self.c2 = None
        self.learning_rate = 0.1
        self.threshold = 0.5  # Cosine distance threshold (1 - cos_sim)
        self.classifier = classifier or get_shared_classifier()

    def extract_features(self, audio_bytes: bytes) -> np.ndarray:
        # 16-bit PCM mono 16kHz
        data = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
        if len(data) == 0:
            return np.zeros(192)
            
        # Normalize audio
        data = data / 32768.0
        
        # SpeechBrain expects shape (batch, time)
        tensor = torch.from_numpy(data).unsqueeze(0)
        
        # Get embedding (batch, time, feat) -> (feat,)
        with torch.no_grad():
            embeddings = self.classifier.encode_batch(tensor)
            emb = embeddings.squeeze().numpy()
            
        # Normalize embedding for cosine similarity
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm
            
        return emb

    def assign_speaker(self, audio_bytes: bytes) -> tuple[str, float]:
        """
        Returns (speaker_label, confidence)
        """
        # Minimum audio length for reliable ECAPA is ~1 second (16000 samples = 32000 bytes)
        is_short = len(audio_bytes) < 32000
        
        features = self.extract_features(audio_bytes)
        
        if self.c1 is None:
            self.c1 = features
            return "spk_a", 0.0 if is_short else 1.0
            
        if self.c2 is None:
            # Check if it's far enough from c1 to be c2 using cosine distance
            # Since features are normalized, cosine distance = 1 - dot_product
            cos_sim = np.dot(features, self.c1)
            dist = 1.0 - cos_sim
            
            if dist > self.threshold:
                if not is_short:
                    self.c2 = features
                return "spk_b", 0.0 if is_short else 1.0
            else:
                if not is_short:
                    self.c1 = (1 - self.learning_rate) * self.c1 + self.learning_rate * features
                    # re-normalize
                    self.c1 = self.c1 / np.linalg.norm(self.c1)
                return "spk_a", 0.0 if is_short else cos_sim
                
        # Both centroids exist, find closest
        sim1 = np.dot(features, self.c1)
        sim2 = np.dot(features, self.c2)
        
        confidence = abs(sim1 - sim2) # difference in similarity is our confidence
        
        if sim1 > sim2:
            if not is_short:
                self.c1 = (1 - self.learning_rate) * self.c1 + self.learning_rate * features
                self.c1 = self.c1 / np.linalg.norm(self.c1)
            return "spk_a", 0.0 if is_short else confidence
        else:
            if not is_short:
                self.c2 = (1 - self.learning_rate) * self.c2 + self.learning_rate * features
                self.c2 = self.c2 / np.linalg.norm(self.c2)
            return "spk_b", 0.0 if is_short else confidence
