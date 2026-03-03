# Release Checklist

Last validated: 2026-02-27
Gate status: green
Validated commit: `7c237ac`

Simulator backend added: 2026-03-03
Simulator commit: `a74fd27`

## Latest validation evidence

- Host type check: `npm run lint` passed.
- Host full test sequence: `npm run test:all` passed (includes Playwright mocked E2E suite).
- Host production build: `npm run build` passed.
- Backend suite: `python3 -m unittest discover -s backend -p "test_*.py"` passed.
- Playwright mocked E2E suite: `npm run test:e2e` passed (11 tests: pipeline, error handling, job execution).
- Packaged container flow: `docker compose up --build -d` passed with route checks for health, ingestion, verification, and circuit generation.
- Runtime submit route correctly blocks when backend token is not configured: `{"detail":"Backend is missing IBM credentials. Set IBM_QUANTUM_TOKEN before calling runtime routes."}`.
- Container teardown: `docker compose down` passed.
- Live hardware smoke run: job `d6h151m48nic73ameq3g` on `ibm_fez` completed with `jones_polynomial: "V(t) = 0.906t^-4 + t^-3 + t^-1"` and `expectation_value: 0.90625`.
- Simulator backend: full submit→poll cycle completed locally with no IBM token. 39 tests pass in `backend/test_simulator_backend.py`.

## Phase Seven Required Checks

- [x] Backend mocked end to end submission and polling check is present: `backend/test_submit_poll_end_to_end.py`.
- [x] Frontend execution screen submit and poll behavior checks are present: `src/components/__tests__/ExecutionResults.test.tsx`.
- [x] Playwright E2E mocked suite is present and passes: `npm run test:e2e` (11 tests in `e2e/mocked/`).
- [x] Full host test sequence passes: `npm run test:all`.
- [x] Packaged container flow starts and serves both user interface and application programming interface.
- [x] Published release runbook exists: `docs/release-runbook.md`.

## Simulator Backend Checks

- [x] `qiskit_simulator` backend routes submit and poll without requiring `IBM_QUANTUM_TOKEN`.
- [x] IBM backend submit and poll still block correctly when token is absent (regression confirmed in `test_simulator_backend.py`).
- [x] 39 simulator tests pass: `backend/test_simulator_backend.py` (`SimulatorEngineSubmitTests`, `SimulatorEngineResultTests`, `SimulatorApiRouteTests`).
- [x] Simulator job IDs use `sim-` prefix for token-free poll routing.
- [x] Frontend hides Runtime Channel and Runtime Instance fields when `qiskit_simulator` is selected.

## Optional Live Hardware Smoke Check

- [x] Run live hardware smoke workflow with valid backend credentials.
  - Backend: `ibm_fez` (156 qubits), channel: `ibm_cloud`, shots: 128
  - Job ID: `d6h151m48nic73ameq3g`
  - Result: `COMPLETED` — `jones_polynomial: "V(t) = 0.906t^-4 + t^-3 + t^-1"`, `expectation_value: 0.90625`
  - Knot: Trefoil (3_1), braid word `s1 s2^-1 s1 s2^-1`, Dowker `4 6 2`
