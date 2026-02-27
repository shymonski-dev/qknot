import { test, expect } from '@playwright/test';
import { KnotPage } from '../fixtures/knot-page';
import { TREFOIL } from '../fixtures/test-data';

/**
 * Live IBM smoke tests.
 *
 * These tests require a valid IBM Quantum API token and (optionally) a CRN:
 *   IBM_QUANTUM_TOKEN=<token>
 *   QKNOT_RUNTIME_INSTANCE=<crn>   (optional, omit for platform channel)
 *
 * They are gated behind the IBM_QUANTUM_TOKEN env var check below and
 * should be run via: npm run test:e2e:live
 *
 * IMPORTANT: These tests submit a REAL job to IBM hardware and immediately
 * cancel it. Expected cost is effectively zero (cancelled before execution),
 * but the token must have hardware access.
 */

const IBM_TOKEN = process.env.IBM_QUANTUM_TOKEN;
const RUNTIME_INSTANCE = process.env.QKNOT_RUNTIME_INSTANCE ?? '';

// Skip the entire suite if no live token is configured
test.skip(!IBM_TOKEN, 'IBM_QUANTUM_TOKEN is not set — skipping live smoke suite');

test.describe('Live IBM smoke suite', () => {
  test('L1: Backend listing returns at least one operational backend', async ({ page }) => {
    const kp = new KnotPage(page);
    await kp.goto();

    // Navigate to execution panel
    await kp.navigateTo('execution');

    // Fill CRN if provided
    if (RUNTIME_INSTANCE) {
      await kp.enterRuntimeInstance(RUNTIME_INSTANCE);
    }

    // Click "Load Accessible Hardware"
    await kp.loadBackendsButton.click();

    // Backend catalog should appear within a reasonable timeout
    await expect(kp.backendCatalog).toBeVisible({ timeout: 30_000 });

    // At least one backend name should appear
    const catalogText = (await kp.backendCatalog.textContent()) ?? '';
    const hasKnownBackend =
      catalogText.includes('ibm_') ||
      catalogText.includes('simulator');
    expect(hasKnownBackend).toBe(true);
  });

  test('L2: Trefoil — submit job to IBM, assert queued, then cancel', async ({ page }) => {
    test.setTimeout(90_000);

    const kp = new KnotPage(page);
    await kp.goto();

    // === Full pipeline ===
    await kp.navigateTo('ingestion');
    await kp.enterDowkerNotation(TREFOIL.dowker);
    await kp.clickIngest();
    await kp.waitForBraidWord();

    await kp.navigateTo('verification');
    await kp.clickVerify();
    await kp.waitForVerified();

    await kp.navigateTo('circuit');
    await kp.clickGenerateCircuit();
    await kp.waitForCircuitSummary();

    // === Execution ===
    await kp.navigateTo('execution');
    await kp.enterShots(128);

    if (RUNTIME_INSTANCE) {
      await kp.enterRuntimeInstance(RUNTIME_INSTANCE);
    }

    // Submit to real IBM hardware
    await kp.clickSubmitJob();

    // Job ID must appear — backend accepted the job
    const jobIdText = await kp.waitForJobId();
    expect(jobIdText).not.toContain('not available');

    // Status should be QUEUED or RUNNING (job was accepted)
    await expect(kp.jobIdDisplay).toContainText(/QUEUED|RUNNING|SUBMITTED|INITIALIZING/, {
      timeout: 30_000,
    });

    // Immediately cancel to avoid hardware charges
    await expect(kp.cancelJobButton).toBeVisible({ timeout: 10_000 });
    await kp.clickCancelJob();

    // Status should eventually show CANCELLED
    await expect(kp.jobIdDisplay).toContainText(/CANCELLED/i, { timeout: 30_000 });
  });
});
