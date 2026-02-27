import React, { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import ExecutionResults from '../ExecutionResults';
import type { ExecutionSettings, ExperimentResult, KnotData } from '../../types';

const PENDING_JOB_STORAGE_KEY = 'qknot.pending_job';

vi.mock('recharts', () => {
  const Wrap = ({ children }: { children?: React.ReactNode }) => <div>{children}</div>;
  return {
    ResponsiveContainer: Wrap,
    BarChart: Wrap,
    CartesianGrid: () => null,
    XAxis: () => null,
    YAxis: () => null,
    Tooltip: () => null,
    Bar: () => null,
  };
});

const compiledKnot: KnotData = {
  id: 'k-1',
  name: 'Trefoil Knot (3_1)',
  dowkerNotation: '4 6 2',
  braidWord: 's1 s2^-1 s1',
  rootOfUnity: 5,
  status: 'compiled',
};

function renderWithHarness(options?: {
  activeKnot?: KnotData | null;
  initialSettings?: ExecutionSettings;
  onExecutionComplete?: (result: ExperimentResult) => void;
  pollIntervalMs?: number;
  maxPollAttempts?: number;
}) {
  const activeKnot = options?.activeKnot ?? compiledKnot;
  const initialSettings =
    options?.initialSettings ??
    ({
      shots: 8192,
      optimizationLevel: 2,
      closureMethod: 'trace',
    } satisfies ExecutionSettings);
  const onExecutionComplete = options?.onExecutionComplete ?? vi.fn();
  const pollIntervalMs = options?.pollIntervalMs;
  const maxPollAttempts = options?.maxPollAttempts;

  function Harness() {
    const [settings, setSettings] = useState<ExecutionSettings>(initialSettings);
    return (
      <ExecutionResults
        activeKnot={activeKnot}
        targetBackend="ibm_kyiv"
        executionSettings={settings}
        setExecutionSettings={setSettings}
        onExecutionComplete={onExecutionComplete}
        pollIntervalMs={pollIntervalMs}
        maxPollAttempts={maxPollAttempts}
      />
    );
  }

  return {
    ...render(<Harness />),
    onExecutionComplete,
  };
}

function jsonResponse(payload: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
  } as Response;
}

