import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import TopologicalVerification from '../TopologicalVerification';
import type { KnotData, KnotVerificationResponse } from '../../types';

const pendingKnot: KnotData = {
  id: 'k-1',
  name: 'Trefoil Knot (3_1)',
  dowkerNotation: '4 6 2',
  braidWord: 's1 s2^-1 s1 s2^-1',
  rootOfUnity: 5,
  status: 'pending',
};

function jsonResponse(payload: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
  } as Response;
}

describe('TopologicalVerification', () => {
  it('submits braid word to verification endpoint and marks verified on pass', async () => {
    const user = userEvent.setup();
    const onVerified = vi.fn();
    const payload: KnotVerificationResponse = {
      is_verified: true,
      status: 'verified',
      detail: 'Topological verification passed with connected three-strand braid evidence.',
      evidence: {
        token_count: 4,
        generator_counts: { s1: 2, s2: 2 },
        inverse_count: 2,
        net_writhe: 0,
        generator_switches: 3,
        alternation_ratio: 1,
        strand_connectivity: 'connected-3-strand',
      },
    };

    const fetchMock = vi.fn<typeof fetch>().mockResolvedValueOnce(jsonResponse(payload));
    vi.stubGlobal('fetch', fetchMock);

    render(<TopologicalVerification activeKnot={pendingKnot} onVerified={onVerified} />);

    await user.click(screen.getByRole('button', { name: /verify topological mapping/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });

    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe('http://localhost:8000/api/knot/verify');
    expect(init?.method).toBe('POST');
    expect(JSON.parse(String(init?.body))).toEqual({
      braid_word: pendingKnot.braidWord,
    });

    await waitFor(() => {
      expect(onVerified).toHaveBeenCalledTimes(1);
    });
    expect(screen.getByRole('heading', { name: /verification passed/i })).toBeInTheDocument();
    expect(screen.getByText(/connected three-strand braid evidence/i)).toBeInTheDocument();
  });

  it('shows failed verification details and does not mark verified', async () => {
    const user = userEvent.setup();
    const onVerified = vi.fn();
    const payload: KnotVerificationResponse = {
      is_verified: false,
      status: 'failed',
      detail: 'Verification failed: braid word must include both s1 and s2 to demonstrate three-strand topological connectivity.',
      evidence: {
        token_count: 3,
        generator_counts: { s1: 3, s2: 0 },
        inverse_count: 0,
        net_writhe: 3,
        generator_switches: 0,
        alternation_ratio: 0,
        strand_connectivity: 'partial-3-strand',
      },
    };

    const fetchMock = vi.fn<typeof fetch>().mockResolvedValueOnce(jsonResponse(payload));
    vi.stubGlobal('fetch', fetchMock);

    render(
      <TopologicalVerification
        activeKnot={{ ...pendingKnot, braidWord: 's1 s1 s1' }}
        onVerified={onVerified}
      />,
    );

    await user.click(screen.getByRole('button', { name: /verify topological mapping/i }));

    await waitFor(() => {
      expect(screen.getByText(/verification failed: braid word must include both s1 and s2/i)).toBeInTheDocument();
    });
    expect(onVerified).not.toHaveBeenCalled();
  });

  it('shows request validation error for invalid braid tokens', async () => {
    const user = userEvent.setup();
    const onVerified = vi.fn();
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse({ detail: "Unsupported braid token 's3'." }, 422));
    vi.stubGlobal('fetch', fetchMock);

    render(
      <TopologicalVerification
        activeKnot={{ ...pendingKnot, braidWord: 's1 s3' }}
        onVerified={onVerified}
      />,
    );

    await user.click(screen.getByRole('button', { name: /verify topological mapping/i }));

    await waitFor(() => {
      expect(screen.getByText(/input validation failed: unsupported braid token 's3'\./i)).toBeInTheDocument();
    });
    expect(onVerified).not.toHaveBeenCalled();
  });
});
