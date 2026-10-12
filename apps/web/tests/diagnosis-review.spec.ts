import { test, expect } from '@playwright/test';

test.describe('Diagnosis Review Risk Gates', () => {
  // Use a mocked backend or run against a real seeded backend if needed.
  // Assuming the user meant a unit/component test or e2e test hitting a specific URL.
  
  test('test_red_flag_case_shows_no_prefilled_suggestion', async ({ page }) => {
    // For this e2e test, we rely on the seeded encounter 59c5e8be-4dff-4f72-a100-3f14868ab1ca
    // which has a red flag diagnosis.
    // In a real automated test environment, we would seed this dynamically.
    
    // First, login
    await page.goto('/');
    
    // Check if there is a login form (if you added one)
    // or just mock local storage
    await page.evaluate(() => {
      localStorage.setItem('demo_role', 'clinician');
    });
    
    // Go to the review page of the seeded encounter
    // Using the ID generated earlier
    await page.goto('/review/59c5e8be-4dff-4f72-a100-3f14868ab1ca');
    
    // Wait for the assessment section
    await expect(page.locator('h3:has-text("Assessment")')).toBeVisible({ timeout: 10000 });
    
    // The red-flag row should not have the prefilled confirm button enabled without manual entry
    // Wait, the prompt says "no prefilled suggestion" - so the manual text area should be empty.
    const textarea = page.locator('textarea[placeholder="Enter clinical determination (required)..."]');
    await expect(textarea).toBeVisible();
    await expect(textarea).toHaveValue('');
  });
  
  test('test_red_flag_case_cannot_be_signed_without_manual_entry', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('demo_role', 'clinician');
    });
    await page.goto('/review/59c5e8be-4dff-4f72-a100-3f14868ab1ca');
    
    await expect(page.locator('h3:has-text("Assessment")')).toBeVisible({ timeout: 10000 });
    
    const confirmDiagnosisBtn = page.getByRole('button', { name: /confirm diagnosis/i });
    // It should be disabled because the red flag requires manual text
    await expect(confirmDiagnosisBtn).toBeDisabled();
    
    // Enter manual text
    const textarea = page.locator('textarea[placeholder="Enter clinical determination (required)..."]');
    await textarea.fill('Patient confirms chest pain is gone');
    
    // Now confirm the row
    const confirmRowBtn = page.locator('button:has-text("Confirm")').first();
    await confirmRowBtn.click();
    
    // Now Confirm Diagnosis button should be enabled
    await expect(confirmDiagnosisBtn).toBeEnabled();
  });
});
