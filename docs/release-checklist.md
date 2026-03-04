# Release Checklist

Last validated: 2026-03-04
Gate status: green
Validated commit: `37fc97c`

Simulator backend added: 2026-03-03
Simulator commit: `a74fd27`

Research-grade invariant upgrade: 2026-03-04
Phase 8 completed: 2026-03-04

## Latest validation evidence

- Host type check: `npm run lint` passed.
- Host full test sequence: `npm run test:all` passed (includes Playwright mocked E2E suite).
- Host production build: `npm run build` passed.
- Backend suite: `python3 -m unittest discover -s backend -p "test_*.py"` passed (119 tests, 0 skipped).
- Playwright mocked E2E suite: `npm run test:e2e` passed (11 tests: pipeline, error handling, job execution).
- Packaged container flow: `docker compose up --build -d` passed with route checks for health, ingestion, verification, and circuit generation.
- Runtime submit route correctly blocks when backend token is not configured: `{"detail":"Backend is missing IBM credentials. Set IBM_QUANTUM_TOKEN before calling runtime routes."}`.
- Container teardown: `docker compose down` passed.
- Live hardware smoke run (legacy output baseline): job `d6h151m48nic73ameq3g` on `ibm_fez` completed with `jones_polynomial: "V(t) = 0.906t^-4 + t^-3 + t^-1"` and `expectation_value: 0.90625`.
- Simulator backend: full submit→poll cycle completed locally with no IBM token. Simulator backend test suite passes in `backend/test_simulator_backend.py`.
- Playwright mocked E2E suite: `npm run test:e2e` passed (14 tests: pipeline, error handling, job execution, simulator).
- Phase 8 standalone smoke: simulator submit→poll for Trefoil braid returned `jones_value_real: -1.2360679774997894`, `jones_polynomial: "V(t) = -1.236068 at t = exp(2*pi*i/5)"` — AJL path ran successfully, no fallback.

## Phase Seven Required Checks

- [x] Backend mocked end to end submission and polling check is present: `backend/test_submit_poll_end_to_end.py`.
- [x] Frontend execution screen submit and poll behavior checks are present: `src/components/__tests__/ExecutionResults.test.tsx`.
- [x] Playwright E2E mocked suite is present and passes: `npm run test:e2e` (14 tests in `e2e/mocked/`).
- [x] Full host test sequence passes: `npm run test:all`.
- [x] Packaged container flow starts and serves both user interface and application programming interface.
- [x] Published release runbook exists: `docs/release-runbook.md`.

## Simulator Backend Checks

- [x] `qiskit_simulator` backend routes submit and poll without requiring `IBM_QUANTUM_TOKEN`.
- [x] IBM backend submit and poll still block correctly when token is absent (regression confirmed in `test_simulator_backend.py`).
- [x] 39 simulator tests pass: `backend/test_simulator_backend.py` (`SimulatorEngineSubmitTests`, `SimulatorEngineResultTests`, `SimulatorApiRouteTests`).
- [x] Simulator job IDs use `sim-` prefix for token-free poll routing.
- [x] Frontend hides Runtime Channel and Runtime Instance fields when `qiskit_simulator` is selected.
- [x] 3 Playwright E2E simulator tests pass: `e2e/mocked/simulator.spec.ts` (Tests 12–14: full pipeline, fields hidden, fields restore on IBM switch).

## Phase 8 Checks — Path-Model Invariant Engine

Phase 8 commit: `37fc97c`

- [x] `NumpyAvailabilityTest.test_numpy_is_importable` passes (not skipped) in backend suite.
- [x] `AharonovJonesLandauInvariantTests` — all 5 tests pass (not skipped): complex return type, determinism, trefoil/figure-eight distinction, generator unitarity, output formatter format.
- [x] `SimulatorApiRouteTests.test_full_submit_then_poll_cycle` — `jones_value_real` is non-null float, `jones_polynomial` contains no fallback string.
- [x] Standalone smoke: simulator poll response shows `jones_value_real: -1.2360679774997894`, `jones_polynomial: "V(t) = -1.236068 at t = exp(2*pi*i/5)"`.
- [x] Full host test sequence passes: `npm run test:all` (119 backend tests, 22 frontend tests, 14 Playwright E2E tests).
- [x] Generator matrices confirmed unitary (`M†M = I` to `1e-9`) and invertible (`M * M⁻¹ = I`).
- [x] `_compute_generator_matrix` corrected: braid relation `ρ(σᵢ) = a·I + a⁻¹·Pᵢ` replaces erroneous `a·I + a⁻¹·d·Pᵢ` formula. Unitarity follows from `a² + a⁻² = -d` and `P² = d·P`.

## Optional Live Hardware Smoke Check

- [x] Run live hardware smoke workflow with valid backend credentials.
  - Backend: `ibm_fez` (156 qubits), channel: `ibm_cloud`, shots: 128
  - Job ID: `d6h151m48nic73ameq3g`
  - Result (legacy baseline): `COMPLETED` — `jones_polynomial: "V(t) = 0.906t^-4 + t^-3 + t^-1"`, `expectation_value: 0.90625`
  - Knot: Trefoil (3_1), braid word `s1 s2^-1 s1 s2^-1`, Dowker `4 6 2`
