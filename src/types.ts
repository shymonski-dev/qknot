export type PipelineStep = 
  | 'dashboard'
  | 'ingestion'
  | 'verification'
  | 'circuit'
  | 'pulse'
  | 'qec'
  | 'execution';

export interface KnotData {
  id: string;
  name: string;
  dowkerNotation: string;
  braidWord: string;
  rootOfUnity: number;
  status: 'pending' | 'verified' | 'compiled' | 'executed';
  jonesPolynomial?: string;
}
