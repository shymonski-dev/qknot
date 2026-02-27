import { useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { AlertCircle, Check, Cpu, GitMerge, Settings2 } from 'lucide-react';
import { ExecutionSettings, KnotCircuitGenerationResponse, KnotData } from '../types';

interface Props {
  activeKnot: KnotData | null;
  targetBackend: string;
  executionSettings: ExecutionSettings;
  setExecutionSettings: Dispatch<SetStateAction<ExecutionSettings>>;
  onGenerateCircuit: (generatedCircuit: KnotCircuitGenerationResponse) => void;
}

function isVerifiedOrLater(status: KnotData['status'] | undefined) {
  return status === 'verified' || status === 'compiled' || status === 'executed';
}

export default function CircuitGeneration({
  activeKnot,
  targetBackend,
  executionSettings,
  setExecutionSettings,
  onGenerateCircuit,
}: Props) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const canGenerate = Boolean(activeKnot?.braidWord?.trim()) && isVerifiedOrLater(activeKnot?.status);
  const circuitSummary = activeKnot?.circuitSummary;

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

  const handleGenerateCircuit = async () => {
    if (!canGenerate) {
      return;
    }

    setIsGenerating(true);
    setError(null);
    setStatusMessage(null);

    try {
      const response = await fetch('/api/knot/circuit/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          braid_word: activeKnot?.braidWord || '',
          optimization_level: executionSettings.optimizationLevel,
          closure_method: executionSettings.closureMethod,
          target_backend: targetBackend,
        }),
      });

      if (!response.ok) {
        const detail = await readErrorDetail(response, 'Failed to generate circuit.');
        if (response.status === 422) {
          throw new Error(`Input validation failed: ${detail}`);
        }
        throw new Error(`Server error (${response.status}): ${detail}`);
      }

      const payload = (await response.json()) as KnotCircuitGenerationResponse;
      onGenerateCircuit(payload);
      setStatusMessage(`Generated circuit signature ${payload.circuit_summary.signature}.`);
    } catch (err: unknown) {
      if (err instanceof Error) {
        if (err.name === 'TypeError') {
          setError('Could not reach the backend API.');
        } else {
          setError(err.message || 'Failed to generate circuit.');
        }
      } else {
        setError('Failed to generate circuit.');
      }
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div>
        <h2 className="text-2xl font-semibold text-zinc-100 tracking-tight">3. Circuit Generation</h2>
        <p className="text-zinc-400 mt-2">
          Generate backend computed circuit metadata from the verified braid word and current transpiler settings.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
            <div className="flex items-center gap-2 mb-6">
              <Settings2 className="w-5 h-5 text-emerald-500" />
              <h3 className="font-medium text-zinc-200">Transpiler Settings</h3>
            </div>

            <div className="space-y-5">
              {error && (
                <div data-testid="circuit-error" className="bg-red-500/10 border border-red-500/20 rounded-md p-3 flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                  <p className="text-xs text-red-300">{error}</p>
                </div>
              )}

              {statusMessage && !error && (
                <div data-testid="circuit-status" className="bg-zinc-800/50 border border-zinc-700 rounded-md p-3">
                  <p className="text-xs text-zinc-300">{statusMessage}</p>
                </div>
              )}

              <div>
                <label className="block text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">
                  Target Backend
                </label>
                <div className="bg-[#0a0a0a] border border-zinc-800 rounded-md px-4 py-2.5 text-zinc-200 font-mono text-sm flex items-center justify-between">
                  <span>{targetBackend}</span>
                  <Cpu className="w-4 h-4 text-zinc-500" />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">
                  Optimization Level
                </label>
                <select
                  value={executionSettings.optimizationLevel}
                  onChange={(e) => {
                    const value = Number.parseInt(e.target.value, 10);
                    if (value >= 0 && value <= 3) {
                      setExecutionSettings((prev) => ({
                        ...prev,
                        optimizationLevel: value as ExecutionSettings['optimizationLevel'],
                      }));
                    }
                  }}
                  className="w-full bg-[#0a0a0a] border border-zinc-800 rounded-md px-4 py-2.5 text-zinc-200 font-mono text-sm focus:outline-none focus:border-emerald-500/50"
                >
                  <option value="3">Level 3 (Heavy Compression)</option>
                  <option value="2">Level 2</option>
                  <option value="1">Level 1</option>
                  <option value="0">Level 0 (None)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">
                  Closure Method
                </label>
                <select
                  value={executionSettings.closureMethod}
                  onChange={(e) =>
                    setExecutionSettings((prev) => ({
                      ...prev,
                      closureMethod: e.target.value as ExecutionSettings['closureMethod'],
                    }))
                  }
                  className="w-full bg-[#0a0a0a] border border-zinc-800 rounded-md px-4 py-2.5 text-zinc-200 font-mono text-sm focus:outline-none focus:border-emerald-500/50"
                >
                  <option value="trace">Trace Closure (Hadamard Test)</option>
                  <option value="plat">Plat Closure</option>
                </select>
              </div>

              <button
                data-testid="generate-circuit-button"
                onClick={handleGenerateCircuit}
                disabled={isGenerating || !canGenerate}
                className="w-full bg-emerald-500 hover:bg-emerald-600 text-emerald-950 font-medium py-2.5 rounded-md transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isGenerating ? (
                  <span className="animate-pulse">Generating Circuit...</span>
                ) : (
                  <>
                    <GitMerge className="w-4 h-4" />
                    Generate Circuit
                  </>
                )}
              </button>

              {!canGenerate && (
                <p className="text-[10px] text-zinc-500 leading-tight">
                  Verify the braid mapping first to enable circuit generation.
                </p>
              )}
            </div>
          </div>
        </div>

        <div className="lg:col-span-2 bg-[#111111] border border-zinc-800 rounded-xl p-6 flex flex-col min-h-[400px]">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-medium text-zinc-200">Circuit Metadata</h3>
            {circuitSummary && (
              <div className="flex items-center gap-2 text-emerald-400 text-xs">
                <Check className="w-4 h-4" />
                <span className="font-mono">Ready</span>
              </div>
            )}
          </div>

          <div className="flex-1 border border-zinc-800 rounded-md bg-[#0a0a0a] p-6 overflow-auto">
            {circuitSummary ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="bg-zinc-900 border border-zinc-800 rounded-md p-3">
                    <div className="text-zinc-500 text-xs uppercase tracking-wider">Depth</div>
                    <div className="text-zinc-200 font-mono mt-1">{circuitSummary.depth}</div>
                  </div>
                  <div className="bg-zinc-900 border border-zinc-800 rounded-md p-3">
                    <div className="text-zinc-500 text-xs uppercase tracking-wider">Two Qubit Gates</div>
                    <div className="text-zinc-200 font-mono mt-1">{circuitSummary.two_qubit_gate_count}</div>
                  </div>
                  <div className="bg-zinc-900 border border-zinc-800 rounded-md p-3">
                    <div className="text-zinc-500 text-xs uppercase tracking-wider">Width</div>
                    <div className="text-zinc-200 font-mono mt-1">{circuitSummary.width}</div>
                  </div>
                  <div className="bg-zinc-900 border border-zinc-800 rounded-md p-3">
                    <div className="text-zinc-500 text-xs uppercase tracking-wider">Measurement Count</div>
                    <div className="text-zinc-200 font-mono mt-1">{circuitSummary.measurement_count}</div>
                  </div>
                  <div className="bg-zinc-900 border border-zinc-800 rounded-md p-3">
                    <div className="text-zinc-500 text-xs uppercase tracking-wider">Qubits / Clbits</div>
                    <div className="text-zinc-200 font-mono mt-1">
                      {circuitSummary.num_qubits} / {circuitSummary.num_clbits}
                    </div>
                  </div>
                  <div className="bg-zinc-900 border border-zinc-800 rounded-md p-3">
                    <div className="text-zinc-500 text-xs uppercase tracking-wider">Circuit Signature</div>
                    <div className="text-zinc-200 font-mono mt-1">{circuitSummary.signature}</div>
                  </div>
                </div>

                <div className="bg-zinc-900 border border-zinc-800 rounded-md p-3">
                  <div className="text-zinc-500 text-xs uppercase tracking-wider mb-2">Operation Counts</div>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs font-mono">
                    {Object.entries(circuitSummary.operation_counts).map(([operation, count]) => (
                      <div key={operation} className="flex justify-between bg-[#0a0a0a] border border-zinc-800 rounded px-2 py-1">
                        <span className="text-zinc-400">{operation}</span>
                        <span className="text-zinc-200">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-zinc-600 text-sm">
                Generate a circuit to view backend computed metadata.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
