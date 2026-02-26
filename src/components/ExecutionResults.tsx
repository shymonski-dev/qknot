import { useState } from 'react';
import { Play, BarChart3, Key, AlertCircle } from 'lucide-react';
import { KnotData } from '../types';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface Props {
  activeKnot: KnotData | null;
  targetBackend: string;
}

export default function ExecutionResults({ activeKnot, targetBackend }: Props) {
  const [ibmToken, setIbmToken] = useState('');
  const [backendUrl, setBackendUrl] = useState('http://localhost:8000');
  const [shots, setShots] = useState(8192);
  const [isExecuting, setIsExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  const mockData = [
    { name: '00', probability: 0.15 },
    { name: '01', probability: 0.35 },
    { name: '10', probability: 0.42 },
    { name: '11', probability: 0.08 },
  ];

  const displayData = result?.counts || mockData;
  const displayJones = result?.jones_polynomial || "V(t) = -t^-4 + t^-3 + t^-1";
  const displayJobId = result?.job_id || "cj8x9...";

  const handleExecute = async () => {
    if (!ibmToken) {
      setError("IBM Quantum API Token is required to run on actual hardware.");
      return;
    }
    
    setIsExecuting(true);
    setError(null);
    
    try {
      const response = await fetch(`${backendUrl}/api/run-experiment`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ibm_token: ibmToken,
          backend_name: targetBackend,
          braid_word: activeKnot?.braidWord || 's1',
          shots: shots,
          optimization_level: 3
        }),
      });
      
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Failed to execute experiment');
      }
      
      const data = await response.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || "Failed to connect to the Python backend. Ensure it is running locally.");
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div>
        <h2 className="text-2xl font-semibold text-zinc-100 tracking-tight">6. Execution & Mitigation</h2>
        <p className="text-zinc-400 mt-2">
          Execute pulse schedules on IBM hardware via the Python Qiskit backend.
        </p>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-medium text-red-400">Execution Error</h3>
            <p className="text-xs text-red-400/80 mt-1">{error}</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
            <div className="flex items-center gap-2 mb-6">
              <Key className="w-5 h-5 text-emerald-500" />
              <h3 className="font-medium text-zinc-200">Hardware Connection</h3>
            </div>
            
            <div className="space-y-5">
              <div>
                <label className="block text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">
                  IBM Quantum API Token
                </label>
                <input
                  type="password"
                  value={ibmToken}
                  onChange={(e) => setIbmToken(e.target.value)}
                  placeholder="Paste your IBM token here..."
                  className="w-full bg-[#0a0a0a] border border-zinc-800 rounded-md px-4 py-2.5 text-zinc-200 font-mono text-sm focus:outline-none focus:border-emerald-500/50"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">
                  Python Backend URL
                </label>
                <input
                  type="text"
                  value={backendUrl}
                  onChange={(e) => setBackendUrl(e.target.value)}
                  className="w-full bg-[#0a0a0a] border border-zinc-800 rounded-md px-4 py-2.5 text-zinc-200 font-mono text-sm focus:outline-none focus:border-emerald-500/50"
                />
                <p className="text-[10px] text-zinc-500 mt-2 leading-tight">
                  The Python backend must be running locally to interface with the Qiskit Runtime API.
                </p>
              </div>
              
              <div>
                <label className="block text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">
                  Shots
                </label>
                <input
                  type="number"
                  value={shots}
                  onChange={(e) => setShots(parseInt(e.target.value))}
                  className="w-full bg-[#0a0a0a] border border-zinc-800 rounded-md px-4 py-2.5 text-zinc-200 font-mono text-sm focus:outline-none focus:border-emerald-500/50"
                />
              </div>

              <button 
                onClick={handleExecute}
                disabled={isExecuting}
                className="w-full bg-emerald-500 hover:bg-emerald-600 text-emerald-950 font-medium py-2.5 rounded-md transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isExecuting ? (
                  <span className="animate-pulse">Executing on IBM Quantum...</span>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-current" />
                    Execute Job on {targetBackend === 'least_busy' ? 'Auto' : targetBackend}
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        <div className="lg:col-span-2 space-y-6">
          <div className="bg-[#111111] border border-zinc-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-blue-500" />
                <h3 className="font-medium text-zinc-200">Probability Distribution</h3>
              </div>
              <span className="px-2 py-1 bg-zinc-800 rounded text-xs font-mono text-zinc-400">
                Job ID: {displayJobId}
              </span>
            </div>
            
            <div className="h-[250px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={displayData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                  <XAxis dataKey="name" stroke="#71717a" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke="#71717a" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip 
                    cursor={{ fill: '#27272a', opacity: 0.4 }}
                    contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '6px' }}
                    itemStyle={{ color: '#10b981' }}
                  />
                  <Bar dataKey="probability" fill="#10b981" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
            <h3 className="font-medium text-zinc-200 mb-4">Jones Polynomial Result</h3>
            <div className="bg-[#0a0a0a] border border-zinc-800 rounded-md p-6 flex flex-col items-center justify-center gap-4">
              <div className="font-serif italic text-2xl text-emerald-400 tracking-wider">
                {displayJones}
              </div>
              <p className="text-xs text-zinc-500 font-mono">
                Evaluated at root of unity: e^(2Ï€i/5)
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
