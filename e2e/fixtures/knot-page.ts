import type { Page, Locator } from '@playwright/test';
import { expect } from '@playwright/test';

/**
 * Page Object Model for the Q-Knot Pipeline UI.
 * Wraps Playwright Page with typed locators and action methods.
 */
export class KnotPage {
  readonly page: Page;

  // Sidebar navigation
  readonly navIngestion: Locator;
  readonly navVerification: Locator;
  readonly navCircuit: Locator;
  readonly navExecution: Locator;

  // Ingestion panel
  readonly dowkerInput: Locator;
  readonly compileButton: Locator;
  readonly braidWordResult: Locator;
  readonly ingestError: Locator;
  readonly ingestStatus: Locator;

  // Verification panel
  readonly verifyButton: Locator;
  readonly verificationPassed: Locator;
  readonly verifyError: Locator;

  // Circuit generation panel
  readonly generateCircuitButton: Locator;
  readonly circuitStatus: Locator;
  readonly circuitError: Locator;

  // Execution panel
  readonly runtimeInstanceInput: Locator;
  readonly loadBackendsButton: Locator;
  readonly backendCatalog: Locator;
  readonly executeButton: Locator;
  readonly cancelJobButton: Locator;
  readonly jobIdDisplay: Locator;
  readonly jobStatusText: Locator;
  readonly jonesPolynomial: Locator;
  readonly executionError: Locator;
  readonly resumeJobButton: Locator;

  constructor(page: Page) {
    this.page = page;

    // Sidebar nav buttons
    this.navIngestion = page.getByRole('button', { name: /1\. Knot Ingestion/ });
    this.navVerification = page.getByRole('button', { name: /2\. Topological Verification/ });
    this.navCircuit = page.getByRole('button', { name: /3\. Circuit Generation/ });
    this.navExecution = page.getByRole('button', { name: /6\. Execution & Results/ });

    // Ingestion
    this.dowkerInput = page.getByTestId('dowker-input');
    this.compileButton = page.getByTestId('compile-button');
    this.braidWordResult = page.getByTestId('braid-word-result');
    this.ingestError = page.getByTestId('ingest-error');
    this.ingestStatus = page.getByTestId('ingest-status');

    // Verification
    this.verifyButton = page.getByTestId('verify-button');
    this.verificationPassed = page.getByTestId('verification-passed');
    this.verifyError = page.getByTestId('verify-error');

    // Circuit generation
    this.generateCircuitButton = page.getByTestId('generate-circuit-button');
    this.circuitStatus = page.getByTestId('circuit-status');
    this.circuitError = page.getByTestId('circuit-error');

    // Execution
    this.runtimeInstanceInput = page.getByTestId('runtime-instance-input');
    this.loadBackendsButton = page.getByTestId('load-backends-button');
    this.backendCatalog = page.getByTestId('backend-catalog');
    this.executeButton = page.getByTestId('execute-button');
    this.cancelJobButton = page.getByTestId('cancel-job-button');
    this.jobIdDisplay = page.getByTestId('job-id-display');
    this.jobStatusText = page.getByTestId('job-status-text');
    this.jonesPolynomial = page.getByTestId('jones-polynomial');
    this.executionError = page.getByTestId('execution-error');
    this.resumeJobButton = page.getByTestId('resume-job-button');
  }

  async goto(path = '/'): Promise<void> {
    await this.page.goto(path);
  }

  async navigateTo(step: 'ingestion' | 'verification' | 'circuit' | 'execution'): Promise<void> {
    const nav = {
      ingestion: this.navIngestion,
      verification: this.navVerification,
      circuit: this.navCircuit,
      execution: this.navExecution,
    }[step];
    await nav.click();
  }

  /** Type Dowker notation into the input, replacing any existing value. */
  async enterDowkerNotation(notation: string): Promise<void> {
    await this.dowkerInput.fill(notation);
  }

  /** Click "Compile to Braid Word" and wait for the button to re-enable. */
  async clickIngest(): Promise<void> {
    await this.compileButton.click();
    // Wait for loading state to finish
    await expect(this.compileButton).not.toBeDisabled({ timeout: 30_000 });
  }

  /** Wait for the braid word to appear and return its text. */
  async waitForBraidWord(): Promise<string> {
    await expect(this.braidWordResult).toBeVisible({ timeout: 30_000 });
    return (await this.braidWordResult.textContent()) ?? '';
  }

  /** Click "Verify Topological Mapping" and wait for the button to re-enable. */
  async clickVerify(): Promise<void> {
    await this.verifyButton.click();
    await expect(this.verifyButton).not.toBeDisabled({ timeout: 30_000 });
  }

  /** Wait for the "Verification Passed" badge to appear. */
  async waitForVerified(): Promise<void> {
    await expect(this.verificationPassed).toBeVisible({ timeout: 30_000 });
  }

  /** Click "Generate Circuit" and wait for the button to re-enable. */
  async clickGenerateCircuit(): Promise<void> {
    await this.generateCircuitButton.click();
    await expect(this.generateCircuitButton).not.toBeDisabled({ timeout: 60_000 });
  }

  /** Wait for the circuit status message (contains signature). */
  async waitForCircuitSummary(): Promise<string> {
    await expect(this.circuitStatus).toBeVisible({ timeout: 60_000 });
    return (await this.circuitStatus.textContent()) ?? '';
  }

  /** Set the shots input to a specific number. */
  async enterShots(shots: number): Promise<void> {
    const shotsInput = this.page.getByRole('spinbutton');
    await shotsInput.fill(String(shots));
  }

  /** Click the execute button. Does NOT wait for completion. */
  async clickSubmitJob(): Promise<void> {
    await this.executeButton.click();
  }

  /**
   * Wait for the job ID display to show a real job ID (not "not available").
   * Returns the raw text of the display element.
   */
  async waitForJobId(): Promise<string> {
    await expect(this.jobIdDisplay).not.toHaveText(/not available/, { timeout: 30_000 });
    return (await this.jobIdDisplay.textContent()) ?? '';
  }

  /** Wait for the Jones polynomial result to appear and return its text. */
  async waitForResult(): Promise<{ expectation: string; jones: string }> {
    await expect(this.jonesPolynomial).toBeVisible({ timeout: 120_000 });
    const jones = (await this.jonesPolynomial.textContent()) ?? '';
    // Expectation value is shown in the banner above the grid
    const banner = this.page.getByText(/expectation value/i);
    const bannerText = (await banner.first().textContent()) ?? '';
    return { expectation: bannerText, jones };
  }

  /** Click the Cancel Current Job button. */
  async clickCancelJob(): Promise<void> {
    await this.cancelJobButton.click();
  }

  /**
   * Seed localStorage with a pending job snapshot so the resume banner
   * appears when the page loads.
   */
  async seedPendingJob(jobId: string): Promise<void> {
    await this.page.evaluate((id) => {
      window.localStorage.setItem(
        'qknot.pending_job',
        JSON.stringify({
          job_id: id,
          backend_name: 'ibm_marrakesh',
          runtime_channel: 'ibm_quantum_platform',
          runtime_instance: null,
        }),
      );
    }, jobId);
  }

  /** Fill the Runtime Instance field in the Execution panel. */
  async enterRuntimeInstance(crn: string): Promise<void> {
    await this.runtimeInstanceInput.fill(crn);
  }
}
