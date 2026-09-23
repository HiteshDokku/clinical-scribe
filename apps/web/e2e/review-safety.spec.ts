import { test, expect } from '@playwright/test';

/**
 * Playwright E2E tests asserting clinical safety guardrails on the SOAP Review UI.
 *
 * These tests navigate directly to the review page which loads mock fixture data
 * containing ungrounded statements and medication safety flags.
 */

const REVIEW_URL = '/encounter/mock-encounter-001/review';

test.describe('SOAP Review — Clinical Safety Guardrails', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(REVIEW_URL);
    // Wait for the review screen to render
    await page.waitForSelector('[data-testid="soap-review-screen"]', { timeout: 10000 });
  });

  test('1. Sign button is disabled by default', async ({ page }) => {
    const signButton = page.locator('[data-testid="sign-button"]');
    await expect(signButton).toBeVisible();
    await expect(signButton).toBeDisabled();
  });

  test('2. Ungrounded statements trigger double-confirmation dialog', async ({ page }) => {
    // Find the ungrounded statement's review button
    // The mock data has assess-003 as ungrounded
    const reviewBtn = page.locator('[data-testid="review-btn-assess-003"]');
    await expect(reviewBtn).toBeVisible();

    // Click to trigger the double-confirmation dialog
    await reviewBtn.click();

    // The confirmation dialog should appear
    const dialog = page.locator('[data-testid="ungrounded-confirm-dialog"]');
    await expect(dialog).toBeVisible();

    // It should contain warning text about ungrounded statement
    await expect(dialog).toContainText('Ungrounded Statement');
    await expect(dialog).toContainText('lacks full transcript grounding');

    // Both Cancel and Confirm buttons should be present
    const cancelBtn = page.locator('[data-testid="ungrounded-cancel-btn"]');
    const confirmBtn = page.locator('[data-testid="ungrounded-confirm-btn"]');
    await expect(cancelBtn).toBeVisible();
    await expect(confirmBtn).toBeVisible();

    // Cancel should close the dialog without approving
    await cancelBtn.click();
    await expect(dialog).not.toBeVisible();

    // Re-open and confirm
    await reviewBtn.click();
    await expect(dialog).toBeVisible();
    await confirmBtn.click();
    await expect(dialog).not.toBeVisible();
  });

  test('3. Safety flag blocks sign-off until individually acknowledged', async ({ page }) => {
    const signButton = page.locator('[data-testid="sign-button"]');

    // Sign should be disabled initially
    await expect(signButton).toBeDisabled();

    // First, confirm the ungrounded statement (prerequisite)
    const reviewBtn = page.locator('[data-testid="review-btn-assess-003"]');
    if (await reviewBtn.isVisible()) {
      await reviewBtn.click();
      const confirmBtn = page.locator('[data-testid="ungrounded-confirm-btn"]');
      await confirmBtn.click();
    }

    // Sign should STILL be disabled because safety flags exist
    await expect(signButton).toBeDisabled();

    // Find all safety flag acknowledge buttons
    const ackButtons = page.locator('[data-testid^="acknowledge-flag-"]');
    const count = await ackButtons.count();
    expect(count).toBeGreaterThan(0);

    // Acknowledge each flag individually
    for (let i = 0; i < count; i++) {
      // Re-query after each click as DOM may update
      const btn = page.locator('[data-testid^="acknowledge-flag-"]').first();
      if (await btn.isVisible()) {
        await btn.click();
      }
    }

    // Now sign should be enabled
    await expect(signButton).toBeEnabled();
  });

  test('4. No "Approve All" exists anywhere in the review DOM', async ({ page }) => {
    // Strict text assertion: "Approve All" must not appear
    const body = page.locator('body');
    await expect(body).not.toContainText('Approve All');
    await expect(body).not.toContainText('approve all');
    await expect(body).not.toContainText('APPROVE ALL');

    // Also check there's no element with a data-action of approve-all
    const approveAllElements = page.locator('[data-action="approve-all"]');
    await expect(approveAllElements).toHaveCount(0);

    // Check no button with text containing "approve all" (case insensitive)
    const approveAllButtons = page.locator('button:has-text("approve all")');
    await expect(approveAllButtons).toHaveCount(0);
  });
});
