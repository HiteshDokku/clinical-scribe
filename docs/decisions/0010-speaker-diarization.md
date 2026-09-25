# 10. Speaker Diarization Strategy

Date: 2026-09-24

## Status
Accepted

## Context
The clinical note generation requires distinguishing between the clinician's speech and the patient's speech to accurately ground subjective and objective findings.
A robust diarization pipeline often relies on complex models like pyannote.audio. However, downloading pyannote models requires a gated Hugging Face token, which violates the strict offline, air-gapped egress policy of the clinical-scribe environment. Modifying the egress checks to allow Hugging Face downloads introduces security and reproducibility concerns.

## Decision
We implemented a lightweight, dependency-free online 2-speaker diarization approach.
The solution relies solely on `numpy` (which is already included) to extract audio features (Zero-Crossing Rate and Spectral Centroid) per VAD-approved chunk. These features are then clustered online into two centroids, mapping each chunk to either `clinician` or `patient`.

## Consequences
- **Positive:** Zero new dependencies, no model downloads, strictly adheres to offline requirements, and low latency for real-time streaming.
- **Negative:** Accuracy may be degraded compared to state-of-the-art embedding-based approaches, especially if the two speakers have similar vocal profiles.

## Upgrade Path
In the future, if the environment allows pre-baking pyannote models or downloading authorized weights via a private artifact registry, this lightweight diarizer can be hot-swapped for a deep learning-based embedding extractor (e.g. ECAPA-TDNN) while preserving the same `assign_speaker` interface.
