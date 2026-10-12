import assert from 'node:assert';

// Pure implementation mirroring apps/web/src/hooks/useReviewState.ts
function computeReviewState(soapNote, phase, state) {
  if (!soapNote) {
    return {
      canSign: false,
      blockingReasons: ['No note loaded'],
      blockingItems: [{ itemId: 'none', reason: 'No note loaded' }],
    };
  }

  const blockingItems = [];

  // Diagnosis phase sections: subjective, objective, assessment
  if (phase === 'diagnosis' || phase === 'all') {
    const diagSections = ['subjective', 'objective', 'assessment'];
    for (const secKey of diagSections) {
      const section = soapNote.sections[secKey];
      if (!section) continue;
      // Insufficient content sections count as complete
      if (section.insufficient_content) continue;

      for (let i = 0; i < section.statements.length; i++) {
        const stmt = section.statements[i];
        if (!stmt) continue;
        const isFlagged = stmt.risk_tier === 'requires_review' || stmt.risk_tier === 'red_flag';
        const isReviewed = state.statementReviews[stmt.id] === true;

        if (isFlagged) {
          const det = state.statementDeterminations[stmt.id] || '';
          if (!isReviewed || det.trim().length < 3) {
            blockingItems.push({
              itemId: stmt.id,
              reason: `Statement ${i + 1} (${secKey}): enter your own determination (at least 3 characters)`,
            });
          }
        } else {
          if (!isReviewed) {
            blockingItems.push({
              itemId: stmt.id,
              reason: `Statement ${i + 1} (${secKey}): confirm statement`,
            });
          }
        }
      }
    }
  }

  // Medication phase sections: plan + medications
  if (phase === 'medication' || phase === 'all') {
    const planSection = soapNote.sections.plan;
    if (planSection && !planSection.insufficient_content) {
      for (let i = 0; i < planSection.statements.length; i++) {
        const stmt = planSection.statements[i];
        if (!stmt) continue;
        if (!state.statementReviews[stmt.id]) {
          blockingItems.push({
            itemId: stmt.id,
            reason: `Plan statement ${i + 1}: confirm statement`,
          });
        }
      }
    }

    const meds = soapNote.medications ?? [];
    for (const med of meds) {
      const isReviewed = state.statementReviews[med.id] === true;
      if (med.needs_manual_confirmation) {
        const entry = state.medicationEntries[med.id] || '';
        if (!isReviewed || entry.trim().length < 3) {
          blockingItems.push({
            itemId: med.id,
            reason: `Medication "${med.verbatim}": enter manual confirmation (at least 3 characters)`,
          });
        }
      } else {
        if (!isReviewed) {
          blockingItems.push({
            itemId: med.id,
            reason: `Medication "${med.verbatim}": confirm medication`,
          });
        }
      }

      // Check safety flags
      for (let idx = 0; idx < med.flags.length; idx++) {
        const key = `${med.id}:${idx}`;
        if (!state.flagAcknowledgments[key]) {
          blockingItems.push({
            itemId: med.id,
            reason: `Safety flag on ${med.verbatim}: ${med.flags[idx].message.slice(0, 60)}...`,
          });
        }
      }
    }
  }

  return {
    canSign: blockingItems.length === 0,
    blockingReasons: blockingItems.map((b) => b.reason),
    blockingItems,
  };
}

console.log('Running unit tests for computeReviewState (pure review gating logic)...');

// Test 1: Null note blocks
{
  const res = computeReviewState(null, 'diagnosis', {
    statementReviews: {},
    flagAcknowledgments: {},
    statementDeterminations: {},
    medicationEntries: {},
  });
  assert.strictEqual(res.canSign, false);
  assert.strictEqual(res.blockingReasons[0], 'No note loaded');
  console.log('✓ Test 1 passed: null note blocked');
}

