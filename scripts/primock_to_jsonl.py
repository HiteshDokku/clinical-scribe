import os
import re
import json

def parse_textgrid(filepath, speaker_label):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Simple regex parsing for TextGrid
    # intervals [x]:
    #     xmin = 0
    #     xmax = 2.5
    #     text = "hello"
    
    segments = []
    pattern = re.compile(r"intervals \[\d+\]:\s*xmin = ([\d\.]+)\s*xmax = ([\d\.]+)\s*text = \"(.*?)\"", re.DOTALL)
    for match in pattern.finditer(content):
        xmin = float(match.group(1))
        xmax = float(match.group(2))
        text = match.group(3).strip()
        if text:  # Ignore empty segments
            segments.append({
                "start": xmin,
                "end": xmax,
                "speaker": speaker_label,
                "text": text
            })
    return segments

def main():
    base_dir = "eval/datasets/audio/primock57/transcripts"
    output_dir = "eval/datasets/audio/primock57/jsonl"
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all consultations
    files = os.listdir(base_dir)
    consultations = set()
    for f in files:
        if f.endswith(".TextGrid"):
            prefix = f.split("_doctor")[0].split("_patient")[0]
            consultations.add(prefix)
            
    for cons in consultations:
        doc_file = os.path.join(base_dir, f"{cons}_doctor.TextGrid")
        pat_file = os.path.join(base_dir, f"{cons}_patient.TextGrid")
        
        segments = []
        if os.path.exists(doc_file):
            segments.extend(parse_textgrid(doc_file, "Doctor"))
        if os.path.exists(pat_file):
            segments.extend(parse_textgrid(pat_file, "Patient"))
            
        segments.sort(key=lambda x: x["start"])
        
        out_file = os.path.join(output_dir, f"{cons}.jsonl")
        with open(out_file, "w", encoding="utf-8") as out:
            for i, seg in enumerate(segments):
                seg_id = f"seg_{i+1}"
                line = {
                    "id": seg_id,
                    "speaker": seg["speaker"],
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"]
                }
                out.write(json.dumps(line) + "\n")

if __name__ == "__main__":
    main()
