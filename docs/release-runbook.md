# Release Runbook

This runbook defines the release gate workflow for phase seven.

## 1. Environment Preparation

1. Use Node 22.19.0:
   ```bash
   nvm use 22.19.0
   ```
2. Ensure Docker daemon is running:
   ```bash
   docker info
   ```

## 2. Host Test Gate

Run the full automated test gate:

```bash
npm run lint
npm run test:all
npm run build
```

Expected result:
- type check passes
- frontend unit tests pass
- backend unit tests pass
- Playwright mocked E2E suite passes (11 tests)
- production build completes

Style note:
- The front end imports `src/styles.prebuilt.css` in local development mode.
- After style changes, refresh this file from the latest build output.

## 3. Packaged Container Gate

1. Build and start packaged runtime:
   ```bash
   docker compose up --build -d
   ```
2. Validate health and user interface routes:
   ```bash
   curl http://127.0.0.1:8000/api/health
   curl -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/
   ```
3. Validate knot pipeline routes:
   ```bash
   curl -X POST http://127.0.0.1:8000/api/knot/ingest \
     -H 'Content-Type: application/json' \
     -d '{"dowker_notation":"4 6 2"}'

   curl -X POST http://127.0.0.1:8000/api/knot/verify \
     -H 'Content-Type: application/json' \
     -d '{"braid_word":"s1 s2^-1 s3 s2 s1^-1"}'

   curl -X POST http://127.0.0.1:8000/api/knot/circuit/generate \
     -H 'Content-Type: application/json' \
     -d '{"braid_word":"s1 s2^-1 s3 s2 s1^-1","optimization_level":2,"closure_method":"trace","target_backend":"ibm_kyiv"}'
   ```
4. Stop packaged runtime:
   ```bash
   docker compose down
   ```

## 4. Mocked End To End Backend Gate

Run backend tests and confirm these cases pass:

- `backend/test_submit_poll_end_to_end.py::SubmitPollEndToEndTests::test_submit_then_poll_reaches_completed_state`
- `backend/test_simulator_backend.py::SimulatorApiRouteTests::test_full_submit_then_poll_cycle`

Command:

```bash
python3 -m unittest discover -s backend -p "test_*.py"
```

## 5. Simulator Smoke Gate

Confirm the simulator backend runs the full pipeline with no IBM token:

```bash
curl -s -X POST http://127.0.0.1:8000/api/jobs/submit \
  -H 'Content-Type: application/json' \
  -d '{"backend_name":"qiskit_simulator","braid_word":"s1 s2^-1 s1 s2^-1","shots":512,"optimization_level":1,"closure_method":"trace"}' \
  | python3 -m json.tool
```

Expected: `status: "SUBMITTED"`, `job_id` starting with `sim-`, `backend: "qiskit_simulator"`.

Then poll with the returned `job_id`:

```bash
curl -s -X POST http://127.0.0.1:8000/api/jobs/poll \
  -H 'Content-Type: application/json' \
  -d '{"job_id":"<sim-job-id>"}' \
  | python3 -m json.tool
```

Expected: `status: "COMPLETED"`, `counts` list, `expectation_value` float, and `jones_polynomial` in root-of-unity format (`V(t) = <value> at t = exp(2*pi*i/k)`). Responses may include `jones_value_real`, `jones_value_imag`, and `jones_root_of_unity` when evaluation dependencies are present.

This gate requires no `IBM_QUANTUM_TOKEN` in the environment.

## 6. Frontend E2E Test Gate

Run the Playwright mocked test suite independently to confirm all browser-level flows pass:

```bash
npm run test:e2e
```

Expected result: 14 tests pass across four suites:
- `e2e/mocked/pipeline.spec.ts` — Tests 1–3: Trefoil, Figure-Eight, and non-catalog knot happy paths
- `e2e/mocked/errors.spec.ts` — Tests 4–7: invalid notation, verification failure stub, network abort, server 500
- `e2e/mocked/jobs.spec.ts` — Tests 8–11: submit → poll → result, cancellation, localStorage resume, poll timeout
- `e2e/mocked/simulator.spec.ts` — Tests 12–14: full simulator pipeline, runtime fields hidden, fields restore on IBM switch

The Playwright config auto-starts the backend (`IBM_QUANTUM_TOKEN=test`) and the Vite dev server when this command runs, so no manual server startup is required.

To run with a visible browser for debugging:

```bash
npx playwright test --project=mocked --headed
```

## 7. Optional Live Hardware Smoke Gate

This step is optional and should run only when valid hardware credentials are available.

Pre-flight guidance:
- Use an explicit runtime channel for first live run.
- Recommended value: `ibm_cloud`.
- Avoid `auto` on first run because some runtime client versions may return a channel error before fallback is attempted.
- Recommended backend: `ibm_torino` or `ibm_marrakesh` (Heron r2, 3–5× better EPLG than Eagle r3). Avoid `ibm_fez` for sl_3 circuits — Eagle r3 EPLG is too high for useful signal.

Option A — Python smoke script:

