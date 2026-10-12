import { test, expect } from '@playwright/test';

test.describe('Medication Review Risk Gates', () => {
  test('test_high_risk_medication_cannot_be_one_click_approved', async ({ page }) => {
    // Navigate and login
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('demo_role', 'clinician');
    });
    
    // In a real test, we would hit a seeded encounter in medication_review state
    // Let's assume we can navigate to one.
    // For now we'll just check if the code is present.
    // This is a placeholder that will fail unless the environment is set up.
    
    // Mocking the API response for an encounter in medication_review state
    await page.route('**/api/v1/encounters/*', async (route) => {
      const response = {
        id: '123',
        state: 'medication_review',
        note: {
          sections: {
            subjective: { statements: [] },
            objective: { statements: [] },
            assessment: { statements: [] },
            plan: { statements: [] }
          },
          medications: [
            {
              id: 'med_1',
              verbatim: 'High Risk Med',
              needs_manual_confirmation: true,
              flags: []
            }
          ]
        },
        transcript: []
      };
      await route.fulfill({ json: response });
    });
    
    await page.goto('/review/123');
    
    // Wait for medications section
    await expect(page.locator('h3:has-text("Medications")')).toBeVisible();
    
    const signBtn = page.getByRole('button', { name: /sign note/i });
    await expect(signBtn).toBeDisabled();
    
    const input = page.locator('input[placeholder="Type medication, dose, route, and frequency..."]');
    await expect(input).toBeVisible();
    await input.fill('Confirmed dose');
    
    const confirmRowBtn = page.locator('button:has-text("Confirm")').first();
    await confirmRowBtn.click();
    
    await expect(signBtn).toBeEnabled();
  });
});
