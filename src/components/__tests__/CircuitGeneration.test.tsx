import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';

import CircuitGeneration from '../CircuitGeneration';
import type { ExecutionSettings, KnotCircuitGenerationResponse, KnotData } from '../../types';

const verifiedKnot: KnotData = {
  id: 'k-1',
  name: 'Trefoil Knot (3_1)',
  dowkerNotation: '4 6 2',
  braidWord: 's1 s2^-1 s1 s2^-1',
  rootOfUnity: 5,
  status: 'verified',
};

function jsonResponse(payload: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
  } as Response;
}

function renderWithHarness(options?: {
  activeKnot?: KnotData | null;
  onGenerateCircuit?: (payload: KnotCircuitGenerationResponse) => void;
}) {
  const activeKnot = options?.activeKnot ?? verifiedKnot;
  const onGenerateCircuit = options?.onGenerateCircuit ?? vi.fn();

  function Harness() {
    const [executionSettings, setExecutionSettings] = useState<ExecutionSettings>({
      shots: 8192,
      optimizationLevel: 2,
      closureMethod: 'trace',
    });

    return (
      <CircuitGeneration
        activeKnot={activeKnot}
        targetBackend="ibm_kyiv"
        executionSettings={executionSettings}
        setExecutionSettings={setExecutionSettings}
        onGenerateCircuit={onGenerateCircuit}
      />
    );
  }

  return {
    ...render(<Harness />),
    onGenerateCircuit,
  };
}

describe('CircuitGeneration', () => {
  it('disables generation before verification is complete', () => {
    renderWithHarness({
      activeKnot: { ...verifiedKnot, status: 'pending' },
    });

    const button = screen.getByRole('button', { name: /generate circuit/i });
    expect(button).toBeDisabled();
  });

  it('submits generation request with expected payload and renders summary', async () => {
    const user = userEvent.setup();
    const onGenerateCircuit = vi.fn();
    const payload: KnotCircuitGenerationResponse = {
      target_backend: 'ibm_kyiv',
      optimization_level: 2,
      closure_method: 'trace',
      braid_word: 's1 s2^-1 s1 s2^-1',
      circuit_summary: {
        depth: 12,
        size: 20,
        width: 4,
        num_qubits: 3,
        num_clbits: 1,
        two_qubit_gate_count: 6,
        measurement_count: 1,
        operation_counts: { cx: 4, cp: 2, h: 2, measure: 1 },
        signature: 'abc123signature',
      },
    };

    const fetchMock = vi.fn<typeof fetch>().mockResolvedValueOnce(jsonResponse(payload));
    vi.stubGlobal('fetch', fetchMock);

    renderWithHarness({ onGenerateCircuit });
    await user.click(screen.getByRole('button', { name: /generate circuit/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });

    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe('/api/knot/circuit/generate');
    expect(init?.method).toBe('POST');
    expect(JSON.parse(String(init?.body))).toEqual({
      braid_word: verifiedKnot.braidWord,
      optimization_level: 2,
      closure_method: 'trace',
      target_backend: 'ibm_kyiv',
    });

    await waitFor(() => {
      expect(onGenerateCircuit).toHaveBeenCalledWith(payload);
    });
    expect(screen.getByText(/generated circuit signature abc123signature\./i)).toBeInTheDocument();
  });

  it('shows backend validation errors', async () => {
    const user = userEvent.setup();
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse({ detail: "Closure method must be either 'trace' or 'plat'." }, 422));
    vi.stubGlobal('fetch', fetchMock);

    renderWithHarness();
    await user.click(screen.getByRole('button', { name: /generate circuit/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/input validation failed: closure method must be either 'trace' or 'plat'\./i),
      ).toBeInTheDocument();
    });
  });
});