1. Start backend runtime (`docker compose up -d` or local standalone launcher).
2. Set environment variables:
   ```bash
   export IBM_QUANTUM_TOKEN="<your-token>"
   export QKNOT_BACKEND_NAME="ibm_torino"
   export QKNOT_RUNTIME_CHANNEL="ibm_cloud"
   # Optional:
   # export QKNOT_RUNTIME_INSTANCE="<crn>"
   # export QKNOT_BRAID_WORD="s1 s2^-1 s1 s2^-1"
   ```
3. Run smoke workflow:
   ```bash
   python3 scripts/run-live-hardware-smoke.py
   ```
4. Archive the output payload in release notes.
5. If the backend is not running, the smoke script exits with a network error and nonzero status.

Option B — Playwright live smoke tests:

```bash
IBM_QUANTUM_TOKEN="<your-token>" npm run test:e2e:live
```

Tests L1–L2 list available backends and submit a Trefoil job against the first available backend, then cancel it before polling completes.

## 8. Phase 8 Gate — Path-Model Invariant Engine

Confirm the AJL invariant engine runs (no skips, no fallback) in the backend suite and in standalone smoke.

### 8a. Backend suite — confirm no AJL skips

```bash
backend/.venv/bin/python3 -m unittest discover -s backend -p "test_*.py" -v 2>&1 | grep -E "ajl|AJL|Numpy"
```

Expected: `NumpyAvailabilityTest.test_numpy_is_importable ... ok` and all five `AharonovJonesLandauInvariantTests` lines show `ok` (not `skipped`).

### 8b. Standalone smoke — confirm non-null jones fields

Start the backend (via launcher or uvicorn), then submit and poll a simulator job:

```bash
curl -s -X POST http://127.0.0.1:8000/api/jobs/submit \
  -H 'Content-Type: application/json' \
  -d '{"backend_name":"qiskit_simulator","braid_word":"s1 s2^-1 s1 s2^-1","shots":512,"optimization_level":1,"closure_method":"trace"}' \
  | python3 -m json.tool

# Extract job_id from the submit response, then poll:
curl -s -X POST http://127.0.0.1:8000/api/jobs/poll \
  -H 'Content-Type: application/json' \
  -d '{"job_id":"<sim-job-id>"}' \
  | python3 -m json.tool
```

Pass conditions:
- `jones_value_real` is a float (not `null`)
- `jones_polynomial` starts with `V(t) =` and does not contain `unavailable`
- `jones_root_of_unity` is `5`

## 9. Phase 9 Gate — KnotInfo Catalog, ZNE, Multi-k Jones

### 9a. KnotInfo catalog lookup

```bash
curl -s -X POST http://127.0.0.1:8000/api/knot/ingest \
  -H 'Content-Type: application/json' \
  -d '{"dowker_notation":"4 6 2"}' \
  | python3 -m json.tool
```

Pass conditions:
- `knot_name` is `"3_1"` (trefoil)
- `braid_word` is `"s1 s2 s1 s2"`
- `homfly_pt` is a non-null string (e.g. `"(2*v^2-v^4)+(v^2)*z^2"`)
- `is_catalog_match` is `true`

### 9b. Multi-k Jones in simulator result

Submit and poll a simulator job, then check:
- `jones_multi_k` is a list with three entries (k = 5, 7, 9)
- Each entry has `k`, `real`, `imag`, `polynomial` fields

### 9c. ZNE fields in backend suite

```bash
backend/.venv/bin/python3 -m unittest discover -s backend -p "test_*.py" -v 2>&1 | grep -E "zne|ZNE|fold|richardson"
```

Expected: ZNE-related tests show `ok`.

## 10. Phase 10 Gate — HOMFLY-PT (Hecke and sl_N)

### 10a. Hecke algebra HOMFLY-PT

```bash
backend/.venv/bin/python3 -m unittest backend.test_homfly -v
```

Expected: 18 tests, all `ok`. Key tests:
- `HomflyEvaluationTests.test_trefoil_matches_knotinfo_homfly_string`
- `HomflyEvaluationTests.test_figure_eight_matches_knotinfo_homfly_string`
- `HomflyEvaluationTests.test_cinquefoil_matches_knotinfo_homfly_string`

### 10b. sl_N quantum group HOMFLY-PT

```bash
backend/.venv/bin/python3 -m unittest backend.test_sl3_homfly -v
```

Expected: 32 tests, all `ok`. Key tests:
- `SlNHomflyEvalTests.test_sl2_trefoil_matches_knotinfo`
- `SlNHomflyEvalTests.test_sl3_trefoil_matches_knotinfo`
- `SlNHomflyEvalTests.test_fig8_is_amphichiral_sl3_value_is_real`
- `Sl3CircuitTests.test_circuit_qubit_count_for_3_strand` (expects 7 qubits)

### 10c. Full backend suite count

```bash
backend/.venv/bin/python3 -m unittest discover -s backend -p "test_*.py" 2>&1 | tail -3
```

Expected: `Ran 200 tests in ...` with `OK`.
