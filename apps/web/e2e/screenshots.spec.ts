import { test } from '@playwright/test';

/**
 * Screenshot capture tests for documentation purposes.
 * These take screenshots of each safety guardrail state.
 */

const REVIEW_URL = '/encounter/mock-encounter-001/review';
const CONSULTATION_URL = '/encounter/mock-encounter-001';

test.describe('Documentation Screenshots', () => {
  test('capture disabled sign button default state', async ({ page }) => {
    await page.goto(REVIEW_URL);
    await page.waitForSelector('[data-testid="soap-review-screen"]', { timeout: 10000 });
    // Wait a beat for animations
    await page.waitForTimeout(1000);
    await page.screenshot({ path: 'screenshots/01-disabled-sign-default.png', fullPage: true });
  });

  test('capture ungrounded double-confirmation dialog', async ({ page }) => {
    await page.goto(REVIEW_URL);
    await page.waitForSelector('[data-testid="soap-review-screen"]', { timeout: 10000 });
    await page.waitForTimeout(500);

    // Click review button for ungrounded statement
    const reviewBtn = page.locator('[data-testid="review-btn-assess-003"]');
    await reviewBtn.click();
    await page.waitForSelector('[data-testid="ungrounded-confirm-dialog"]');
    await page.waitForTimeout(500);
    await page.screenshot({ path: 'screenshots/02-ungrounded-confirm-dialog.png', fullPage: true });
  });

  test('capture safety flag blocking state', async ({ page }) => {
    await page.goto(REVIEW_URL);
    await page.waitForSelector('[data-testid="soap-review-screen"]', { timeout: 10000 });
    await page.waitForTimeout(500);

    // Scroll to medications area
    const medSection = page.locator('[data-testid^="medication-"]').first();
    await medSection.scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);
    await page.screenshot({ path: 'screenshots/03-safety-flags-blocking.png', fullPage: true });
  });

  test('capture consultation recording state', async ({ page }) => {
    await page.goto(CONSULTATION_URL);
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'screenshots/04-consultation-consent-gate.png', fullPage: true });
  });
});
