/**
 * Shared test constants for E2E tests.
 */

export const TREFOIL = {
  dowker: '4 6 2',
  knotName: 'Trefoil Knot (3_1)',
  braidWord: 's1 s2^-1 s1 s2^-1',
} as const;

export const FIGURE_EIGHT = {
  dowker: '4 6 8 2',
  knotName: 'Figure-Eight Knot (4_1)',
  braidWord: 's1 s2^-1 s1 s2 s1^-1 s2',
} as const;

export const NON_CATALOG = {
  // Valid 5-crossing Dowker notation (permutation of 2,4,6,8,10) not in catalog.
  // Catalog only has (6,8,10,2,4) for Cinquefoil; (2,4,6,10,8) is a different key.
  dowker: '2 4 6 10 8',
} as const;

export const INVALID_DOWKER = {
  // Odd values — rejected by the parser
  dowker: '3 5 7',
} as const;

export const MOCK_JOB_ID = 'test-job-abc-123';

export const MOCK_BACKENDS_RESPONSE = {
  runtime_channel_used: 'ibm_quantum_platform',
  runtime_instance_used: null,
  recommended_backend: 'ibm_marrakesh',
  backends: [
    { name: 'ibm_marrakesh', num_qubits: 156, pending_jobs: 2, operational: true },
    { name: 'ibm_fez', num_qubits: 156, pending_jobs: 5, operational: true },
    { name: 'ibm_torino', num_qubits: 133, pending_jobs: 1, operational: true },
  ],
};

export const MOCK_JOB_RESULT = {
  job_id: MOCK_JOB_ID,
  backend: 'ibm_marrakesh',
  runtime_channel_used: 'ibm_quantum_platform',
  runtime_instance_used: null,
  counts: [
    { name: '00', probability: 0.375 },
    { name: '11', probability: 0.625 },
  ],
  expectation_value: 0.625,
  jones_polynomial: 'V(t) = -t^-4 + t^-3 + t^-1',
  status: 'COMPLETED',
};
