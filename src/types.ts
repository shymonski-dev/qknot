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
  closure_method?: ClosureMethod;
  circuit_summary?: KnotCircuitSummary;
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

export interface KnotIngestionResponse {
  dowker_notation_normalized: string;
  crossing_count: number;
  knot_name: string;
  braid_word: string;
  root_of_unity: number;
  is_catalog_match: boolean;
}

export interface KnotVerificationEvidence {
  token_count: number;
  generator_counts: {
    s1: number;
    s2: number;
  };
  inverse_count: number;
  net_writhe: number;
  generator_switches: number;
  alternation_ratio: number;
  strand_connectivity: string;
}

export interface KnotVerificationResponse {
  is_verified: boolean;
  status: 'verified' | 'failed';
  detail: string;
  evidence: KnotVerificationEvidence;
}

export interface KnotCircuitSummary {
  depth: number;
  size: number;
  width: number;
  num_qubits: number;
  num_clbits: number;
  two_qubit_gate_count: number;
  measurement_count: number;
  operation_counts: Record<string, number>;
  signature: string;
}

export interface KnotCircuitGenerationResponse {
  target_backend: string;
  optimization_level: number;
  closure_method: ClosureMethod;
  braid_word: string;
  circuit_summary: KnotCircuitSummary;
}

export interface KnotData {
  id: string;
  name: string;
  dowkerNotation: string;
  braidWord: string;
  rootOfUnity: number;
  status: KnotStatus;
  jonesPolynomial?: string;
  circuitSummary?: KnotCircuitSummary;
}
