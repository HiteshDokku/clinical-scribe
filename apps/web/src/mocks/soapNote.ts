import type { SoapNote } from '@/types/contracts';

/**
 * Realistic SOAP note fixture aligned with soap_note.schema.json.
 * Includes ungrounded statements and medication safety flags for testing
 * the review UI's safety guardrails.
 */
export const MOCK_SOAP_NOTE: SoapNote = {
  encounter_id: 'mock-encounter-001',
  model: {
    name: 'llama-3-8b-instruct',
    quant: 'Q4_K_M',
    prompt_version: 'v1.2.0',
  },
  generated_at: new Date().toISOString(),
  sections: {
    subjective: [
      {
        id: 'subj-001',
        text: 'Patient reports persistent chest tightness for the past 3 days, worsening with exertion.',
        evidence: ['seg-0012', 'seg-0013'],
        confidence: 0.94,
      },
      {
        id: 'subj-002',
        text: 'Denies any radiating pain to the arms or jaw.',
        evidence: ['seg-0014'],
        confidence: 0.91,
      },
      {
        id: 'subj-003',
        text: 'Reports intermittent dizziness upon standing, especially in the morning.',
        evidence: ['seg-0018'],
        confidence: 0.88,
      },
    ],
    objective: [
      {
        id: 'obj-001',
        text: 'Blood pressure 148/92 mmHg, heart rate 88 bpm, respiratory rate 18/min.',
        evidence: ['seg-0021', 'seg-0022'],
        confidence: 0.97,
      },
      {
        id: 'obj-002',
        text: 'Cardiac auscultation reveals a grade II/VI systolic murmur at the apex.',
        evidence: ['seg-0024'],
        confidence: 0.85,
      },
      {
        id: 'obj-003',
        text: 'Bilateral lower extremity edema noted, 1+ pitting.',
        evidence: ['seg-0025'],
        confidence: 0.72,
      },
    ],
    assessment: [
      {
        id: 'assess-001',
        text: 'Hypertensive urgency with borderline Stage 2 hypertension.',
        evidence: ['seg-0021', 'seg-0022', 'seg-0030'],
        confidence: 0.92,
      },
      {
        id: 'assess-002',
        text: 'Possible early-stage congestive heart failure given bilateral edema and systolic murmur.',
        evidence: ['seg-0024', 'seg-0025'],
        confidence: 0.78,
      },
      {
        id: 'assess-003',
        text: 'Patient may have an underlying thyroid disorder contributing to symptoms.',
        evidence: ['seg-0018'],
        confidence: 0.42,
      },
    ],
    plan: [
      {
        id: 'plan-001',
        text: 'Start Lisinopril 10mg daily for blood pressure management.',
        evidence: ['seg-0032'],
        confidence: 0.95,
      },
      {
        id: 'plan-002',
        text: 'Continue Metformin 500mg twice daily for existing diabetes management.',
        evidence: ['seg-0033'],
        confidence: 0.93,
      },
      {
        id: 'plan-003',
        text: 'Order echocardiogram and BNP levels to evaluate cardiac function.',
        evidence: ['seg-0034'],
        confidence: 0.90,
      },
      {
        id: 'plan-004',
        text: 'Schedule thyroid panel (TSH, Free T4) at next visit.',
        evidence: ['seg-0035'],
        confidence: 0.87,
      },
    ],
  },
  medications: [
    {
      id: 'med-001',
      verbatim: 'Lisinopril 10mg daily',
      ingredient_id: 'lisinopril',
      match_confidence: 0.98,
      needs_manual_confirmation: false,
      dose: { value: 10, unit: 'mg' },
      frequency: 'once daily',
      route: 'oral',
      evidence: ['seg-0032'],
      flags: [],
    },
    {
      id: 'med-002',
      verbatim: 'Metformin 500mg twice daily',
      ingredient_id: 'metformin',
      match_confidence: 0.97,
      needs_manual_confirmation: false,
      dose: { value: 500, unit: 'mg' },
      frequency: 'twice daily',
      route: 'oral',
      evidence: ['seg-0033'],
      flags: [
        {
          severity: 'high',
          type: 'interaction',
          pair: ['lisinopril', 'metformin'],
          source_ref: 'DDInter2#88014',
          message:
            'Lisinopril combined with Metformin may increase the risk of hypoglycemia and lactic acidosis. Monitor renal function and blood glucose closely.',
        },
      ],
    },
    {
      id: 'med-003',
      verbatim: 'Warfarin 5mg',
      ingredient_id: 'warfarin',
      match_confidence: 0.95,
      needs_manual_confirmation: false,
      dose: { value: 5, unit: 'mg' },
      frequency: 'once daily',
      route: 'oral',
      evidence: ['seg-0036'],
      flags: [
        {
          severity: 'moderate',
          type: 'interaction',
          pair: ['warfarin', 'metformin'],
          source_ref: 'ONC-HighPriority#412',
          message:
            'Warfarin and Metformin co-administration may alter INR levels. Regular INR monitoring is recommended.',
        },
      ],
    },
  ],
  safety_flags: [
    {
      severity: 'high',
      type: 'interaction',
      pair: ['lisinopril', 'metformin'],
      source_ref: 'DDInter2#88014',
      message:
        'Lisinopril combined with Metformin may increase the risk of hypoglycemia and lactic acidosis.',
    },
    {
      severity: 'moderate',
      type: 'interaction',
      pair: ['warfarin', 'metformin'],
      source_ref: 'ONC-HighPriority#412',
      message: 'Warfarin and Metformin co-administration may alter INR levels.',
    },
  ],
  grounding: {
    statements_total: 10,
    ungrounded: 1,
    ungrounded_ids: ['assess-003'],
  },
};

/**
 * Map of evidence span IDs to transcript text, for the review evidence panel.
 */
export const MOCK_EVIDENCE_MAP: Record<string, string> = {
  'seg-0012':
    'I have been having this tightness in my chest for about three days now.',
  'seg-0013':
    'It gets worse when I climb stairs or walk for a long time.',
  'seg-0014':
    'No, I don\'t have any pain going down my arm or into my jaw.',
  'seg-0018':
    'Sometimes when I get up in the morning I feel dizzy for a few seconds.',
  'seg-0021':
    'Blood pressure is reading 148 over 92.',
  'seg-0022':
    'Heart rate 88, respiratory rate 18.',
  'seg-0024':
    'I can hear a systolic murmur at the apex, sounds like a grade two out of six.',
  'seg-0025':
    'There is some mild bilateral lower extremity edema, about one plus pitting.',
  'seg-0030':
    'This is concerning for hypertensive urgency, we are looking at borderline stage two.',
  'seg-0032':
    'Let us start you on Lisinopril, ten milligrams once a day.',
  'seg-0033':
    'Continue taking the Metformin five hundred milligrams twice a day as you have been.',
  'seg-0034':
    'I am going to order an echo and BNP labs to take a closer look at how your heart is functioning.',
  'seg-0035':
    'At your next visit, we will also check your thyroid with a TSH and Free T4.',
  'seg-0036':
    'And keep taking the Warfarin five milligrams once daily as prescribed.',
};
