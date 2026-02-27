import { test, expect } from '@playwright/test';
import { KnotPage } from '../fixtures/knot-page';
import {
  mockJobSubmit,
  mockJobPollSequence,
  mockJobPollRunning,
  mockJobCancel,
} from '../fixtures/mock-ibm';
import { TREFOIL, MOCK_JOB_ID } from '../fixtures/test-data';

/**
 * Run the full ingest → verify → circuit pipeline using the real backend,
 * leaving the app in "compiled" state ready for job submission.
 */
async function setupPipeline(kp: KnotPage): Promise<void> {
  await kp.goto();

  // Ingest
  await kp.navigateTo('ingestion');
  await kp.enterDowkerNotation(TREFOIL.dowker);
  await kp.clickIngest();
  await kp.waitForBraidWord();

  // Verify
  await kp.navigateTo('verification');
  await kp.clickVerify();
  await kp.waitForVerified();

  // Generate circuit
  await kp.navigateTo('circuit');
  await kp.clickGenerateCircuit();
  await kp.waitForCircuitSummary();
}

test.describe('Job execution flow (IBM mocked)', () => {
  test('Test 8: Full submit → poll → completed result displayed', async ({ page }) => {
    const kp = new KnotPage(page);
    await setupPipeline(kp);

    // Set up IBM mocks
    await mockJobSubmit(page, MOCK_JOB_ID);
    await mockJobPollSequence(page, MOCK_JOB_ID, ['QUEUED', 'RUNNING', 'COMPLETED']);

    // Navigate to execution and submit
    await kp.navigateTo('execution');
    await kp.clickSubmitJob();

    // Job ID should appear in the header
    const jobIdText = await kp.waitForJobId();
    expect(jobIdText).toContain(MOCK_JOB_ID);

    // Wait for final result
    const { jones } = await kp.waitForResult();
    expect(jones.length).toBeGreaterThan(0);

    // Execution complete banner
    await expect(page.getByText('Execution Complete')).toBeVisible();

    // Expectation value in banner
    await expect(page.getByText(/expectation value/i)).toContainText('0.625');
  });

  test('Test 9: Job cancellation stops execution and shows cancelled status', async ({ page }) => {
    const kp = new KnotPage(page);
    await setupPipeline(kp);

    // Submit returns QUEUED, poll always returns RUNNING
    await mockJobSubmit(page, MOCK_JOB_ID);
    await mockJobPollRunning(page, MOCK_JOB_ID);
    await mockJobCancel(page, MOCK_JOB_ID);

    await kp.navigateTo('execution');
    await kp.clickSubmitJob();

    // Wait until the job is in-flight (job ID visible)
    await kp.waitForJobId();
    await expect(kp.cancelJobButton).toBeVisible({ timeout: 10_000 });

    // Cancel the job
    await kp.clickCancelJob();

    // Cancel button should disappear (job no longer in-flight)
    await expect(kp.cancelJobButton).not.toBeVisible({ timeout: 15_000 });

    // Job ID display should show CANCELLED
    await expect(kp.jobIdDisplay).toContainText(/CANCELLED/i, { timeout: 10_000 });
  });

  test('Test 10: Resume pending job from localStorage triggers poll', async ({ page }) => {
    const kp = new KnotPage(page);
    await setupPipeline(kp);

    // Seed a pending job into localStorage while on the execution page
    await kp.navigateTo('execution');
    await kp.seedPendingJob(MOCK_JOB_ID);

    // Set up mock poll BEFORE reload (route handlers persist across reloads)
    await mockJobPollSequence(page, MOCK_JOB_ID, ['RUNNING', 'COMPLETED']);

    // Reload the page to trigger the pending-job detection on mount
    await page.reload();

    // Navigate to execution panel (after reload, activeStep defaults to 'dashboard')
    await kp.navigateTo('execution');

    // Resume banner should appear (localStorage-seeded job found on mount)
    await expect(kp.resumeJobButton).toBeVisible({ timeout: 10_000 });

    // Click resume
    await kp.resumeJobButton.click();

    // Wait for the Jones polynomial result
    const { jones } = await kp.waitForResult();
    expect(jones.length).toBeGreaterThan(0);
  });

  test('Test 11: Poll timeout saves pending job and shows error', async ({ page }) => {
    // Use URL params to configure a very short poll cycle (3 attempts, 50ms each)
    // so the timeout triggers in < 200ms without needing to manipulate the fake clock.
    const kp = new KnotPage(page);
    await kp.goto('/?test_max_poll=3&test_poll_ms=50');

    // Complete the pipeline (ingest + verify + circuit) with these URL params active
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

    // Submit succeeds, poll always returns RUNNING (never completes)
    await mockJobSubmit(page, MOCK_JOB_ID);
    await mockJobPollRunning(page, MOCK_JOB_ID);

    await kp.navigateTo('execution');
    await kp.clickSubmitJob();

    // With only 3 poll attempts at 50ms each, timeout fires in ~150ms
    await expect(kp.executionError).toBeVisible({ timeout: 10_000 });
    await expect(kp.executionError).toContainText(/timed out/i);
  });
});
