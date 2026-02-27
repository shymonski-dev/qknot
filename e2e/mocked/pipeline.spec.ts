import { test, expect } from '@playwright/test';
import { KnotPage } from '../fixtures/knot-page';
import { TREFOIL, FIGURE_EIGHT, NON_CATALOG } from '../fixtures/test-data';

/**
 * Full 4-stage happy-path pipeline tests.
 * These use the real backend for knot/verify/circuit calls;
 * IBM hardware routes are not needed for these tests.
 */

test.describe('Happy-path pipeline — catalog knots', () => {
  test('Test 1: Trefoil knot completes full pipeline through circuit generation', async ({ page }) => {
    const kp = new KnotPage(page);
    await kp.goto();

    // === Stage 1: Ingestion ===
    await kp.navigateTo('ingestion');
    await kp.enterDowkerNotation(TREFOIL.dowker);
    await kp.clickIngest();

    const braidWord = await kp.waitForBraidWord();
    expect(braidWord.trim()).toBe(TREFOIL.braidWord);

    // Status message should mention catalog match
    await expect(kp.ingestStatus).toContainText('Trefoil Knot');

    // === Stage 2: Verification ===
    await kp.navigateTo('verification');
    await kp.clickVerify();
    await kp.waitForVerified();
    await expect(kp.verificationPassed).toBeVisible();

    // === Stage 3: Circuit Generation ===
    await kp.navigateTo('circuit');
    await kp.clickGenerateCircuit();
    const circuitStatusText = await kp.waitForCircuitSummary();

    // Status message should contain a circuit signature
    expect(circuitStatusText).toMatch(/Generated circuit signature/);
    // Circuit metadata grid should show the signature value box
    await expect(page.getByTestId('circuit-status')).toBeVisible();
  });

  test('Test 2: Figure-Eight knot resolves correctly from catalog', async ({ page }) => {
    const kp = new KnotPage(page);
    await kp.goto();

    // === Stage 1: Ingestion ===
    await kp.navigateTo('ingestion');
    await kp.enterDowkerNotation(FIGURE_EIGHT.dowker);
    await kp.clickIngest();

    const braidWord = await kp.waitForBraidWord();
    expect(braidWord.trim()).toBe(FIGURE_EIGHT.braidWord);

    await expect(kp.ingestStatus).toContainText('Figure-Eight Knot');

    // === Stage 2: Verification ===
    await kp.navigateTo('verification');
    await kp.clickVerify();
    await kp.waitForVerified();

    // === Stage 3: Circuit Generation ===
    await kp.navigateTo('circuit');
    await kp.clickGenerateCircuit();
    await kp.waitForCircuitSummary();
    await expect(page.getByTestId('circuit-status')).toBeVisible();
  });

  test('Test 3: Non-catalog notation uses fallback braid generation', async ({ page }) => {
    const kp = new KnotPage(page);
    await kp.goto();

    await kp.navigateTo('ingestion');
    await kp.enterDowkerNotation(NON_CATALOG.dowker);
    await kp.clickIngest();

    // Should succeed (fallback path) but show "fallback mapping" message
    await expect(kp.braidWordResult).toBeVisible({ timeout: 30_000 });
    await expect(kp.ingestStatus).toContainText('fallback mapping');
  });
});
