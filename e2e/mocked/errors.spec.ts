import { test, expect } from '@playwright/test';
import { KnotPage } from '../fixtures/knot-page';
import { INVALID_DOWKER, TREFOIL } from '../fixtures/test-data';

/**
 * Error-handling tests — verifies that each stage surfaces failures correctly.
 */

test.describe('Error handling', () => {
  test('Test 4: Invalid Dowker notation is rejected with an error message', async ({ page }) => {
    const kp = new KnotPage(page);
    await kp.goto();
    await kp.navigateTo('ingestion');

    // Record the current (default) braid word before attempting invalid notation
    const originalBraidWord = (await kp.braidWordResult.textContent()) ?? '';

    await kp.enterDowkerNotation(INVALID_DOWKER.dowker);
    await kp.compileButton.click();

    // Wait for the error banner
    await expect(kp.ingestError).toBeVisible({ timeout: 15_000 });
    const errorText = (await kp.ingestError.textContent()) ?? '';
    expect(errorText.length).toBeGreaterThan(0);

    // The success status message should NOT appear
    await expect(kp.ingestStatus).not.toBeVisible();

    // Braid word should remain unchanged (failed compile doesn't update it)
    const newBraidWord = (await kp.braidWordResult.textContent()) ?? '';
    expect(newBraidWord).toBe(originalBraidWord);
  });

  test('Test 5: Verification returns is_verified=false — failed state rendered', async ({ page }) => {
    const kp = new KnotPage(page);
    await kp.goto();

    // First ingest the Trefoil so we have a braid word
    await kp.navigateTo('ingestion');
    await kp.enterDowkerNotation(TREFOIL.dowker);
    await kp.clickIngest();
    await kp.waitForBraidWord();

    // Stub /api/knot/verify to return failed
    await page.route('**/api/knot/verify', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          is_verified: false,
          status: 'failed',
          detail: 'Braid generators are non-contiguous.',
          evidence: {
            token_count: 4,
            generator_counts: { s1: 2, s2: 2 },
            inverse_count: 2,
            net_writhe: 0,
            generator_switches: 3,
            alternation_ratio: 0.75,
            unique_generator_count: 2,
            max_generator_index: 2,
            strand_count: 3,
            missing_generators: [],
            strand_connectivity: 'connected',
          },
        }),
      });
    });

    await kp.navigateTo('verification');
    await kp.verifyButton.click();

    // Wait for verify button to re-enable after response
    await expect(kp.verifyButton).not.toBeDisabled({ timeout: 15_000 });

    // Verified badge should NOT appear
    await expect(kp.verificationPassed).not.toBeVisible();

    // Error message should be shown
    await expect(kp.verifyError).toBeVisible();
    await expect(kp.verifyError).toContainText('non-contiguous');
  });

  test('Test 6: Backend unreachable — ingest shows network error', async ({ page }) => {
    const kp = new KnotPage(page);
    await kp.goto();
    await kp.navigateTo('ingestion');

    // Abort all ingest requests to simulate backend being down
    await page.route('**/api/knot/ingest', (route) => route.abort('connectionrefused'));

    await kp.enterDowkerNotation(TREFOIL.dowker);
    await kp.compileButton.click();

    // Wait for error
    await expect(kp.ingestError).toBeVisible({ timeout: 15_000 });
    await expect(kp.ingestError).toContainText(/reach|network|backend/i);
  });

  test('Test 7: Server 500 on ingest — generic error shown', async ({ page }) => {
    const kp = new KnotPage(page);
    await kp.goto();
    await kp.navigateTo('ingestion');

    // Stub ingest to return 500
    await page.route('**/api/knot/ingest', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal server error' }),
      });
    });

    await kp.enterDowkerNotation(TREFOIL.dowker);
    await kp.compileButton.click();

    await expect(kp.ingestError).toBeVisible({ timeout: 15_000 });
    await expect(kp.ingestError).toContainText(/500|server error/i);
  });
});
