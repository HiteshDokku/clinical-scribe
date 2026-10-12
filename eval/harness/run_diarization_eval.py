import pathlib, shutil
def copy_instead(self, target, target_is_directory=False):
    try: shutil.copy(target, self)
    except: pass
pathlib.Path.symlink_to = copy_instead
import os
import json
import wave
import numpy as np
from services.asr.src.speaker_tracker import SpeakerTracker

def mix_audio(doc_file, pat_file, start_sec, end_sec):
    with wave.open(doc_file, 'rb') as f_d, wave.open(pat_file, 'rb') as f_p:
        sr = f_d.getframerate()
        start_frame = int(start_sec * sr)
        num_frames = int((end_sec - start_sec) * sr)
        
        f_d.setpos(start_frame)
        f_p.setpos(start_frame)
        
        doc_frames = f_d.readframes(num_frames)
        pat_frames = f_p.readframes(num_frames)
        
        doc_data = np.frombuffer(doc_frames, dtype=np.int16)
        pat_data = np.frombuffer(pat_frames, dtype=np.int16)
        
        # Mix and clip
        mixed = np.clip(doc_data.astype(np.int32) + pat_data.astype(np.int32), -32768, 32767).astype(np.int16)
        return mixed.tobytes()

def eval_diarization(consultation_id):
    base_dir = "eval/datasets/audio/primock57"
    jsonl_path = f"{base_dir}/jsonl/{consultation_id}.jsonl"
    doc_wav = f"{base_dir}/audio/{consultation_id}_doctor.wav"
    pat_wav = f"{base_dir}/audio/{consultation_id}_patient.wav"
    
    tracker = SpeakerTracker()
    
    zcr_c1 = None
    zcr_c2 = None
    
    ecapa_correct = 0
    zcr_correct = 0
    total = 0
    
    # Track the map from cluster to ground truth speaker (since it's unsupervised)
    ecapa_map = {} # 'spk_a' -> 'doctor', 'spk_b' -> 'patient' (or vice versa)
    zcr_map = {}
    
    segments = []
    with open(jsonl_path, 'r') as f:
        for line in f:
            segments.append(json.loads(line))
            
    # Process sequentially
    ecapa_preds = []
    zcr_preds = []
    true_labels = []
    
    for seg in segments[:30]:
        start = seg['start']
        end = seg['end']
        true_speaker = seg['speaker'].lower() # "doctor" or "patient"
        
        if end - start < 0.1:
            continue # skip short segments for evaluation clarity
            
        audio_bytes = mix_audio(doc_wav, pat_wav, start, end)
        
        # ECAPA
        label, conf = tracker.assign_speaker(audio_bytes)
        ecapa_preds.append(label)
        
        # ZCR
        data = np.frombuffer(audio_bytes, dtype=np.int16)
        crossings = np.nonzero(np.diff(data > 0))[0]
        zcr = len(crossings) / len(data) if len(data) > 0 else 0
        
        if zcr_c1 is None:
            zcr_c1 = zcr
            zcr_label = "spk_a"
        elif zcr_c2 is None:
            if abs(zcr - zcr_c1) > 0.05:
                zcr_c2 = zcr
                zcr_label = "spk_b"
            else:
                zcr_c1 = 0.9 * zcr_c1 + 0.1 * zcr
                zcr_label = "spk_a"
        else:
            d1 = abs(zcr - zcr_c1)
            d2 = abs(zcr - zcr_c2)
            if d1 < d2:
                zcr_c1 = 0.9 * zcr_c1 + 0.1 * zcr
                zcr_label = "spk_a"
            else:
                zcr_c2 = 0.9 * zcr_c2 + 0.1 * zcr
                zcr_label = "spk_b"
        
        zcr_preds.append(zcr_label)
        true_labels.append(true_speaker)
        
    # Map clusters to maximize accuracy
    def get_acc(preds):
        if not preds: return 0
        # Try mapping spk_a -> doctor, spk_b -> patient
        acc1 = sum(1 for p, t in zip(preds, true_labels) if (p == "spk_a" and t == "doctor") or (p == "spk_b" and t == "patient"))
        # Try mapping spk_a -> patient, spk_b -> doctor
        acc2 = sum(1 for p, t in zip(preds, true_labels) if (p == "spk_a" and t == "patient") or (p == "spk_b" and t == "doctor"))
        return max(acc1, acc2) / len(preds)

    return get_acc(zcr_preds), get_acc(ecapa_preds)

if __name__ == "__main__":
    consultations = [
        "day1_consultation01",
        "day1_consultation02",
        "day1_consultation03",
        "day1_consultation04",
        "day1_consultation05"
    ]
    
    print("Encounter ID | ZCR Acc | ECAPA Acc")
    print("-" * 40)
    for c in consultations:
        zcr_acc, ecapa_acc = eval_diarization(c)
        print(f"{c} | {zcr_acc:.2%} | {ecapa_acc:.2%}")
