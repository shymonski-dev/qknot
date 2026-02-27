import type { Dispatch, SetStateAction } from 'react';
import { GitMerge, Cpu, Settings2 } from 'lucide-react';
import { ExecutionSettings, KnotData } from '../types';

interface Props {
  activeKnot: KnotData | null;
  targetBackend: string;
  executionSettings: ExecutionSettings;
  setExecutionSettings: Dispatch<SetStateAction<ExecutionSettings>>;
  onGenerateCircuit: () => void;
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
  const canGenerate = Boolean(activeKnot?.braidWord?.trim()) && isVerifiedOrLater(activeKnot?.status);

  const handleGenerateCircuit = () => {
    if (!canGenerate) {
      return;
    }
    onGenerateCircuit();
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div>
        <h2 className="text-2xl font-semibold text-zinc-100 tracking-tight">3. Circuit Generation</h2>
        <p className="text-zinc-400 mt-2">
          Use Qiskit Terra to generate high-level quantum circuits. Map strands to IBM qubits and apply Yang-Baxter unitaries.
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
                onClick={handleGenerateCircuit}
                disabled={!canGenerate}
                className="w-full bg-emerald-500 hover:bg-emerald-600 text-emerald-950 font-medium py-2.5 rounded-md transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <GitMerge className="w-4 h-4" />
                Generate Circuit
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
            <h3 className="font-medium text-zinc-200">Circuit Diagram</h3>
            <div className="flex gap-2">
              <span className="px-2 py-1 bg-zinc-800 rounded text-xs font-mono text-zinc-400">Depth: 42</span>
              <span className="px-2 py-1 bg-zinc-800 rounded text-xs font-mono text-zinc-400">CX Count: 18</span>
            </div>
          </div>
          
          <div className="flex-1 border border-zinc-800 rounded-md bg-[#0a0a0a] p-6 overflow-x-auto">
            {/* Mock Circuit Visualization */}
            <div className="min-w-[600px] h-full flex flex-col justify-center gap-8 font-mono text-sm text-zinc-400">
              
              {/* Ancilla Qubit */}
              <div className="flex items-center gap-4">
                <div className="w-12 text-right">q_anc</div>
                <div className="flex-1 h-px bg-zinc-800 relative flex items-center">
                  <div className="absolute left-8 w-8 h-8 bg-emerald-500/20 border border-emerald-500/50 rounded flex items-center justify-center text-emerald-400">H</div>
                  <div className="absolute left-32 w-2 h-2 rounded-full bg-emerald-500" />
                  <div className="absolute left-64 w-2 h-2 rounded-full bg-emerald-500" />
                  <div className="absolute left-96 w-8 h-8 bg-emerald-500/20 border border-emerald-500/50 rounded flex items-center justify-center text-emerald-400">H</div>
                </div>
              </div>

              {/* Data Qubits */}
              <div className="flex items-center gap-4">
                <div className="w-12 text-right">q_0</div>
                <div className="flex-1 h-px bg-zinc-800 relative flex items-center">
                  <div className="absolute left-32 w-8 h-8 bg-blue-500/20 border border-blue-500/50 rounded flex items-center justify-center text-blue-400">U</div>
                  <div className="absolute left-[136px] top-[-32px] w-px h-[32px] bg-emerald-500" />
                </div>
              </div>

              <div className="flex items-center gap-4">
                <div className="w-12 text-right">q_1</div>
                <div className="flex-1 h-px bg-zinc-800 relative flex items-center">
                  <div className="absolute left-64 w-8 h-8 bg-blue-500/20 border border-blue-500/50 rounded flex items-center justify-center text-blue-400">U</div>
                  <div className="absolute left-[264px] top-[-64px] w-px h-[64px] bg-emerald-500" />
                </div>
              </div>

            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
