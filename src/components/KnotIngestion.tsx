import { useState } from 'react';
import { KnotData } from '../types';
import { Database, ArrowRight, Check } from 'lucide-react';

interface Props {
  activeKnot: KnotData | null;
  setActiveKnot: (k: KnotData) => void;
}

export default function KnotIngestion({ activeKnot, setActiveKnot }: Props) {
  const [notation, setNotation] = useState(activeKnot?.dowkerNotation || '');
  const [isCompiling, setIsCompiling] = useState(false);

  const handleCompile = () => {
    setIsCompiling(true);
    setTimeout(() => {
      setIsCompiling(false);
      if (activeKnot) {
        setActiveKnot({
          ...activeKnot,
          dowkerNotation: notation,
          braidWord: 's1 s2^-1 s1 s2^-1', // Mock compilation result
        });
      }
    }, 1500);
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
            <div>
              <label className="block text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">
                Dowker Notation
              </label>
              <input
                type="text"
                value={notation}
                onChange={(e) => setNotation(e.target.value)}
                className="w-full bg-[#0a0a0a] border border-zinc-800 rounded-md px-4 py-2.5 text-zinc-200 font-mono text-sm focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/50 transition-all"
                placeholder="e.g., 4 6 2"
              />
            </div>
            
            <button
              onClick={handleCompile}
              disabled={isCompiling || !notation}
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
                  <div className="font-mono text-lg text-zinc-200 tracking-wider">
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
