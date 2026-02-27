import { Activity, CheckCircle2, CircleDashed, Clock } from 'lucide-react';
import { KnotData } from '../types';

interface Props {
  targetBackend: string;
  activeKnot: KnotData | null;
}

type TaskStatus = 'completed' | 'in-progress' | 'pending';

function isAtLeastStatus(
  knot: KnotData | null,
  minimum: KnotData['status'],
) {
  if (!knot) {
    return false;
  }

  const order: Record<KnotData['status'], number> = {
    pending: 0,
    verified: 1,
    compiled: 2,
    executed: 3,
  };

  return order[knot.status] >= order[minimum];
}

export default function Dashboard({ targetBackend, activeKnot }: Props) {
  const hasBraidWord = Boolean(activeKnot?.braidWord?.trim());
  const verificationComplete = isAtLeastStatus(activeKnot, 'verified');
  const circuitComplete = isAtLeastStatus(activeKnot, 'compiled');
  const executionComplete = isAtLeastStatus(activeKnot, 'executed');

  const getStatus = (
    isComplete: boolean,
    canStart: boolean,
  ): TaskStatus => {
    if (isComplete) {
      return 'completed';
    }
    if (canStart) {
      return 'in-progress';
    }
    return 'pending';
  };

  const tasks = [
    { id: 1, title: 'Knot Ingestion', desc: 'Compile Dowker notation to Braid Word', status: getStatus(hasBraidWord, false) },
    { id: 2, title: 'Topological Verification', desc: 'Simulate anyonic braiding in QTop', status: getStatus(verificationComplete, hasBraidWord) },
    { id: 3, title: 'Circuit Generation', desc: 'Map strands to IBM qubits & apply Yang-Baxter unitaries', status: getStatus(circuitComplete, verificationComplete) },
    { id: 4, title: 'Pulse-Level Compilation', desc: 'Replace CX/Rzz with custom Cross-Resonance pulses', status: 'pending' as TaskStatus },
    { id: 5, title: 'Quantum Error Correction', desc: 'Encode logical qubits on heavy-hex lattice', status: 'pending' as TaskStatus },
    { id: 6, title: 'Execution & Mitigation', desc: `Run on ${targetBackend} & apply dynamical decoupling`, status: getStatus(executionComplete, circuitComplete) },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div>
        <h2 className="text-2xl font-semibold text-zinc-100 tracking-tight">Project Overview</h2>
        <p className="text-zinc-400 mt-2">
          Mapping knot invariants (Jones polynomial) onto FTQC IBM hardware using QTop, Qiskit, and Qiskit Pulse.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
          <div className="flex items-center gap-3 text-emerald-400 mb-2">
            <Activity className="w-5 h-5" />
            <h3 className="font-medium">System Status</h3>
          </div>
          <p className="text-3xl font-light text-zinc-100 mt-4">Online</p>
          <p className="text-xs text-zinc-500 mt-1 uppercase tracking-wider">IBM Quantum API Connected</p>
        </div>
        
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
          <h3 className="font-medium text-zinc-400 mb-2">Target Root of Unity</h3>
          <p className="text-3xl font-light text-zinc-100 mt-4">5th</p>
          <p className="text-xs text-zinc-500 mt-1 uppercase tracking-wider">BQP-Complete Evaluation</p>
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
          <h3 className="font-medium text-zinc-400 mb-2">Active Backend</h3>
          <p className="text-3xl font-light text-zinc-100 mt-4">{targetBackend}</p>
          <p className="text-xs text-zinc-500 mt-1 uppercase tracking-wider">Heavy-Hex Topology</p>
        </div>
      </div>

      <div className="bg-[#111111] border border-zinc-800 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-zinc-800 bg-zinc-900/50">
          <h3 className="font-medium text-zinc-200">Pipeline Status</h3>
        </div>
        <div className="divide-y divide-zinc-800/50">
          {tasks.map((task) => (
            <div key={task.id} className="px-6 py-4 flex items-center gap-4 hover:bg-zinc-800/20 transition-colors">
              {task.status === 'completed' && <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />}
              {task.status === 'in-progress' && <Clock className="w-5 h-5 text-amber-500 shrink-0" />}
              {task.status === 'pending' && <CircleDashed className="w-5 h-5 text-zinc-600 shrink-0" />}
              
              <div>
                <p className="text-sm font-medium text-zinc-200">{task.title}</p>
                <p className="text-xs text-zinc-500 mt-0.5">{task.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
