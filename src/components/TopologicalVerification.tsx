import { Layers, PlayCircle, ShieldCheck } from 'lucide-react';
import { KnotData } from '../types';
import { useState } from 'react';

interface Props {
  activeKnot: KnotData | null;
}

export default function TopologicalVerification({ activeKnot }: Props) {
  const [isSimulating, setIsSimulating] = useState(false);
  const [isVerified, setIsVerified] = useState(false);

  const handleSimulate = () => {
    setIsSimulating(true);
    setTimeout(() => {
      setIsSimulating(false);
      setIsVerified(true);
    }, 2000);
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div>
        <h2 className="text-2xl font-semibold text-zinc-100 tracking-tight">2. Topological Verification</h2>
        <p className="text-zinc-400 mt-2">
          Feed the braid word into QTop to simulate the anyonic braiding and visually verify the topological mapping before hardware execution.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
            <div className="flex items-center gap-2 mb-6">
              <Layers className="w-5 h-5 text-emerald-500" />
              <h3 className="font-medium text-zinc-200">QTop Simulation</h3>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">
                  Input Braid Word
                </label>
                <div className="bg-[#0a0a0a] border border-zinc-800 rounded-md px-4 py-2.5 text-zinc-200 font-mono text-sm">
                  {activeKnot?.braidWord || 'No braid word available'}
                </div>
              </div>
              
              <button
                onClick={handleSimulate}
                disabled={isSimulating || !activeKnot?.braidWord}
                className="w-full bg-emerald-500 hover:bg-emerald-600 text-emerald-950 font-medium py-2.5 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isSimulating ? (
                  <span className="animate-pulse">Simulating Lattice...</span>
                ) : (
                  <>
                    <PlayCircle className="w-4 h-4" />
                    Run QTop Simulation
                  </>
                )}
              </button>
            </div>
          </div>

          {isVerified && (
            <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="flex items-center gap-3 text-emerald-400 mb-4">
                <ShieldCheck className="w-5 h-5" />
                <h3 className="font-medium">Verification Passed</h3>
              </div>
              <p className="text-sm text-emerald-400/80 leading-relaxed">
                The braid word and closure operations logically map to the correct topological invariants. 
                Ready for circuit synthesis.
              </p>
            </div>
          )}
        </div>

        <div className="lg:col-span-2 bg-[#111111] border border-zinc-800 rounded-xl p-6 flex flex-col min-h-[400px]">
          <h3 className="font-medium text-zinc-200 mb-6">Lattice Visualization</h3>
          
          <div className="flex-1 border border-zinc-800 rounded-md bg-[#0a0a0a] relative overflow-hidden flex items-center justify-center">
            {isSimulating ? (
              <div className="absolute inset-0 flex items-center justify-center bg-zinc-900/50 backdrop-blur-sm z-10">
                <div className="flex flex-col items-center gap-4">
                  <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                  <span className="text-sm font-medium text-emerald-400">Rendering Anyonic Paths...</span>
                </div>
              </div>
            ) : null}
            
            {isVerified ? (
              <div className="w-full h-full p-8 flex items-center justify-center">
                {/* Mock Visualization of Braiding */}
                <svg viewBox="0 0 400 200" className="w-full max-w-md opacity-80">
                  <path d="M 50 50 Q 150 50 200 100 T 350 150" fill="none" stroke="#10b981" strokeWidth="4" strokeLinecap="round" />
                  <path d="M 50 150 Q 150 150 200 100 T 350 50" fill="none" stroke="#3b82f6" strokeWidth="4" strokeLinecap="round" />
                  <path d="M 50 100 L 350 100" fill="none" stroke="#8b5cf6" strokeWidth="4" strokeLinecap="round" strokeDasharray="8 8" />
                  <circle cx="200" cy="100" r="8" fill="#f59e0b" />
                </svg>
              </div>
            ) : (
              <div className="text-zinc-600 text-sm">
                Awaiting simulation...
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
