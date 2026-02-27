export type PipelineStep = 
  | 'dashboard'
  | 'ingestion'
  | 'verification'
  | 'circuit'
  | 'pulse'
  | 'qec'
  | 'execution';

export type KnotStatus = 'pending' | 'verified' | 'compiled' | 'executed';
export type ClosureMethod = 'trace' | 'plat';

export interface ExecutionSettings {
  shots: number;
  optimizationLevel: 0 | 1 | 2 | 3;
  closureMethod: ClosureMethod;
}

export interface ExperimentResult {
  job_id: string;
  backend: string;
  runtime_channel_used?: string | null;
  runtime_instance_used?: string | null;
  counts: { name: string; probability: number }[];
  expectation_value: number;
  jones_polynomial: string;
  status: string;
}

export interface ExperimentJobStatus {
  job_id: string;
  backend?: string;
  runtime_channel_used?: string | null;
  runtime_instance_used?: string | null;
  status: string;
  detail?: string;
}

export interface BackendSummary {
  name: string;
  num_qubits?: number | null;
  pending_jobs?: number | null;
  operational?: boolean | null;
}

export interface BackendCatalogResponse {
  runtime_channel_used?: string | null;
  runtime_instance_used?: string | null;
  recommended_backend?: string | null;
  backends: BackendSummary[];
}

export interface KnotData {
  id: string;
  name: string;
  dowkerNotation: string;
  braidWord: string;
  rootOfUnity: number;
  status: KnotStatus;
  jonesPolynomial?: string;
}
