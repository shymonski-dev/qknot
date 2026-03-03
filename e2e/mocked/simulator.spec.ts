import { test, expect } from '@playwright/test';
import { KnotPage } from '../fixtures/knot-page';
import { TREFOIL } from '../fixtures/test-data';

/**
 * Simulator backend E2E tests.
 * These tests use the real backend for all API calls — no route mocking needed.
 * The qiskit_simulator backend requires no IBM token, so they are safe to run
 * in the mocked CI suite alongside the IBM-mocked tests.
 */

test.describe('Simulator backend', () => {
  test('Test 12: Full simulator pipeline — ingest → verify → circuit → execute completes without IBM token', async ({ page }) => {
    const kp = new KnotPage(page);
    await kp.goto();

    // Select the simulator backend before starting the pipeline
    await kp.selectTargetBackend('qiskit_simulator');

    // === Stage 1: Ingestion ===
    await kp.navigateTo('ingestion');
    await kp.enterDowkerNotation(TREFOIL.dowker);
    await kp.clickIngest();
    const braidWord = await kp.waitForBraidWord();
    expect(braidWord.trim()).toBe(TREFOIL.braidWord);

    // === Stage 2: Verification ===
    await kp.navigateTo('verification');
    await kp.clickVerify();
    await kp.waitForVerified();

    // === Stage 3: Circuit Generation ===
    await kp.navigateTo('circuit');
    await kp.clickGenerateCircuit();
    await kp.waitForCircuitSummary();

    // === Stage 4: Execution ===
    await kp.navigateTo('execution');
    await kp.clickSubmitJob();

    // Job ID should appear with the sim- prefix
    const jobIdText = await kp.waitForJobId();
    expect(jobIdText).toContain('sim-');

    // Result should arrive quickly (local simulation)
    const { jones } = await kp.waitForResult();
    expect(jones).toMatch(/^V\(t\) =/);

    // Execution complete banner
    await expect(page.getByText('Execution Complete')).toBeVisible();

    // Banner references the simulator backend
    await expect(page.getByText(/Result received from qiskit_simulator/)).toBeVisible();
  });

  test('Test 13: Simulator hides runtime channel and instance fields', async ({ page }) => {
    const kp = new KnotPage(page);
    await kp.goto();

    await kp.selectTargetBackend('qiskit_simulator');
    await kp.navigateTo('execution');

    // Runtime Channel label and Runtime Instance input should not be present
    await expect(page.getByText('Runtime Channel')).not.toBeVisible();
    await expect(kp.runtimeInstanceInput).not.toBeVisible();

    // Panel header should read "Simulator Runtime"
    await expect(page.getByText('Simulator Runtime')).toBeVisible();
  });

  test('Test 14: Switching from simulator to IBM backend restores runtime fields', async ({ page }) => {
    const kp = new KnotPage(page);
    await kp.goto();

    // Start on simulator — fields hidden
    await kp.selectTargetBackend('qiskit_simulator');
    await kp.navigateTo('execution');
    await expect(page.getByText('Runtime Channel')).not.toBeVisible();
    await expect(kp.runtimeInstanceInput).not.toBeVisible();

    // Switch to an IBM backend — fields should reappear
    await kp.selectTargetBackend('ibm_kyiv');
    await expect(page.getByText('Runtime Channel')).toBeVisible();
    await expect(kp.runtimeInstanceInput).toBeVisible();

    // Panel header should revert to "Hardware Runtime"
    await expect(page.getByText('Hardware Runtime')).toBeVisible();
  });
});
