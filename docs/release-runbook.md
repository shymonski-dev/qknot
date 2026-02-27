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

Run backend tests and confirm this case passes:

- `backend/test_submit_poll_end_to_end.py::SubmitPollEndToEndTests::test_submit_then_poll_reaches_completed_state`

Command:

```bash
python3 -m unittest discover -s backend -p "test_*.py"
```

## 5. Frontend E2E Test Gate

Run the Playwright mocked test suite independently to confirm all browser-level flows pass:

```bash
npm run test:e2e
```

Expected result: 11 tests pass across three suites:
- `e2e/mocked/pipeline.spec.ts` — Tests 1–3: Trefoil, Figure-Eight, and non-catalog knot happy paths
- `e2e/mocked/errors.spec.ts` — Tests 4–7: invalid notation, verification failure stub, network abort, server 500
- `e2e/mocked/jobs.spec.ts` — Tests 8–11: submit → poll → result, cancellation, localStorage resume, poll timeout

The Playwright config auto-starts the backend (`IBM_QUANTUM_TOKEN=test`) and the Vite dev server when this command runs, so no manual server startup is required.

To run with a visible browser for debugging:

```bash
npx playwright test --project=mocked --headed
```

## 6. Optional Live Hardware Smoke Gate

This step is optional and should run only when valid hardware credentials are available.

Pre-flight guidance:
- Use an explicit runtime channel for first live run.
- Recommended value: `ibm_cloud`.
- Avoid `auto` on first run because some runtime client versions may return a channel error before fallback is attempted.
- Recommended backend: `ibm_fez` (156 qubits). Alternatives: `ibm_marrakesh`, `ibm_torino`.

Option A — Python smoke script:

1. Start backend runtime (`docker compose up -d` or local standalone launcher).
2. Set environment variables:
   ```bash
   export IBM_QUANTUM_TOKEN="<your-token>"
   export QKNOT_BACKEND_NAME="ibm_fez"
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
