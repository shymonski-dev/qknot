import { useEffect, useRef, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { Play, BarChart3, AlertCircle, CheckCircle2, Info } from 'lucide-react';
import {
  BackendCatalogResponse,
  ExecutionSettings,
  ExperimentJobStatus,
  ExperimentResult,
  KnotData,
} from '../types';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface Props {
  activeKnot: KnotData | null;
  targetBackend: string;
  executionSettings: ExecutionSettings;
  setExecutionSettings: Dispatch<SetStateAction<ExecutionSettings>>;
  onExecutionComplete: (result: ExperimentResult) => void;
  pollIntervalMs?: number;
  maxPollAttempts?: number;
}

type RuntimeChannelSelection = 'auto' | 'ibm_quantum_platform' | 'ibm_cloud' | 'ibm_quantum';
type PendingJobSnapshot = {
  job_id: string;
  backend_name: string;
  runtime_channel: RuntimeChannelSelection;
  runtime_instance: string | null;
};

const MAX_SHOTS = 100_000;
const POLL_INTERVAL_MS = 1000;
const MAX_POLL_ATTEMPTS = 180;
const PENDING_JOB_STORAGE_KEY = 'qknot.pending_job';
const POLL_CANCELLED_ERROR = 'QKNOT_POLL_CANCELLED';
const IN_PROGRESS_JOB_STATUSES = new Set(['INITIALIZING', 'QUEUED', 'RUNNING', 'VALIDATING', 'SUBMITTED']);
const FAILED_JOB_STATUSES = new Set(['FAILED', 'ERROR', 'CANCELLED', 'CANCELED']);
const BRAID_TOKEN_REGEX = /^s([1-9]\d*)(\^-1)?$/;

function isCompiledOrLater(status: KnotData['status'] | undefined) {
  return status === 'compiled' || status === 'executed';
}

function isExperimentResultPayload(payload: ExperimentJobStatus | ExperimentResult): payload is ExperimentResult {
  return Array.isArray((payload as ExperimentResult).counts);
}

async function readErrorDetail(response: Response, fallbackMessage: string) {
  let detail = fallbackMessage;
  try {
    const errData = await response.json();
    if (typeof errData?.detail === 'string' && errData.detail.trim()) {
      detail = errData.detail;
    }
  } catch {
    // Keep the fallback message when the error body is not JSON.
  }
  return detail;
}

function sleep(ms: number) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function validateBraidWordForExecution(braidWord: string | undefined): string | null {
  const normalizedBraidWord = braidWord?.trim() ?? '';
  if (!normalizedBraidWord) {
    return 'Braid word is required before execution.';
  }

  const tokens = normalizedBraidWord.split(/\s+/);
  const generators: number[] = [];
  for (const token of tokens) {
    const match = BRAID_TOKEN_REGEX.exec(token);
    if (!match) {
      return `Unsupported braid token '${token}'. Use tokens like s1 or s3^-1.`;
    }
    generators.push(Number(match[1]));
  }

  if (tokens.length < 3) {
    return 'Braid word must contain at least three generators before execution.';
  }

  const uniqueGenerators = new Set(generators);
  if (uniqueGenerators.size < 2) {
    return 'Braid word must include at least two distinct generators before execution.';
  }

  const maxGenerator = Math.max(...generators);
  const missingGenerators: string[] = [];
  for (let generator = 1; generator <= maxGenerator; generator += 1) {
    if (!uniqueGenerators.has(generator)) {
      missingGenerators.push(`s${generator}`);
    }
  }

  if (missingGenerators.length > 0) {
    return (
      `Braid word must use contiguous generators from s1 through s${maxGenerator}. `
      + `Missing: ${missingGenerators.join(', ')}.`
    );
  }

  return null;
}

function readRuntimePayload(
  runtimeChannel: RuntimeChannelSelection,
  runtimeInstance: string,
): { runtime_channel?: RuntimeChannelSelection; runtime_instance?: string } {
  const runtimePayload: { runtime_channel?: RuntimeChannelSelection; runtime_instance?: string } = {};
  if (runtimeChannel !== 'auto') {
    runtimePayload.runtime_channel = runtimeChannel;
  }
  const normalizedRuntimeInstance = runtimeInstance.trim();
  if (normalizedRuntimeInstance) {
    runtimePayload.runtime_instance = normalizedRuntimeInstance;
  }
  return runtimePayload;
}

function isPendingJobSnapshot(value: unknown): value is PendingJobSnapshot {
  if (!value || typeof value !== 'object') {
    return false;
  }
  const candidate = value as Partial<PendingJobSnapshot> & { backend_url?: unknown };
  const runtimeChannel = candidate.runtime_channel;
  const runtimeChannelIsValid =
    runtimeChannel === 'auto'
    || runtimeChannel === 'ibm_quantum_platform'
    || runtimeChannel === 'ibm_cloud'
    || runtimeChannel === 'ibm_quantum';
  return (
    typeof candidate.job_id === 'string'
    && typeof candidate.backend_name === 'string'
    && runtimeChannelIsValid
    && (candidate.backend_url === undefined || typeof candidate.backend_url === 'string')
    && (candidate.runtime_instance === null || typeof candidate.runtime_instance === 'string')
  );
}

function loadPendingJobSnapshot(): PendingJobSnapshot | null {
  if (typeof window === 'undefined') {
    return null;
  }

  try {
    const stored = window.localStorage.getItem(PENDING_JOB_STORAGE_KEY);
    if (!stored) {
      return null;
    }

    const parsed = JSON.parse(stored);
    if (!isPendingJobSnapshot(parsed)) {
      window.localStorage.removeItem(PENDING_JOB_STORAGE_KEY);
      return null;
    }

    return parsed;
  } catch {
    window.localStorage.removeItem(PENDING_JOB_STORAGE_KEY);
    return null;
  }
}

function savePendingJobSnapshot(snapshot: PendingJobSnapshot) {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.setItem(PENDING_JOB_STORAGE_KEY, JSON.stringify(snapshot));
}

function clearPendingJobSnapshot() {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.removeItem(PENDING_JOB_STORAGE_KEY);
}

export default function ExecutionResults({
  activeKnot,
  targetBackend,
  executionSettings,
  setExecutionSettings,
  onExecutionComplete,
  pollIntervalMs = POLL_INTERVAL_MS,
  maxPollAttempts = MAX_POLL_ATTEMPTS,
}: Props) {
  const [pendingResumeJob, setPendingResumeJob] = useState<PendingJobSnapshot | null>(() => loadPendingJobSnapshot());
  const [runtimeChannel, setRuntimeChannel] = useState<RuntimeChannelSelection>(
    () => pendingResumeJob?.runtime_channel ?? 'auto',
  );
  const [runtimeInstance, setRuntimeInstance] = useState(() => pendingResumeJob?.runtime_instance ?? '');
  const [shotsInput, setShotsInput] = useState(String(executionSettings.shots));
  const [isExecuting, setIsExecuting] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [isLoadingBackends, setIsLoadingBackends] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusDetail, setStatusDetail] = useState<string | null>(null);
  const [backendCatalogError, setBackendCatalogError] = useState<string | null>(null);
  const [shotInputError, setShotInputError] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<ExperimentJobStatus | null>(
    () => (
      pendingResumeJob
        ? {
            job_id: pendingResumeJob.job_id,
            backend: pendingResumeJob.backend_name,
            status: 'SUBMITTED',
          }
        : null
    ),
  );
  const [result, setResult] = useState<ExperimentResult | null>(null);
  const [backendCatalog, setBackendCatalog] = useState<BackendCatalogResponse | null>(null);
  const cancelRequestedRef = useRef(false);

  useEffect(() => {
    setShotsInput(String(executionSettings.shots));
  }, [executionSettings.shots]);

  const canExecute = isCompiledOrLater(activeKnot?.status);
  const visibleError = shotInputError ?? error;
  const hasResult = result !== null;
  const hasInFlightJob = isExecuting && jobStatus !== null;
  const hasPendingResume = pendingResumeJob !== null;
  const showingPreviousResult = hasResult && visibleError !== null;

  const clearPendingJob = () => {
    clearPendingJobSnapshot();
    setPendingResumeJob(null);
  };

  const persistPendingJob = (snapshot: PendingJobSnapshot) => {
    savePendingJobSnapshot(snapshot);
    setPendingResumeJob(snapshot);
  };

  const pollRuntimeJob = async ({
    jobId,
    backendNameHint,
    runtimeChannelForJob,
    runtimeInstanceForJob,
  }: {
    jobId: string;
    backendNameHint: string;
    runtimeChannelForJob: RuntimeChannelSelection;
    runtimeInstanceForJob: string;
  }) => {
    for (let attempt = 0; attempt < maxPollAttempts; attempt += 1) {
      if (cancelRequestedRef.current) {
        throw new Error(POLL_CANCELLED_ERROR);
      }

      const pollResponse = await fetch('/api/jobs/poll', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          job_id: jobId,
          ...readRuntimePayload(runtimeChannelForJob, runtimeInstanceForJob),
        }),
      });

      if (!pollResponse.ok) {
        const detail = await readErrorDetail(pollResponse, 'Failed to poll experiment job.');
        if (pollResponse.status === 422) {
          throw new Error(`Request validation failed: ${detail}`);
        }
        throw new Error(`Server error (${pollResponse.status}): ${detail}`);
      }

      const pollPayload = (await pollResponse.json()) as ExperimentJobStatus | ExperimentResult;

      if (isExperimentResultPayload(pollPayload) && pollPayload.status === 'COMPLETED') {
        setJobStatus({
          job_id: pollPayload.job_id,
          backend: pollPayload.backend,
          runtime_channel_used: pollPayload.runtime_channel_used,
          runtime_instance_used: pollPayload.runtime_instance_used,
          status: pollPayload.status,
        });
        setResult(pollPayload);
        setStatusDetail(null);
        clearPendingJob();
        onExecutionComplete(pollPayload);
        return;
      }

      setJobStatus(pollPayload);
      const pollDetail = 'detail' in pollPayload ? pollPayload.detail : undefined;

      if (FAILED_JOB_STATUSES.has(pollPayload.status)) {
        clearPendingJob();
        throw new Error(pollDetail || `Runtime job failed with status ${pollPayload.status}.`);
      }

      if (!IN_PROGRESS_JOB_STATUSES.has(pollPayload.status)) {
        clearPendingJob();
        throw new Error(pollDetail || `Unexpected runtime job status ${pollPayload.status}.`);
      }

      await sleep(pollIntervalMs);
    }

    const timeoutSnapshot: PendingJobSnapshot = {
      job_id: jobId,
      backend_name: backendNameHint || targetBackend,
      runtime_channel: runtimeChannelForJob,
      runtime_instance: runtimeInstanceForJob.trim() ? runtimeInstanceForJob.trim() : null,
    };
    persistPendingJob(timeoutSnapshot);
    setStatusDetail(`Saved pending job ${jobId}. You can resume polling later.`);
    throw new Error('Timed out waiting for the IBM runtime job to complete.');
  };

  const handleShotsChange = (value: string) => {
    setShotsInput(value);

    if (!value.trim()) {
      setShotInputError(`Shots must be a whole number between 1 and ${MAX_SHOTS}.`);
      return;
    }

    const parsed = Number(value);
    if (!Number.isInteger(parsed) || parsed < 1 || parsed > MAX_SHOTS) {
      setShotInputError(`Shots must be a whole number between 1 and ${MAX_SHOTS}.`);
      return;
    }

    setShotInputError(null);
    setExecutionSettings((prev) => ({
      ...prev,
      shots: parsed,
    }));
  };

  const handleExecute = async () => {
    cancelRequestedRef.current = false;

    if (!canExecute) {
      setError('Generate the circuit after verification before executing the job.');
      return;
    }

    if (shotInputError || !shotsInput.trim()) {
      setError(`Shots must be a whole number between 1 and ${MAX_SHOTS}.`);
      return;
    }

    const braidValidationError = validateBraidWordForExecution(activeKnot?.braidWord);
    if (braidValidationError) {
      setError(braidValidationError);
      return;
    }
    
    setIsExecuting(true);
    setIsCancelling(false);
    setError(null);
    setStatusDetail(null);
    
    try {
      const runtimePayload = readRuntimePayload(runtimeChannel, runtimeInstance);
      const submitResponse = await fetch('/api/jobs/submit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          backend_name: targetBackend,
          braid_word: activeKnot?.braidWord?.trim(),
          shots: executionSettings.shots,
          optimization_level: executionSettings.optimizationLevel,
          closure_method: executionSettings.closureMethod,
          ...runtimePayload,
        }),
      });
      
      if (!submitResponse.ok) {
        const detail = await readErrorDetail(submitResponse, 'Failed to submit experiment job.');
        if (submitResponse.status === 422) {
          throw new Error(`Request validation failed: ${detail}`);
        }
        throw new Error(`Server error (${submitResponse.status}): ${detail}`);
      }

      const submittedJob = (await submitResponse.json()) as ExperimentJobStatus;

      const generatedSignature = activeKnot?.circuitSummary?.signature;
      const submittedSignature = submittedJob.circuit_summary?.signature;
      if (generatedSignature && submittedSignature && generatedSignature !== submittedSignature) {
        throw new Error(
          `Generated circuit signature ${generatedSignature} does not match submitted signature ${submittedSignature}.`,
        );
      }

      setJobStatus(submittedJob);

      if (!submittedJob.job_id) {
        throw new Error('The backend did not return a runtime job identifier.');
      }
      const pendingSnapshot: PendingJobSnapshot = {
        job_id: submittedJob.job_id,
        backend_name: submittedJob.backend || targetBackend,
        runtime_channel: runtimeChannel,
        runtime_instance: runtimeInstance.trim() ? runtimeInstance.trim() : null,
      };
      persistPendingJob(pendingSnapshot);

      await pollRuntimeJob({
        jobId: submittedJob.job_id,
        backendNameHint: submittedJob.backend || targetBackend,
        runtimeChannelForJob: runtimeChannel,
        runtimeInstanceForJob: runtimeInstance,
      });
    } catch (err: unknown) {
      if (err instanceof Error) {
        if (err.message === POLL_CANCELLED_ERROR) {
          return;
        }
        if (err.name === 'TypeError') {
          setError('Could not reach the backend API.');
        } else {
          setError(err.message || 'Failed to connect to the backend API. Ensure it is running.');
        }
      } else {
        setError('Failed to connect to the backend API. Ensure it is running.');
      }
    } finally {
      setIsExecuting(false);
      setIsCancelling(false);
    }
  };

  const handleResumePendingJob = async () => {
    cancelRequestedRef.current = false;

    if (!pendingResumeJob) {
      return;
    }
    setRuntimeChannel(pendingResumeJob.runtime_channel);
    setRuntimeInstance(pendingResumeJob.runtime_instance ?? '');
    setJobStatus({
      job_id: pendingResumeJob.job_id,
      backend: pendingResumeJob.backend_name,
      status: 'SUBMITTED',
    });
    setError(null);
    setStatusDetail(null);
    setIsExecuting(true);

    try {
      await pollRuntimeJob({
        jobId: pendingResumeJob.job_id,
        backendNameHint: pendingResumeJob.backend_name,
        runtimeChannelForJob: pendingResumeJob.runtime_channel,
        runtimeInstanceForJob: pendingResumeJob.runtime_instance ?? '',
      });
    } catch (err: unknown) {
      if (err instanceof Error) {
        if (err.message === POLL_CANCELLED_ERROR) {
          return;
        }
        if (err.name === 'TypeError') {
          setError('Could not reach the backend API.');
        } else {
          setError(err.message || 'Failed to resume polling.');
        }
      } else {
        setError('Failed to resume polling.');
      }
    } finally {
      setIsExecuting(false);
    }
  };

  const handleCancelJob = async () => {
    if (!jobStatus?.job_id) {
      return;
    }

    cancelRequestedRef.current = true;
    setIsCancelling(true);
    setError(null);
    setStatusDetail(null);

    try {
      const response = await fetch('/api/jobs/cancel', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          job_id: jobStatus.job_id,
          ...readRuntimePayload(runtimeChannel, runtimeInstance),
        }),
      });

      if (!response.ok) {
        const detail = await readErrorDetail(response, 'Failed to cancel experiment job.');
        if (response.status === 422) {
          throw new Error(`Request validation failed: ${detail}`);
        }
        throw new Error(`Server error (${response.status}): ${detail}`);
      }

      const payload = (await response.json()) as ExperimentJobStatus;
      setJobStatus(payload);
      clearPendingJob();
      setStatusDetail(payload.detail || 'Cancellation requested.');
    } catch (err: unknown) {
      if (err instanceof Error) {
        if (err.name === 'TypeError') {
          setError('Could not reach the backend API.');
        } else {
          setError(err.message || 'Failed to cancel runtime job.');
        }
      } else {
        setError('Failed to cancel runtime job.');
      }
    } finally {
      setIsExecuting(false);
      setIsCancelling(false);
    }
  };

  const handleLoadBackends = async () => {
    setIsLoadingBackends(true);
    setBackendCatalogError(null);

    try {
      const response = await fetch('/api/backends', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...readRuntimePayload(runtimeChannel, runtimeInstance),
        }),
      });

      if (!response.ok) {
        const detail = await readErrorDetail(response, 'Failed to list accessible hardware backends.');
        if (response.status === 422) {
          throw new Error(`Request validation failed: ${detail}`);
        }
        throw new Error(`Server error (${response.status}): ${detail}`);
      }

      const payload = (await response.json()) as BackendCatalogResponse;
      setBackendCatalog(payload);
    } catch (err: unknown) {
      if (err instanceof Error) {
        if (err.name === 'TypeError') {
          setBackendCatalogError('Could not reach the backend API.');
        } else {
          setBackendCatalogError(err.message || 'Failed to list accessible hardware backends.');
        }
      } else {
        setBackendCatalogError('Failed to list accessible hardware backends.');
      }
    } finally {
      setIsLoadingBackends(false);
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

      {hasPendingResume && !isExecuting && (
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 space-y-3">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <h3 className="text-sm font-medium text-amber-400">Pending Runtime Job Found</h3>
              <p className="text-xs text-amber-400/80 mt-1">
                Job {pendingResumeJob?.job_id} is saved from a previous session.
                {' '}Resume polling to fetch final results.
              </p>
            </div>
          </div>
          <button
            data-testid="resume-job-button"
            onClick={handleResumePendingJob}
            className="w-full bg-amber-400/80 hover:bg-amber-400 text-amber-950 font-medium py-2.5 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Resume Pending Job
          </button>
        </div>
      )}

      {visibleError && (
        <div data-testid="execution-error" className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-medium text-red-400">Execution Error</h3>
            <p className="text-xs text-red-400/80 mt-1">{visibleError}</p>
          </div>
        </div>
      )}

      {statusDetail && !visibleError && (
        <div className="bg-zinc-800/60 border border-zinc-700 rounded-xl p-4 flex items-start gap-3">
          <Info className="w-5 h-5 text-zinc-300 shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-medium text-zinc-200">Execution Status</h3>
            <p className="text-xs text-zinc-400 mt-1">{statusDetail}</p>
          </div>
        </div>
      )}

      {!visibleError && hasInFlightJob && (
        <div data-testid="job-in-flight" className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 flex items-start gap-3">
          <Info className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-medium text-amber-400">Execution In Progress</h3>
            <p data-testid="job-status-text" className="text-xs text-amber-400/80 mt-1">
              Job {jobStatus.job_id} is currently {jobStatus.status}
              {jobStatus.backend ? ` on ${jobStatus.backend}` : ''}.
            </p>
          </div>
        </div>
      )}

      {showingPreviousResult && (
        <div className="bg-zinc-800/50 border border-zinc-700 rounded-xl p-4 flex items-start gap-3">
          <Info className="w-5 h-5 text-zinc-300 shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-medium text-zinc-200">Showing Previous Successful Result</h3>
            <p className="text-xs text-zinc-400 mt-1">
              The latest run failed, so this view still shows the most recent completed hardware result.
            </p>
          </div>
        </div>
      )}

      {!visibleError && !hasResult && !isExecuting && (
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-4 flex items-start gap-3">
          <Info className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-medium text-blue-400">No Result Yet</h3>
            <p className="text-xs text-blue-400/80 mt-1">
              Complete verification and circuit generation, then run a job to populate real measurement output.
            </p>
          </div>
        </div>
      )}

      {hasResult && !visibleError && (
        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4 flex items-start gap-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-medium text-emerald-400">Execution Complete</h3>
            <p className="text-xs text-emerald-400/80 mt-1">
              Result received from {result.backend}
              {result.runtime_channel_used ? ` via ${result.runtime_channel_used}` : ''}
              {' '}with expectation value {result.expectation_value.toFixed(4)}.
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
            <div className="flex items-center gap-2 mb-6">
              <Info className="w-5 h-5 text-emerald-500" />
              <h3 className="font-medium text-zinc-200">Hardware Runtime</h3>
            </div>
            
            <div className="space-y-5">
              <div>
                <label className="block text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">
                  Runtime Channel
                </label>
                <select
                  value={runtimeChannel}
                  onChange={(e) => setRuntimeChannel(e.target.value as RuntimeChannelSelection)}
                  className="w-full bg-[#0a0a0a] border border-zinc-800 rounded-md px-4 py-2.5 text-zinc-200 font-mono text-sm focus:outline-none focus:border-emerald-500/50"
                >
                  <option value="auto">Auto (try platform, cloud, legacy)</option>
                  <option value="ibm_quantum_platform">ibm_quantum_platform</option>
                  <option value="ibm_cloud">ibm_cloud</option>
                  <option value="ibm_quantum">ibm_quantum (legacy)</option>
                </select>
                <p className="text-[10px] text-zinc-500 mt-2 leading-tight">
                  Auto mode improves compatibility across installed qiskit runtime client versions.
                </p>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">
                  Runtime Instance (optional)
                </label>
                <input
                  data-testid="runtime-instance-input"
                  type="text"
                  value={runtimeInstance}
                  onChange={(e) => setRuntimeInstance(e.target.value)}
                  placeholder="For example hub/group/project or cloud instance identifier"
                  className="w-full bg-[#0a0a0a] border border-zinc-800 rounded-md px-4 py-2.5 text-zinc-200 font-mono text-sm focus:outline-none focus:border-emerald-500/50"
                />
                <p className="text-[10px] text-zinc-500 mt-2 leading-tight">
                  Some IBM runtime accounts require an instance to access hardware backends.
                </p>
              </div>
              
              <div>
                <label className="block text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">
                  Shots
                </label>
                <input
                  type="number"
                  value={shotsInput}
                  min={1}
                  max={MAX_SHOTS}
                  step={1}
                  onChange={(e) => handleShotsChange(e.target.value)}
                  className="w-full bg-[#0a0a0a] border border-zinc-800 rounded-md px-4 py-2.5 text-zinc-200 font-mono text-sm focus:outline-none focus:border-emerald-500/50"
                />
                <p className="text-[10px] text-zinc-500 mt-2 leading-tight">
                  Optimization level is controlled in Circuit Generation and currently set to {executionSettings.optimizationLevel}.
                </p>
              </div>

              <div className="space-y-3">
                <button
                  data-testid="load-backends-button"
                  type="button"
                  onClick={handleLoadBackends}
                  disabled={isLoadingBackends}
                  className="w-full bg-zinc-800 hover:bg-zinc-700 text-zinc-100 font-medium py-2.5 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoadingBackends ? 'Loading backend catalog...' : 'Load Accessible Hardware'}
                </button>

                {backendCatalogError && (
                  <p className="text-xs text-red-300">{backendCatalogError}</p>
                )}

                {backendCatalog && (
                  <div data-testid="backend-catalog" className="rounded-md border border-zinc-800 bg-[#0a0a0a] p-3 space-y-2">
                    <p className="text-xs text-zinc-400">
                      Runtime channel in use:{' '}
                      <span className="font-mono text-zinc-300">{backendCatalog.runtime_channel_used || 'unknown'}</span>
                    </p>
                    <p className="text-xs text-zinc-400">
                      Recommended backend:{' '}
                      <span className="font-mono text-emerald-400">{backendCatalog.recommended_backend || 'n/a'}</span>
                    </p>
                    <div className="max-h-36 overflow-auto space-y-1 pr-1">
                      {backendCatalog.backends.map((backend) => (
                        <div
                          key={backend.name}
                          className="flex items-center justify-between text-[11px] bg-zinc-900 border border-zinc-800 rounded px-2 py-1"
                        >
                          <span className="font-mono text-zinc-300">{backend.name}</span>
                          <span className="text-zinc-500">
                            {backend.num_qubits ?? '?'}q | {backend.pending_jobs ?? 'n/a'} queued
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <button
                data-testid="execute-button"
                onClick={handleExecute}
                disabled={isExecuting || !canExecute || shotInputError !== null}
                className="w-full bg-emerald-500 hover:bg-emerald-600 text-emerald-950 font-medium py-2.5 rounded-md transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isExecuting ? (
                  <span className="animate-pulse">Submitting and polling IBM Quantum job...</span>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-current" />
                    Execute Job on {targetBackend === 'least_busy' ? 'Auto' : targetBackend}
                  </>
                )}
              </button>

              {hasInFlightJob && (
                <button
                  data-testid="cancel-job-button"
                  type="button"
                  onClick={handleCancelJob}
                  disabled={isCancelling}
                  className="w-full bg-red-500/90 hover:bg-red-500 text-red-50 font-medium py-2.5 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isCancelling ? 'Cancelling runtime job...' : 'Cancel Current Job'}
                </button>
              )}
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
              <span data-testid="job-id-display" className="px-2 py-1 bg-zinc-800 rounded text-xs font-mono text-zinc-400">
                {hasResult
                  ? `${showingPreviousResult ? 'Previous Result Job ID' : 'Job ID'}: ${result.job_id}`
                  : jobStatus?.job_id
                    ? `Job ID: ${jobStatus.job_id} (${jobStatus.status})`
                    : 'Job ID: not available'}
              </span>
            </div>
            
            <div className="h-[250px] w-full">
              {hasResult ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={result.counts} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
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
              ) : (
                <div className="h-full w-full flex items-center justify-center text-center px-6">
                  <p className="text-sm text-zinc-500">
                    No probability distribution yet. Run an execution job to display measured output.
                  </p>
                </div>
              )}
            </div>
          </div>

          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
            <h3 className="font-medium text-zinc-200 mb-4">Jones Polynomial Result</h3>
            <div className="bg-[#0a0a0a] border border-zinc-800 rounded-md p-6 flex flex-col items-center justify-center gap-4">
              {hasResult ? (
                <>
                  <div data-testid="jones-polynomial" className="font-serif italic text-2xl text-emerald-400 tracking-wider">
                    {result.jones_polynomial}
                  </div>
                  <p className="text-xs text-zinc-500 font-mono">
                    Evaluated at root of unity: e^(2*pi*i/5)
                  </p>
                </>
              ) : (
                <>
                  <div className="font-serif italic text-xl text-zinc-500 tracking-wide">
                    No polynomial result yet
                  </div>
                  <p className="text-xs text-zinc-500 font-mono text-center">
                    This panel updates after a successful hardware execution response.
                  </p>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
