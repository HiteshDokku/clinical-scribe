from typing import List, Dict, Tuple
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

# Load the model offline during startup
model_name = "cross-encoder/nli-deberta-v3-small"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)
model.eval()

def verify_grounding(statement_text: str, evidence_spans: List[Tuple[int, int]], transcript_segments: List[Dict]) -> bool:
    """
    Verifies that the statement is strictly grounded in the transcript using NLI.
    - evidence_spans: list of (start_ms, end_ms) indicating where the evidence is.
    - transcript_segments: list of dicts with 'start_ms', 'end_ms', 'text'.
    
    Returns True if the statement is plausible given the evidence, False otherwise.
    """
    if not evidence_spans:
        return False
        
    # Extract the cited text from the transcript
    cited_text_parts = []
    for span_start, span_end in evidence_spans:
        # Find all segments that overlap with this span
        for seg in transcript_segments:
            seg_start, seg_end = seg['start_ms'], seg['end_ms']
            if not (seg_end <= span_start or seg_start >= span_end):
                cited_text_parts.append(seg['text'])
                
    if not cited_text_parts:
        return False
        
    premise = " ".join(cited_text_parts)
    hypothesis = statement_text
    
    # NLI check using cross-encoder
    features = tokenizer(premise, hypothesis, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        scores = model(**features).logits
        
    # cross-encoder/nli-deberta-v3-small outputs: 0=Contradiction, 1=Entailment, 2=Neutral
    # We want to ensure it is NOT a contradiction, and preferably Entailment.
    # Let's be strict: it must be Entailment.
    predicted_label = torch.argmax(scores, dim=1).item()
    
    # Check string just in case
    id2label = model.config.id2label
    label_str = id2label[predicted_label].lower()
    
    # If the model predicts contradiction, it's definitely a hallucination
    if "contradiction" in label_str or predicted_label == 0:
        return False
        
    # If it predicts entailment, it's grounded
    if "entail" in label_str or predicted_label == 1:
        return True
        
    # If neutral, we reject it as well for strict grounding
    return False
