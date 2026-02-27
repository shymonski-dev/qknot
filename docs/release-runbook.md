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
- frontend tests pass
- backend tests pass
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

## 5. Optional Live Hardware Smoke Gate

This step is optional and should run only when valid hardware credentials are available.

Pre-flight guidance:
- Use an explicit runtime channel for first live run.
- Recommended value: `ibm_cloud`.
- Avoid `auto` on first run because some runtime client versions may return a channel error before fallback is attempted.

1. Start backend runtime (`docker compose up -d` or local standalone launcher).
2. Set environment variables:
   ```bash
   export IBM_QUANTUM_TOKEN="<your-token>"
   export QKNOT_BACKEND_NAME="ibm_kyiv"
   export QKNOT_RUNTIME_CHANNEL="ibm_cloud"
   # Optional:
   # export QKNOT_RUNTIME_INSTANCE="<instance>"
   # export QKNOT_BRAID_WORD="s1 s2^-1 s1 s2^-1"
   ```
3. Run smoke workflow:
   ```bash
   python3 scripts/run-live-hardware-smoke.py
   ```
4. Archive the output payload in release notes.
5. If the backend is not running, the smoke script exits with a network error and nonzero status.
