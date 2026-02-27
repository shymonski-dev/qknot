import type { Page } from '@playwright/test';
import {
  MOCK_BACKENDS_RESPONSE,
  MOCK_JOB_RESULT,
} from './test-data';

/**
 * Mock POST /api/backends → returns canned backend list.
 */
export async function mockBackendsList(page: Page): Promise<void> {
  await page.route('**/api/backends', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_BACKENDS_RESPONSE),
    });
  });
}

/**
 * Mock POST /api/jobs/submit → returns job QUEUED.
 */
export async function mockJobSubmit(page: Page, jobId: string): Promise<void> {
  await page.route('**/api/jobs/submit', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        job_id: jobId,
        status: 'QUEUED',
        backend: 'ibm_marrakesh',
        runtime_channel_used: 'ibm_quantum_platform',
        runtime_instance_used: null,
      }),
    });
  });
}

/**
 * Mock POST /api/jobs/poll → always returns QUEUED.
 */
export async function mockJobPollQueued(page: Page, jobId: string): Promise<void> {
  await page.route('**/api/jobs/poll', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        job_id: jobId,
        status: 'QUEUED',
        backend: 'ibm_marrakesh',
        runtime_channel_used: 'ibm_quantum_platform',
        runtime_instance_used: null,
      }),
    });
  });
}

/**
 * Mock POST /api/jobs/poll → always returns RUNNING.
 */
export async function mockJobPollRunning(page: Page, jobId: string): Promise<void> {
  await page.route('**/api/jobs/poll', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        job_id: jobId,
        status: 'RUNNING',
        backend: 'ibm_marrakesh',
        runtime_channel_used: 'ibm_quantum_platform',
        runtime_instance_used: null,
      }),
    });
  });
}

type PollSequence = Array<'QUEUED' | 'RUNNING' | 'COMPLETED'>;

/**
 * Mock POST /api/jobs/poll → returns a sequence of statuses in order,
 * then returns COMPLETED with full result payload for all subsequent calls.
 *
 * @param sequence - e.g. ['QUEUED', 'RUNNING', 'COMPLETED']
 */
export async function mockJobPollSequence(
  page: Page,
  jobId: string,
  sequence: PollSequence,
): Promise<void> {
  let callIndex = 0;

  await page.route('**/api/jobs/poll', (route) => {
    const status = sequence[callIndex] ?? 'COMPLETED';
    if (callIndex < sequence.length - 1) {
      callIndex += 1;
    }

    if (status === 'COMPLETED') {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ...MOCK_JOB_RESULT, job_id: jobId }),
      });
    } else {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          job_id: jobId,
          status,
          backend: 'ibm_marrakesh',
          runtime_channel_used: 'ibm_quantum_platform',
          runtime_instance_used: null,
        }),
      });
    }
  });
}

/**
 * Mock POST /api/jobs/cancel → returns CANCELLED.
 */
export async function mockJobCancel(page: Page, jobId: string): Promise<void> {
  await page.route('**/api/jobs/cancel', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        job_id: jobId,
        status: 'CANCELLED',
        backend: 'ibm_marrakesh',
        runtime_channel_used: 'ibm_quantum_platform',
        runtime_instance_used: null,
      }),
    });
  });
}