describe('ExecutionResults', () => {
  it('disables execution when the circuit stage is not complete', () => {
    renderWithHarness({
      activeKnot: {
        ...compiledKnot,
        status: 'verified',
      },
    });

    const executeButton = screen.getByRole('button', { name: /execute job on ibm_kyiv/i });
    expect(executeButton).toBeDisabled();
  });

  it('disables execution when shots input is invalid', async () => {
    const user = userEvent.setup();
    renderWithHarness();

    const executeButton = screen.getByRole('button', { name: /execute job on ibm_kyiv/i });
    const shotsInput = screen.getByRole('spinbutton');

    expect(executeButton).toBeEnabled();

    await user.clear(shotsInput);

    expect(executeButton).toBeDisabled();
    expect(screen.getByText(/shots must be a whole number between 1 and 100000/i)).toBeInTheDocument();
  });

  it('blocks submit when braid word is not contiguous', async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn<typeof fetch>();
    vi.stubGlobal('fetch', fetchMock);

    renderWithHarness({
      activeKnot: {
        ...compiledKnot,
        braidWord: 's1 s3 s1',
      },
    });

    await user.click(screen.getByRole('button', { name: /execute job on ibm_kyiv/i }));

    await waitFor(() => {
      expect(screen.getByText(/must use contiguous generators from s1 through s3/i)).toBeInTheDocument();
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('submits and polls with the expected payloads', async () => {
    const user = userEvent.setup();
    const onExecutionComplete = vi.fn();
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(
        jsonResponse({
          job_id: 'job-123',
          backend: 'ibm_kyiv',
          runtime_channel_used: 'ibm_cloud',
          runtime_instance_used: 'hub/group/project',
          status: 'QUEUED',
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          job_id: 'job-123',
          backend: 'ibm_kyiv',
          runtime_channel_used: 'ibm_cloud',
          runtime_instance_used: 'hub/group/project',
          counts: [{ name: '00', probability: 1 }],
          expectation_value: 1,
          jones_polynomial: 'V(t) = 1.000t^-4 + t^-3 + t^-1',
          status: 'COMPLETED',
        } satisfies ExperimentResult),
      );

    vi.stubGlobal('fetch', fetchMock);

    renderWithHarness({
      initialSettings: {
        shots: 4096,
        optimizationLevel: 2,
        closureMethod: 'trace',
      },
      onExecutionComplete,
    });

    await user.selectOptions(screen.getByRole('combobox'), 'ibm_cloud');
    await user.type(
      screen.getByPlaceholderText(/hub\/group\/project or cloud instance identifier/i),
      'hub/group/project',
    );

    const shotsInput = screen.getByRole('spinbutton');
    await user.clear(shotsInput);
    await user.type(shotsInput, '2048');

    await user.click(screen.getByRole('button', { name: /execute job on ibm_kyiv/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(2);
    });

    const [submitUrl, submitInit] = fetchMock.mock.calls[0]!;
    expect(submitUrl).toBe('/api/jobs/submit');
    expect(submitInit?.method).toBe('POST');
    const submitBody = JSON.parse(String(submitInit?.body));
    expect(submitBody).toMatchObject({
      backend_name: 'ibm_kyiv',
      braid_word: compiledKnot.braidWord,
      shots: 2048,
      optimization_level: 2,
      closure_method: 'trace',
      runtime_channel: 'ibm_cloud',
      runtime_instance: 'hub/group/project',
    });

    const [pollUrl, pollInit] = fetchMock.mock.calls[1]!;
    expect(pollUrl).toBe('/api/jobs/poll');
    expect(pollInit?.method).toBe('POST');
    const pollBody = JSON.parse(String(pollInit?.body));
    expect(pollBody).toEqual({
      job_id: 'job-123',
      runtime_channel: 'ibm_cloud',
      runtime_instance: 'hub/group/project',
    });

    await waitFor(() => {
      expect(onExecutionComplete).toHaveBeenCalledTimes(1);
    });
  });

  it('omits runtime channel when auto mode is selected', async () => {
    const user = userEvent.setup();
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(
        jsonResponse({
          job_id: 'job-999',
          backend: 'ibm_kyiv',
          status: 'QUEUED',
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          job_id: 'job-999',
          backend: 'ibm_kyiv',
          counts: [{ name: '00', probability: 1 }],
          expectation_value: 1,
          jones_polynomial: 'V(t) = 1.000t^-4 + t^-3 + t^-1',
          status: 'COMPLETED',
        } satisfies ExperimentResult),
      );

    vi.stubGlobal('fetch', fetchMock);

    renderWithHarness();

    await user.click(screen.getByRole('button', { name: /execute job on ibm_kyiv/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(2);
    });

    const submitInit = fetchMock.mock.calls[0]?.[1];
    const submitBody = JSON.parse(String(submitInit?.body));
    expect(submitBody.runtime_channel).toBeUndefined();
    expect(submitBody.closure_method).toBe('trace');

    const pollInit = fetchMock.mock.calls[1]?.[1];
    const pollBody = JSON.parse(String(pollInit?.body));
    expect(pollBody.runtime_channel).toBeUndefined();
  });

  it('shows a poll failure error and does not call completion handler', async () => {
    const user = userEvent.setup();
    const onExecutionComplete = vi.fn();
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(
        jsonResponse({
          job_id: 'job-fail',
          backend: 'ibm_kyiv',
          status: 'QUEUED',
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          job_id: 'job-fail',
          backend: 'ibm_kyiv',
          status: 'FAILED',
          detail: 'Backend calibration failed',
        }),
      );

    vi.stubGlobal('fetch', fetchMock);

    renderWithHarness({ onExecutionComplete });
    await user.click(screen.getByRole('button', { name: /execute job on ibm_kyiv/i }));

    await waitFor(() => {
      expect(screen.getByText(/backend calibration failed/i)).toBeInTheDocument();
    });

    expect(onExecutionComplete).not.toHaveBeenCalled();
  });

  it('shows a validation error when polling fails with 422', async () => {
    const user = userEvent.setup();
    const onExecutionComplete = vi.fn();
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(
        jsonResponse({
          job_id: 'job-422',
          backend: 'ibm_kyiv',
          status: 'QUEUED',
        }),
      )
      .mockResolvedValueOnce(jsonResponse({ detail: 'Unknown job id' }, 422));

    vi.stubGlobal('fetch', fetchMock);

    renderWithHarness({ onExecutionComplete });
    await user.click(screen.getByRole('button', { name: /execute job on ibm_kyiv/i }));

    await waitFor(() => {
      expect(screen.getByText(/request validation failed: unknown job id/i)).toBeInTheDocument();
    });

    expect(onExecutionComplete).not.toHaveBeenCalled();
  });

  it('shows a timeout error when polling never completes', async () => {
    const user = userEvent.setup();
    const onExecutionComplete = vi.fn();
    const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/api/jobs/submit')) {
        return jsonResponse({
          job_id: 'job-timeout',
          backend: 'ibm_kyiv',
          status: 'QUEUED',
        });
      }
      return jsonResponse({
        job_id: 'job-timeout',
        backend: 'ibm_kyiv',
        status: 'QUEUED',
      });
    });

    vi.stubGlobal('fetch', fetchMock);

    renderWithHarness({
      onExecutionComplete,
      pollIntervalMs: 1,
      maxPollAttempts: 3,
    });

    fireEvent.click(screen.getByRole('button', { name: /execute job on ibm_kyiv/i }));

    await waitFor(
      () => {
        expect(screen.getByText(/timed out waiting for the ibm runtime job to complete/i)).toBeInTheDocument();
      },
      { timeout: 5000 },
    );

    expect(fetchMock).toHaveBeenCalledTimes(4);
    expect(onExecutionComplete).not.toHaveBeenCalled();
  });

  it('loads accessible backend catalog with runtime settings', async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValueOnce(
      jsonResponse({
        runtime_channel_used: 'ibm_cloud',
        runtime_instance_used: 'hub/group/project',
        recommended_backend: 'ibm_osaka',
        backends: [
          { name: 'ibm_osaka', num_qubits: 127, pending_jobs: 3, operational: true },
          { name: 'ibm_kyiv', num_qubits: 127, pending_jobs: 7, operational: true },
        ],
      }),
    );

    vi.stubGlobal('fetch', fetchMock);
    renderWithHarness();

    await user.selectOptions(screen.getByRole('combobox'), 'ibm_cloud');
    await user.type(
      screen.getByPlaceholderText(/hub\/group\/project or cloud instance identifier/i),
      'hub/group/project',
    );

    await user.click(screen.getByRole('button', { name: /load accessible hardware/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });

    const [catalogUrl, catalogInit] = fetchMock.mock.calls[0]!;
    expect(catalogUrl).toBe('/api/backends');
    const catalogBody = JSON.parse(String(catalogInit?.body));
    expect(catalogBody).toEqual({
      runtime_channel: 'ibm_cloud',
      runtime_instance: 'hub/group/project',
    });

    expect(screen.getByText(/recommended backend/i)).toBeInTheDocument();
    expect(screen.getAllByText(/ibm_osaka/i).length).toBeGreaterThan(0);
  });

  it('resumes polling for a saved pending runtime job', async () => {
    const user = userEvent.setup();
    const onExecutionComplete = vi.fn();

    window.localStorage.setItem(
      PENDING_JOB_STORAGE_KEY,
      JSON.stringify({
        job_id: 'job-resume',
        backend_name: 'ibm_kyiv',
        runtime_channel: 'ibm_cloud',
        runtime_instance: 'hub/group/project',
      }),
    );

    const fetchMock = vi.fn<typeof fetch>().mockResolvedValueOnce(
      jsonResponse({
        job_id: 'job-resume',
        backend: 'ibm_kyiv',
        runtime_channel_used: 'ibm_cloud',
        runtime_instance_used: 'hub/group/project',
        counts: [{ name: '00', probability: 1 }],
        expectation_value: 1,
        jones_polynomial: 'V(t) = 1.000t^-4 + t^-3 + t^-1',
        status: 'COMPLETED',
      } satisfies ExperimentResult),
    );

    vi.stubGlobal('fetch', fetchMock);
    renderWithHarness({ onExecutionComplete });

    expect(screen.getByText(/pending runtime job found/i)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /resume pending job/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });

    const [pollUrl, pollInit] = fetchMock.mock.calls[0]!;
    expect(pollUrl).toBe('/api/jobs/poll');
    const pollBody = JSON.parse(String(pollInit?.body));
    expect(pollBody).toEqual({
      job_id: 'job-resume',
      runtime_channel: 'ibm_cloud',
      runtime_instance: 'hub/group/project',
    });

    await waitFor(() => {
      expect(onExecutionComplete).toHaveBeenCalledTimes(1);
    });
    expect(window.localStorage.getItem(PENDING_JOB_STORAGE_KEY)).toBeNull();
  });

  it('cancels an in-flight runtime job', async () => {
    const user = userEvent.setup();
    const onExecutionComplete = vi.fn();

    const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/api/jobs/submit')) {
        return jsonResponse({
          job_id: 'job-cancel',
          backend: 'ibm_kyiv',
          status: 'QUEUED',
        });
      }
      if (url.endsWith('/api/jobs/poll')) {
        return jsonResponse({
          job_id: 'job-cancel',
          backend: 'ibm_kyiv',
          status: 'QUEUED',
        });
      }
      if (url.endsWith('/api/jobs/cancel')) {
        return jsonResponse({
          job_id: 'job-cancel',
          backend: 'ibm_kyiv',
          status: 'CANCELLED',
          detail: 'Cancellation requested.',
        });
      }
      return jsonResponse({ detail: 'Unexpected route' }, 500);
    });

    vi.stubGlobal('fetch', fetchMock);
    renderWithHarness({
      onExecutionComplete,
      pollIntervalMs: 500,
      maxPollAttempts: 20,
    });

    await user.click(screen.getByRole('button', { name: /execute job on ibm_kyiv/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /cancel current job/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /cancel current job/i }));

    await waitFor(() => {
      expect(screen.getByText(/cancellation requested/i)).toBeInTheDocument();
    });

    const cancelCall = fetchMock.mock.calls.find(([url]) => String(url).endsWith('/api/jobs/cancel'));
    expect(cancelCall).toBeDefined();
    const cancelBody = JSON.parse(String(cancelCall?.[1]?.body));
    expect(cancelBody).toMatchObject({
      job_id: 'job-cancel',
    });
    expect(onExecutionComplete).not.toHaveBeenCalled();
  });

  it('keeps previous successful result visible when a retry fails', async () => {
    const user = userEvent.setup();
    const onExecutionComplete = vi.fn();

    const firstResult: ExperimentResult = {
      job_id: 'job-pass',
      backend: 'ibm_kyiv',
      runtime_channel_used: 'ibm_cloud',
      runtime_instance_used: 'hub/group/project',
      counts: [{ name: '00', probability: 1 }],
      expectation_value: 1,
      jones_polynomial: 'V(t) = 1.000t^-4 + t^-3 + t^-1',
      status: 'COMPLETED',
    };

    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(
        jsonResponse({
          job_id: 'job-pass',
          backend: 'ibm_kyiv',
          status: 'QUEUED',
        }),
      )
      .mockResolvedValueOnce(jsonResponse(firstResult))
      .mockResolvedValueOnce(
        jsonResponse({
          job_id: 'job-fail-2',
          backend: 'ibm_kyiv',
          status: 'QUEUED',
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          job_id: 'job-fail-2',
          backend: 'ibm_kyiv',
          status: 'FAILED',
          detail: 'Backend calibration failed',
        }),
      );

    vi.stubGlobal('fetch', fetchMock);
    renderWithHarness({
      onExecutionComplete,
      pollIntervalMs: 1,
      maxPollAttempts: 5,
    });

    await user.click(screen.getByRole('button', { name: /execute job on ibm_kyiv/i }));

    await waitFor(() => {
      expect(screen.getByText(/execution complete/i)).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /execute job on ibm_kyiv/i }));

    await waitFor(() => {
      expect(screen.getByText(/backend calibration failed/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/showing previous successful result/i)).toBeInTheDocument();
    expect(screen.getByText(firstResult.jones_polynomial)).toBeInTheDocument();
    expect(screen.getByText(/previous result job id: job-pass/i)).toBeInTheDocument();
    expect(onExecutionComplete).toHaveBeenCalledTimes(1);
  });
});
