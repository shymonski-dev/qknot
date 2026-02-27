import { useState } from 'react';
import { KnotData, KnotIngestionResponse } from '../types';
import { Database, ArrowRight, Check, AlertCircle } from 'lucide-react';

interface Props {
  activeKnot: KnotData | null;
  onCompiled: (compiledKnot: KnotIngestionResponse) => void;
}

export default function KnotIngestion({ activeKnot, onCompiled }: Props) {
  const [notation, setNotation] = useState(activeKnot?.dowkerNotation || '');
  const [isCompiling, setIsCompiling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const readErrorDetail = async (response: Response, fallbackMessage: string) => {
    let detail = fallbackMessage;
    try {
      const errData = await response.json();
      if (typeof errData?.detail === 'string' && errData.detail.trim()) {
        detail = errData.detail;
      }
    } catch {
      // Keep fallback when server response body is not JSON.
    }
    return detail;
  };

  const handleCompile = async () => {
    if (!notation.trim()) {
      setError('Dowker notation is required.');
      return;
    }

    setIsCompiling(true);
    setError(null);
    setStatusMessage(null);

    try {
      const response = await fetch('/api/knot/ingest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          dowker_notation: notation,
        }),
      });

      if (!response.ok) {
        const detail = await readErrorDetail(response, 'Failed to compile knot notation.');
        if (response.status === 422) {
          throw new Error(`Input validation failed: ${detail}`);
        }
        throw new Error(`Server error (${response.status}): ${detail}`);
      }

      const payload = (await response.json()) as KnotIngestionResponse;
      onCompiled(payload);
      setNotation(payload.dowker_notation_normalized);
      if (payload.is_catalog_match) {
        setStatusMessage(`Loaded catalog mapping for ${payload.knot_name}.`);
      } else {
        setStatusMessage(`Compiled ${payload.crossing_count}-crossing notation with fallback mapping.`);
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        if (err.name === 'TypeError') {
          setError('Could not reach the backend API.');
        } else {
          setError(err.message || 'Failed to compile knot notation.');
        }
      } else {
        setError('Failed to compile knot notation.');
      }
    } finally {
      setIsCompiling(false);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div>
        <h2 className="text-2xl font-semibold text-zinc-100 tracking-tight">1. Knot Ingestion</h2>
        <p className="text-zinc-400 mt-2">
          Input standard knot notation (e.g., Dowker notation) and classically compile it into a Braid Word.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
          <div className="flex items-center gap-2 mb-6">
            <Database className="w-5 h-5 text-emerald-500" />
            <h3 className="font-medium text-zinc-200">Input Notation</h3>
          </div>
          
          <div className="space-y-4">
            {error && (
              <div data-testid="ingest-error" className="bg-red-500/10 border border-red-500/20 rounded-md p-3 flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <p className="text-xs text-red-300">{error}</p>
              </div>
            )}

            {statusMessage && !error && (
              <div data-testid="ingest-status" className="bg-zinc-800/50 border border-zinc-700 rounded-md p-3">
                <p className="text-xs text-zinc-300">{statusMessage}</p>
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">
                Dowker Notation
              </label>
              <input
                data-testid="dowker-input"
                type="text"
                value={notation}
                onChange={(e) => setNotation(e.target.value)}
                className="w-full bg-[#0a0a0a] border border-zinc-800 rounded-md px-4 py-2.5 text-zinc-200 font-mono text-sm focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/50 transition-all"
                placeholder="e.g., 4 6 2"
              />
            </div>

            <button
              data-testid="compile-button"
              onClick={handleCompile}
              disabled={isCompiling || !notation.trim()}
              className="w-full bg-emerald-500 hover:bg-emerald-600 text-emerald-950 font-medium py-2.5 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isCompiling ? (
                <span className="animate-pulse">Compiling via Snappy/SageMath...</span>
              ) : (
                <>
                  Compile to Braid Word
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </div>

        <div className="bg-[#111111] border border-zinc-800 rounded-xl p-6 flex flex-col">
          <h3 className="font-medium text-zinc-200 mb-6">Compilation Result</h3>
          
          <div className="flex-1 flex flex-col justify-center">
            {activeKnot?.braidWord ? (
              <div className="space-y-6">
                <div className="flex items-center gap-3 text-emerald-400">
                  <Check className="w-5 h-5" />
                  <span className="text-sm font-medium">Successfully compiled</span>
                </div>
                
                <div className="bg-zinc-900 border border-zinc-800 rounded-md p-4">
                  <label className="block text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">
                    Braid Word
                  </label>
                  <div data-testid="braid-word-result" className="font-mono text-lg text-zinc-200 tracking-wider">
                    {activeKnot.braidWord}
                  </div>
                </div>
                
                <p className="text-xs text-zinc-500 leading-relaxed">
                  This braid word represents the sequence of generators in the Braid Group. 
                  These will physically translate to solutions of the Yang-Baxter equation on the quantum hardware.
                </p>
              </div>
            ) : (
              <div className="text-center text-zinc-600 text-sm">
                Awaiting compilation...
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
