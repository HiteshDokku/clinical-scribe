import { test, expect } from '@playwright/test';

test('signing screen layout validation', async ({ page }) => {
  await page.goto('http://localhost:3000/review/mock-encounter-id');
  
  // Verify the layout components
  await expect(page.locator('[data-testid="encounter-summary"]')).toBeVisible();
  
  // Verify the risk tier is prominently displayed
  await expect(page.locator('[data-testid="risk-tier-badge"]')).toBeVisible();
  
  // Ensure the confirm override button is present if high risk
  const isHighRisk = await page.locator('[data-testid="high-risk-warning"]').isVisible();
  if (isHighRisk) {
    await expect(page.locator('[data-testid="confirm-override-input"]')).toBeVisible();
  }
  
  // Take screenshot of signing screen
  await page.screenshot({ path: 'artifacts/signing_screen_layout.png', fullPage: true });
});
