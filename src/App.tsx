import React, { useState } from 'react';
import { Activity, Cpu, Database, GitMerge, Layers, Play, Settings, Zap, ShieldAlert } from 'lucide-react';
import { PipelineStep, KnotData, ExecutionSettings, ExperimentResult, KnotCircuitGenerationResponse, KnotIngestionResponse } from './types';
import { cn } from './lib/utils';
import Dashboard from './components/Dashboard';
import KnotIngestion from './components/KnotIngestion';
import TopologicalVerification from './components/TopologicalVerification';
import CircuitGeneration from './components/CircuitGeneration';
import PulseControl from './components/PulseControl';
import QuantumErrorCorrection from './components/QuantumErrorCorrection';
import ExecutionResults from './components/ExecutionResults';

export default function App() {
  const [activeStep, setActiveStep] = useState<PipelineStep>('dashboard');
  const [targetBackend, setTargetBackend] = useState<string>('ibm_kyiv');
  const [executionSettings, setExecutionSettings] = useState<ExecutionSettings>({
    shots: 8192,
    optimizationLevel: 3,
    closureMethod: 'trace',
  });
  const [activeKnot, setActiveKnot] = useState<KnotData | null>({
    id: 'k-1',
    name: 'Trefoil Knot (3_1)',
    dowkerNotation: '4 6 2',
    braidWord: 's1 s1 s1',
    rootOfUnity: 5,
    status: 'pending',
  });

  const handleKnotCompiled = (compiledKnot: KnotIngestionResponse) => {
    setActiveKnot((prev) => {
      if (!prev) {
        return prev;
      }

      return {
        ...prev,
        name: compiledKnot.knot_name,
        dowkerNotation: compiledKnot.dowker_notation_normalized,
        braidWord: compiledKnot.braid_word,
        rootOfUnity: compiledKnot.root_of_unity,
        status: 'pending',
        jonesPolynomial: undefined,
        circuitSummary: undefined,
      };
    });
  };

  const handleVerificationComplete = () => {
    setActiveKnot((prev) => {
      if (!prev) {
        return prev;
      }

      return {
        ...prev,
        status:
          prev.status === 'compiled' || prev.status === 'executed'
            ? prev.status
            : 'verified',
      };
    });
  };

  const handleCircuitGenerated = (generatedCircuit: KnotCircuitGenerationResponse) => {
    setActiveKnot((prev) => {
      if (!prev) {
        return prev;
      }

      return {
        ...prev,
        status: 'compiled',
        jonesPolynomial: undefined,
        circuitSummary: generatedCircuit.circuit_summary,
      };
    });
  };

  const handleExecutionComplete = (experimentResult: ExperimentResult) => {
    setActiveKnot((prev) => {
      if (!prev) {
        return prev;
      }

      return {
        ...prev,
        status: 'executed',
        jonesPolynomial: experimentResult.jones_polynomial,
      };
    });
  };

  const steps: { id: PipelineStep; label: string; icon: React.ElementType }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: Activity },
    { id: 'ingestion', label: '1. Knot Ingestion', icon: Database },
    { id: 'verification', label: '2. Topological Verification', icon: Layers },
    { id: 'circuit', label: '3. Circuit Generation', icon: GitMerge },
    { id: 'pulse', label: '4. Pulse Control', icon: Zap },
    { id: 'qec', label: '5. Error Correction', icon: ShieldAlert },
    { id: 'execution', label: '6. Execution & Results', icon: Play },
  ];

  return (
    <div className="flex h-screen w-full bg-[#0a0a0a] text-zinc-300 font-sans overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 border-r border-zinc-800 bg-[#111111] flex flex-col">
        <div className="p-6 border-b border-zinc-800">
          <div className="flex items-center gap-3 text-zinc-100">
            <Cpu className="w-6 h-6 text-emerald-500" />
            <span className="font-semibold tracking-wide text-sm uppercase">Q-Knot Pipeline</span>
          </div>
          <p className="text-xs text-zinc-500 mt-2 font-mono">IBM FTQC Hardware</p>
        </div>
        
        <nav className="flex-1 py-4 px-3 space-y-1">
          {steps.map((step) => {
            const Icon = step.icon;
            const isActive = activeStep === step.id;
            return (
              <button
                key={step.id}
                onClick={() => setActiveStep(step.id)}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors",
                  isActive 
                    ? "bg-emerald-500/10 text-emerald-400" 
                    : "text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200"
                )}
              >
                <Icon className={cn("w-4 h-4", isActive ? "text-emerald-400" : "text-zinc-500")} />
                {step.label}
              </button>
            );
          })}
        </nav>

        <div className="p-4 border-t border-zinc-800">
          <div className="bg-zinc-900 rounded-md p-3 border border-zinc-800">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Target Hardware</span>
              <Settings className="w-3 h-3 text-zinc-500" />
            </div>
            <select 
              value={targetBackend}
              onChange={(e) => setTargetBackend(e.target.value)}
              className="w-full bg-[#0a0a0a] border border-zinc-800 rounded text-sm text-zinc-200 font-mono p-1.5 focus:outline-none focus:border-emerald-500/50"
            >
              <option value="ibm_kyiv">ibm_kyiv (127Q)</option>
              <option value="ibm_brisbane">ibm_brisbane (127Q)</option>
              <option value="ibm_osaka">ibm_osaka (127Q)</option>
              <option value="ibm_sherbrooke">ibm_sherbrooke (127Q)</option>
              <option value="least_busy">Auto (Least Busy)</option>
            </select>
            <div className="text-xs text-zinc-500 mt-2">Heavy-Hex Topology</div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-full overflow-hidden bg-[#0a0a0a]">
        <header className="h-14 border-b border-zinc-800 flex items-center px-6 justify-between shrink-0">
          <h1 className="text-sm font-medium text-zinc-200">
            {steps.find(s => s.id === activeStep)?.label}
          </h1>
          {activeKnot && (
            <div className="flex items-center gap-2 text-xs font-mono">
              <span className="text-zinc-500">Active Target:</span>
              <span className="text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded">
                {activeKnot.name}
              </span>
            </div>
          )}
        </header>
        
        <div className="flex-1 overflow-auto p-6">
          <div className="max-w-5xl mx-auto h-full">
            {activeStep === 'dashboard' && <Dashboard targetBackend={targetBackend} activeKnot={activeKnot} />}
            {activeStep === 'ingestion' && (
              <KnotIngestion activeKnot={activeKnot} onCompiled={handleKnotCompiled} />
            )}
            {activeStep === 'verification' && (
              <TopologicalVerification activeKnot={activeKnot} onVerified={handleVerificationComplete} />
            )}
            {activeStep === 'circuit' && (
              <CircuitGeneration
                activeKnot={activeKnot}
                targetBackend={targetBackend}
                executionSettings={executionSettings}
                setExecutionSettings={setExecutionSettings}
                onGenerateCircuit={handleCircuitGenerated}
              />
            )}
            {activeStep === 'pulse' && <PulseControl activeKnot={activeKnot} />}
            {activeStep === 'qec' && <QuantumErrorCorrection activeKnot={activeKnot} />}
            {activeStep === 'execution' && (
              <ExecutionResults
                activeKnot={activeKnot}
                targetBackend={targetBackend}
                executionSettings={executionSettings}
                setExecutionSettings={setExecutionSettings}
                onExecutionComplete={handleExecutionComplete}
              />
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