// Test 2: Unconfirmed grounded statement blocks
{
  const note = {
    sections: {
      subjective: { statements: [{ id: 's1', text: 'Cough', risk_tier: 'common' }], insufficient_content: false },
      objective: { statements: [], insufficient_content: true },
      assessment: { statements: [], insufficient_content: true },
    },
  };
  const res = computeReviewState(note, 'diagnosis', {
    statementReviews: {},
    flagAcknowledgments: {},
    statementDeterminations: {},
    medicationEntries: {},
  });
  assert.strictEqual(res.canSign, false);
  assert.strictEqual(res.blockingItems.length, 1);
  assert.strictEqual(res.blockingItems[0].itemId, 's1');
  console.log('✓ Test 2 passed: unconfirmed grounded statement blocks with item link');
}

// Test 3: Insufficient content sections count as complete
{
  const note = {
    sections: {
      subjective: { statements: [{ id: 's1', text: 'Cough', risk_tier: 'common' }], insufficient_content: false },
      objective: { statements: [], insufficient_content: true, reason: 'None observed' },
      assessment: { statements: [], insufficient_content: true, reason: 'None recorded' },
    },
  };
  const res = computeReviewState(note, 'diagnosis', {
    statementReviews: { s1: true },
    flagAcknowledgments: {},
    statementDeterminations: {},
    medicationEntries: {},
  });
  assert.strictEqual(res.canSign, true);
  assert.strictEqual(res.blockingReasons.length, 0);
  console.log('✓ Test 3 passed: insufficient content sections count as complete');
}

// Test 4: Flagged statement requires determination >= 3 chars
{
  const note = {
    sections: {
      subjective: { statements: [{ id: 's1', text: 'Cough', risk_tier: 'common' }], insufficient_content: false },
      objective: { statements: [], insufficient_content: true },
      assessment: { statements: [{ id: 'a1', text: 'Suspected pneumonia', risk_tier: 'requires_review' }], insufficient_content: false },
    },
  };
  // Case 4a: No determination
  let res = computeReviewState(note, 'diagnosis', {
    statementReviews: { s1: true, a1: true },
    flagAcknowledgments: {},
    statementDeterminations: { a1: '  ' },
    medicationEntries: {},
  });
  assert.strictEqual(res.canSign, false);
  assert.strictEqual(res.blockingItems[0].itemId, 'a1');

  // Case 4b: Determination with >= 3 chars
  res = computeReviewState(note, 'diagnosis', {
    statementReviews: { s1: true, a1: true },
    flagAcknowledgments: {},
    statementDeterminations: { a1: 'Common cold' },
    medicationEntries: {},
  });
  assert.strictEqual(res.canSign, true);
  console.log('✓ Test 4 passed: flagged statement requires >= 3 char determination');
}

// Test 5: Medication review phase gating
{
  const note = {
    sections: {
      plan: { statements: [{ id: 'p1', text: 'Rest and hydration' }], insufficient_content: false },
    },
    medications: [
      { id: 'm1', verbatim: 'Amoxicillin', needs_manual_confirmation: true, flags: [] },
      { id: 'm2', verbatim: 'Paracetamol', needs_manual_confirmation: false, flags: [{ message: 'Liver risk' }] },
    ],
  };

  // Initially all blocked
  let res = computeReviewState(note, 'medication', {
    statementReviews: {},
    flagAcknowledgments: {},
    statementDeterminations: {},
    medicationEntries: {},
  });
  assert.strictEqual(res.canSign, false);
  assert.strictEqual(res.blockingItems.length, 4); // p1, m1 manual, m2 confirm, m2 flag

  // Confirm plan, provide m1 manual entry, acknowledge flag
  res = computeReviewState(note, 'medication', {
    statementReviews: { p1: true, m1: true, m2: true },
    flagAcknowledgments: { 'm2:0': true },
    statementDeterminations: {},
    medicationEntries: { m1: 'Amoxicillin 500mg TDS' },
  });
  assert.strictEqual(res.canSign, true);
  console.log('✓ Test 5 passed: medication review gating enforced per ADR-0010');
}

console.log('ALL 5 computeReviewState unit tests passed successfully!');
