import { ShieldAlert, Cpu, Activity, GitMerge } from 'lucide-react';
import { KnotData } from '../types';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface Props {
  activeKnot: KnotData | null;
}

export default function QuantumErrorCorrection({ activeKnot }: Props) {
  const mockErrorData = [
    { cycle: 1, physical: 0.015, logical: 0.008 },
    { cycle: 2, physical: 0.016, logical: 0.007 },
    { cycle: 3, physical: 0.014, logical: 0.005 },
    { cycle: 4, physical: 0.015, logical: 0.004 },
    { cycle: 5, physical: 0.017, logical: 0.003 },
    { cycle: 6, physical: 0.015, logical: 0.002 },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div>
        <h2 className="text-2xl font-semibold text-zinc-100 tracking-tight">5. Quantum Error Correction</h2>
        <p className="text-zinc-400 mt-2">
          Encode logical qubits onto the heavy-hex lattice and configure real-time syndrome decoding to transition from NISQ to FTQC.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
            <div className="flex items-center gap-2 mb-6">
              <ShieldAlert className="w-5 h-5 text-indigo-500" />
              <h3 className="font-medium text-zinc-200">QEC Configuration</h3>
            </div>
            
            <div className="space-y-5">
              <div>
                <label className="block text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">
                  Logical Encoding
                </label>
                <select className="w-full bg-[#0a0a0a] border border-zinc-800 rounded-md px-4 py-2.5 text-zinc-200 font-mono text-sm focus:outline-none focus:border-indigo-500/50">
                  <option value="heavy-hex">Heavy-Hex Code (d=3)</option>
                  <option value="bacon-shor">Bacon-Shor Subsystem</option>
                  <option value="surface">Standard Surface Code</option>
                </select>
              </div>
              
              <div>
                <label className="block text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">
                  Classical Decoder
                </label>
                <select className="w-full bg-[#0a0a0a] border border-zinc-800 rounded-md px-4 py-2.5 text-zinc-200 font-mono text-sm focus:outline-none focus:border-indigo-500/50">
                  <option value="mwpm">Minimum Weight Perfect Matching (MWPM)</option>
                  <option value="union-find">Union-Find (Fast)</option>
                  <option value="tensor">Tensor Network Decoder</option>
                </select>
              </div>

              <div className="bg-[#0a0a0a] border border-zinc-800 rounded-md p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Syndrome Cycles</span>
                  <span className="text-xs font-mono text-zinc-300">6 per gate</span>
                </div>
                <div className="w-full bg-zinc-800 rounded-full h-1.5 mt-3">
                  <div className="bg-indigo-500 h-1.5 rounded-full" style={{ width: '60%' }}></div>
                </div>
              </div>

              <button className="w-full bg-indigo-500 hover:bg-indigo-600 text-indigo-950 font-medium py-2.5 rounded-md transition-colors flex items-center justify-center gap-2">
                <GitMerge className="w-4 h-4" />
                Map Logical Qubits
              </button>
            </div>
          </div>
        </div>

        <div className="lg:col-span-2 space-y-6">
          <div className="bg-[#111111] border border-zinc-800 rounded-xl p-6 flex flex-col min-h-[300px]">
            <div className="flex items-center justify-between mb-6">
              <h3 className="font-medium text-zinc-200">Heavy-Hex Lattice Mapping</h3>
              <div className="flex gap-2">
                <span className="px-2 py-1 bg-indigo-500/10 border border-indigo-500/20 rounded text-xs font-mono text-indigo-400">
                  1 Logical = 17 Physical
                </span>
              </div>
            </div>
            
            <div className="flex-1 border border-zinc-800 rounded-md bg-[#0a0a0a] p-6 relative overflow-hidden flex items-center justify-center">
              {/* Mock Heavy-Hex Visualization */}
              <svg viewBox="0 0 400 200" className="w-full h-full opacity-80">
                <g stroke="#27272a" strokeWidth="2">
                  {/* Hexagon 1 */}
                  <path d="M 100 50 L 150 50 L 175 93 L 150 136 L 100 136 L 75 93 Z" fill="none" />
                  {/* Hexagon 2 */}
                  <path d="M 200 50 L 250 50 L 275 93 L 250 136 L 200 136 L 175 93 Z" fill="none" />
                  {/* Hexagon 3 */}
                  <path d="M 150 136 L 200 136 L 225 179 L 175 179 L 125 179 L 125 136 Z" fill="none" />
                </g>
                
                {/* Data Qubits (Vertices) */}
                <circle cx="100" cy="50" r="6" fill="#10b981" />
                <circle cx="150" cy="50" r="6" fill="#10b981" />
                <circle cx="200" cy="50" r="6" fill="#10b981" />
                <circle cx="250" cy="50" r="6" fill="#10b981" />
                
                <circle cx="100" cy="136" r="6" fill="#10b981" />
                <circle cx="150" cy="136" r="6" fill="#10b981" />
                <circle cx="200" cy="136" r="6" fill="#10b981" />
                <circle cx="250" cy="136" r="6" fill="#10b981" />

                {/* Measure Qubits (Edges) */}
                <circle cx="125" cy="50" r="4" fill="#6366f1" />
                <circle cx="225" cy="50" r="4" fill="#6366f1" />
                <circle cx="125" cy="136" r="4" fill="#6366f1" />
                <circle cx="225" cy="136" r="4" fill="#6366f1" />
                
                <circle cx="87.5" cy="71.5" r="4" fill="#f59e0b" />
                <circle cx="162.5" cy="71.5" r="4" fill="#f59e0b" />
                <circle cx="262.5" cy="71.5" r="4" fill="#f59e0b" />
                
                <circle cx="87.5" cy="114.5" r="4" fill="#f59e0b" />
                <circle cx="162.5" cy="114.5" r="4" fill="#f59e0b" />
                <circle cx="262.5" cy="114.5" r="4" fill="#f59e0b" />
                
                {/* Legend */}
                <g transform="translate(10, 10)">
                  <circle cx="0" cy="0" r="4" fill="#10b981" />
                  <text x="10" y="4" fill="#71717a" fontSize="10" fontFamily="monospace">Data Qubit</text>
                  <circle cx="0" cy="15" r="4" fill="#6366f1" />
                  <text x="10" y="19" fill="#71717a" fontSize="10" fontFamily="monospace">Z-Measure</text>
                  <circle cx="0" cy="30" r="4" fill="#f59e0b" />
                  <text x="10" y="34" fill="#71717a" fontSize="10" fontFamily="monospace">X-Measure</text>
                </g>
              </svg>
            </div>
          </div>

          <div className="bg-[#111111] border border-zinc-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-indigo-500" />
                <h3 className="font-medium text-zinc-200">Error Rate Projection</h3>
              </div>
              <span className="text-xs font-mono text-zinc-500">Pseudo-threshold crossed</span>
            </div>
            
            <div className="h-[200px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={mockErrorData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                  <XAxis dataKey="cycle" stroke="#71717a" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke="#71717a" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip 
                    cursor={{ stroke: '#27272a', strokeWidth: 1 }}
                    contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '6px' }}
                    labelStyle={{ color: '#71717a', marginBottom: '4px' }}
                  />
                  <Line type="monotone" dataKey="physical" name="Physical Error" stroke="#f59e0b" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="logical" name="Logical Error" stroke="#6366f1" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
