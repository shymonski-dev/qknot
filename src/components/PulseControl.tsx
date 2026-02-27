import { Zap, Activity, Cpu } from 'lucide-react';
import { KnotData } from '../types';

interface Props {
  activeKnot: KnotData | null;
}

export default function PulseControl({ activeKnot }: Props) {
  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div>
        <h2 className="text-2xl font-semibold text-zinc-100 tracking-tight">4. Pulse-Level Compilation</h2>
        <p className="text-zinc-400 mt-2">
          Intercept the transpiled circuit and replace standard CX/Rzz gates with pre-calibrated, shortened Cross-Resonance microwave pulses to maximize coherence time.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
            <div className="flex items-center gap-2 mb-6">
              <Zap className="w-5 h-5 text-amber-500" />
              <h3 className="font-medium text-zinc-200">Pulse Calibration</h3>
            </div>
            
            <div className="space-y-4">
              <div className="bg-[#0a0a0a] border border-zinc-800 rounded-md p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Target Qubit Pair</span>
                  <span className="text-xs font-mono text-zinc-300">Q0 to Q1</span>
                </div>
                <div className="space-y-2 mt-4">
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-zinc-500">Anharmonicity</span>
                    <span className="text-amber-400">-330 MHz</span>
                  </div>
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-zinc-500">Coupling Strength (J)</span>
                    <span className="text-amber-400">2.4 MHz</span>
                  </div>
                </div>
              </div>

              <button className="w-full bg-amber-500 hover:bg-amber-600 text-amber-950 font-medium py-2.5 rounded-md transition-colors flex items-center justify-center gap-2">
                <Activity className="w-4 h-4" />
                Run Hamiltonian Tomography
              </button>
              
              <button className="w-full bg-zinc-800 hover:bg-zinc-700 text-zinc-200 font-medium py-2.5 rounded-md transition-colors border border-zinc-700 flex items-center justify-center gap-2">
                <Cpu className="w-4 h-4" />
                Apply CR Pulses
              </button>
            </div>
          </div>
        </div>

        <div className="lg:col-span-2 bg-[#111111] border border-zinc-800 rounded-xl p-6 flex flex-col min-h-[400px]">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-medium text-zinc-200">Microwave Pulse Schedule</h3>
            <div className="flex gap-2">
              <span className="px-2 py-1 bg-amber-500/10 border border-amber-500/20 rounded text-xs font-mono text-amber-400">
                Duration: 180ns (vs 320ns standard)
              </span>
            </div>
          </div>
          
          <div className="flex-1 border border-zinc-800 rounded-md bg-[#0a0a0a] p-6 relative overflow-hidden flex items-center justify-center">
            {/* Mock Pulse Visualization */}
            <svg viewBox="0 0 600 200" className="w-full h-full opacity-80">
              {/* Grid */}
              <g stroke="#27272a" strokeWidth="1" strokeDasharray="4 4">
                <line x1="0" y1="50" x2="600" y2="50" />
                <line x1="0" y1="100" x2="600" y2="100" />
                <line x1="0" y1="150" x2="600" y2="150" />
              </g>

              {/* D0 Drive Channel */}
              <text x="10" y="45" fill="#71717a" fontSize="12" fontFamily="monospace">D0 (Drive)</text>
              <path d="M 50 50 Q 100 20 150 50 T 250 50" fill="none" stroke="#3b82f6" strokeWidth="2" />
              <path d="M 50 50 Q 100 20 150 50 T 250 50" fill="#3b82f6" opacity="0.2" />

              {/* U0 Control Channel (Cross-Resonance) */}
              <text x="10" y="95" fill="#71717a" fontSize="12" fontFamily="monospace">U0 (CR)</text>
              <path d="M 150 100 Q 200 60 250 100 T 350 100" fill="none" stroke="#f59e0b" strokeWidth="2" />
              <path d="M 150 100 Q 200 60 250 100 T 350 100" fill="#f59e0b" opacity="0.2" />
              
              {/* D1 Drive Channel */}
              <text x="10" y="145" fill="#71717a" fontSize="12" fontFamily="monospace">D1 (Drive)</text>
              <path d="M 250 150 Q 300 120 350 150 T 450 150" fill="none" stroke="#10b981" strokeWidth="2" />
              <path d="M 250 150 Q 300 120 350 150 T 450 150" fill="#10b981" opacity="0.2" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}
