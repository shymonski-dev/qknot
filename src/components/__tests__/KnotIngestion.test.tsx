import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import KnotIngestion from '../KnotIngestion';
import type { KnotData, KnotIngestionResponse } from '../../types';

const activeKnot: KnotData = {
  id: 'k-1',
  name: 'Trefoil Knot (3_1)',
  dowkerNotation: '4 6 2',
  braidWord: 's1 s2^-1 s1',
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

describe('KnotIngestion', () => {
  it('submits notation to ingestion endpoint and forwards compiled payload', async () => {
    const user = userEvent.setup();
    const onCompiled = vi.fn();
    const responsePayload: KnotIngestionResponse = {
      dowker_notation_normalized: '4 6 2',
      crossing_count: 3,
      knot_name: 'Trefoil Knot (3_1)',
      braid_word: 's1 s2^-1 s1 s2^-1',
      root_of_unity: 5,
      is_catalog_match: true,
    };

    const fetchMock = vi.fn<typeof fetch>().mockResolvedValueOnce(jsonResponse(responsePayload));
    vi.stubGlobal('fetch', fetchMock);

    render(<KnotIngestion activeKnot={activeKnot} onCompiled={onCompiled} />);

    const notationInput = screen.getByPlaceholderText(/e\.g\., 4 6 2/i);
    await user.clear(notationInput);
    await user.type(notationInput, '4,-6,2');
    await user.click(screen.getByRole('button', { name: /compile to braid word/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });

    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe('/api/knot/ingest');
    expect(init?.method).toBe('POST');
    expect(JSON.parse(String(init?.body))).toEqual({ dowker_notation: '4,-6,2' });

    await waitFor(() => {
      expect(onCompiled).toHaveBeenCalledWith(responsePayload);
    });
    expect(screen.getByText(/loaded catalog mapping for trefoil knot/i)).toBeInTheDocument();
  });

  it('shows validation error returned by backend', async () => {
    const user = userEvent.setup();
    const onCompiled = vi.fn();
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse({ detail: "Dowker notation token '3' must be even." }, 422));
    vi.stubGlobal('fetch', fetchMock);

    render(<KnotIngestion activeKnot={activeKnot} onCompiled={onCompiled} />);

    const notationInput = screen.getByPlaceholderText(/e\.g\., 4 6 2/i);
    await user.clear(notationInput);
    await user.type(notationInput, '4 3 2');
    await user.click(screen.getByRole('button', { name: /compile to braid word/i }));

    await waitFor(() => {
      expect(screen.getByText(/input validation failed: dowker notation token '3' must be even\./i)).toBeInTheDocument();
    });
    expect(onCompiled).not.toHaveBeenCalled();
  });

  it('shows connectivity error when backend is unreachable', async () => {
    const user = userEvent.setup();
    const onCompiled = vi.fn();
    const fetchMock = vi.fn<typeof fetch>().mockRejectedValueOnce(new TypeError('Failed to fetch'));
    vi.stubGlobal('fetch', fetchMock);

    render(<KnotIngestion activeKnot={activeKnot} onCompiled={onCompiled} />);

    await user.click(screen.getByRole('button', { name: /compile to braid word/i }));

    await waitFor(() => {
      expect(screen.getByText(/could not reach the backend api\./i)).toBeInTheDocument();
    });
    expect(onCompiled).not.toHaveBeenCalled();
  });
});
