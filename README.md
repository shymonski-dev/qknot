# Q-Knot

Front end plus Python back end for submitting a path-model knot-evaluation circuit to IBM Quantum hardware.

## Current delivery status

- All eight phases are complete.
- Qiskit simulator backend added: full pipeline runs locally with no IBM token required.
- Release gate status is green for all required checks including the Playwright E2E suite.
- Live hardware smoke run completed against `ibm_fez` (Trefoil, 128 shots, job `d6h151m48nic73ameq3g`, Jones polynomial returned).
- Topological invariant evaluation uses a correct Aharonov Jones Landau path model implementation: braid generators are unitary (`ρ(σᵢ) = a·I + a⁻¹·Pᵢ`), and Jones values are confirmed non-null through the full simulator pipeline.
- Latest validated release gate commit: `37fc97c`.

## What runs where

- Front end development server: React and Vite (`http://localhost:3000`)
- Standalone runtime: FastAPI serving both user interface and application programming interface (`http://localhost:8000`)
- IBM hardware access: handled by the Python back end through `qiskit-ibm-runtime`
- Local simulation: handled by the Python back end through `qiskit.primitives.StatevectorSampler` — no IBM token required

## Prerequisites

- Option one (container): Docker Desktop
- Option two (desktop launcher): Python 3.10, 3.11, or 3.12

Notes:
- The pinned quantum packages in `backend/requirements.txt` may not install on very new Python releases.
- `IBM_QUANTUM_TOKEN` is only required for IBM hardware routes. The `qiskit_simulator` backend runs locally with no token.
- Some IBM accounts also require a runtime instance identifier.
- Node.js 22.x is only required for development workflows and local front end rebuilds.
- Front end commands enforce Node.js 22.x and fail fast on unsupported versions.
- If front end source folders change, update the `@source` lines in `src/index.css` before running production builds.
- The front end currently imports `src/styles.prebuilt.css` to avoid local style transform stalls during development server startup.

## Quick start (container, no Python setup)

From the repository root:

```bash
# Optional but required for hardware submit, poll, cancel, and backend list routes:
# export IBM_QUANTUM_TOKEN="<your-token>"
docker compose up
```

Open `http://localhost:8000`.

What this does:
- Reuses committed front end distribution files from `dist`
- Installs backend dependencies inside the container image
- Serves both user interface and API from one container on port `8000`

Stop with `Ctrl + C`, then run `docker compose down`.

## Quick start (desktop standalone, no Node)

From the repository root:

```bash
./launchers/start-macos.command
```

Linux:

```bash
./launchers/start-linux.sh
```

Windows:

```bat
.\launchers\start-windows.bat
```

These launcher files are committed in this repository and do not require a generation step.

What this does:
- Automatically creates `backend/.venv` when needed
- Installs or refreshes backend Python dependencies when `backend/requirements.txt` changes
- Uses committed `dist` files for the user interface
- Starts a single standalone runtime on `http://localhost:8000`

You can stop with `Ctrl + C`.

If your machine has multiple Python versions and you want to force one:

```bash
python3.12 scripts/start-standalone.py
```

## Node-based standalone command (development)

From the repository root:

```bash
npm install
npm run start:standalone
```

## Desktop launcher packaging (optional bundle output)

From the repository root:

```bash
npm install
npm run package:desktop
```

This creates platform launcher files in `release/desktop`:
- `start-macos.command`
- `start-linux.sh`
- `start-windows.bat`
- `README.txt`

If you want the packaging step to rebuild `dist` first:

```bash
QKNOT_PACKAGE_WITH_BUILD=1 npm run package:desktop
```

## Manual local setup (advanced)

### 1. Install front end dependencies

```bash
npm install
```

### 2. Create a Python virtual environment and install back end dependencies

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
```

### 3. Start the Python back end

From the repository root:

```bash
export IBM_QUANTUM_TOKEN="<your-token>"
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/api/health
```

### 4. Start the front end

From the repository root:

```bash
npm run dev
```

Open `http://localhost:3000`.

The development server proxies relative `/api/*` calls to `http://localhost:8000`.
If your backend runs elsewhere, set:

```bash
QKNOT_BACKEND_PROXY_TARGET="http://your-backend-host:8000" npm run dev
```

If you change user interface styles and want to refresh the prebuilt style file:

```bash
npm run build
cp dist/assets/index-*.css src/styles.prebuilt.css
```

## Running locally with the simulator (no IBM token)

1. Select `qiskit_simulator (Local)` from the Target Hardware dropdown in the sidebar.
2. Run through the pipeline: ingest → verify → generate circuit → execute.
3. Results return immediately from `qiskit.primitives.StatevectorSampler`. No IBM token is needed.

The simulator uses exact statevector simulation with no noise model. It is suitable for pipeline and development testing, not hardware-fidelity benchmarking.

## Running against IBM hardware

1. Set backend credentials before starting the standalone runtime:
   ```bash
   export IBM_QUANTUM_TOKEN="<your-token>"
   ```
2. Select an IBM backend from the Target Hardware dropdown.
3. In the `Execution & Results` screen, choose a runtime channel:
   - For the first live hardware run, select `ibm_cloud` explicitly.
   - `Auto` may fail on some runtime client versions before fallback is attempted.
4. Provide `Runtime Instance` if your account requires one.
5. Set shots.
6. Run the job.

Notes:
- The execution screen no longer accepts token input.
- The token must be provided to the backend process environment.
- The Runtime Channel and Runtime Instance fields are hidden when `qiskit_simulator` is selected.

## Knot ingestion behavior

- The `Knot Ingestion` screen now calls `POST /api/knot/ingest` on the Python backend.
- Dowker notation is validated server side before braid generation.
- Validation errors are shown directly in the user interface.

## Topological verification behavior

- The `Topological Verification` screen now calls `POST /api/knot/verify` on the Python backend.
- Verification returns computed evidence: token count, generator usage, inverse count, net writhe, alternation, and strand connectivity.
- The pipeline only marks verification complete when `is_verified` is true.

## Circuit generation behavior

- The `Circuit Generation` screen now calls `POST /api/knot/circuit/generate` on the Python backend.
- Generation returns backend computed circuit metadata: depth, width, operation counts, and a deterministic signature.
- The execution submit request includes closure method and compares the generated signature with the submitted job circuit signature before polling.

## Topological invariant evaluation behavior

- The backend computes Jones values through an Aharonov Jones Landau style path model representation.
- Output uses root-of-unity evaluation formatting: `V(t) = <value> at t = exp(2*pi*i/k)`.
- Completed result payloads include `jones_value_real`, `jones_value_imag`, and `jones_root_of_unity` when evaluation dependencies are available.

## Expanded braid support behavior

- Braid parsing now accepts tokens in the form `sN` and `sN^-1` for any positive integer `N`.
- Verification checks for contiguous generator ranges and reports missing generators in computed evidence.
- Circuit generation allocates one ancilla plus a compressed work register derived from the admissible path basis dimension.
- Execution blocks invalid braid problems before submit, including too few tokens, one-generator braids, and non-contiguous generator ranges.

## Release gate artifacts

- Release checklist: `docs/release-checklist.md`
- Release runbook: `docs/release-runbook.md`
- Optional live hardware smoke workflow script: `scripts/run-live-hardware-smoke.py`

## End to end tests

The repository ships a Playwright E2E suite covering the full pipeline from the browser.

```bash
npm run test:e2e         # mocked suite (CI-safe, 14 tests, no IBM credentials required)
npm run test:e2e:live    # live IBM smoke tests (requires IBM_QUANTUM_TOKEN)
```

Mocked test coverage:
- Pipeline happy path: Trefoil, Figure-Eight, and non-catalog knots (Tests 1–3)
- Error handling: invalid notation, verification failure stub, network abort, server 500 (Tests 4–7)
- Job execution: submit → poll → result, cancellation, localStorage resume, poll timeout (Tests 8–11)
- Simulator backend: full pipeline, runtime fields hidden, fields restore on IBM switch (Tests 12–14)

Live smoke tests (Tests L1–L2) call real IBM backends and gate on `IBM_QUANTUM_TOKEN`.

The Playwright config (`playwright.config.ts`) auto-starts both the backend and Vite dev server when running tests.

## Backend unit tests

```bash
python3 -m unittest discover -s backend -p "test_*.py"
```

Test files:
- `test_simulator_backend.py` — covers `run_simulator_experiment`, `get_simulator_result`, HTTP routing, IBM regression, and a full submit→poll HTTP cycle
- `test_submit_poll_end_to_end.py` — mocked IBM submit and poll end-to-end
- `test_api_main.py` — Pydantic model validation and API handler routing
- `test_braid_parser.py`, `test_braid_validation.py` — braid word parsing and validation
- `test_circuit_generation.py` — circuit build and transpile
- `test_knot_ingestion.py`, `test_knot_verification.py` — Dowker notation and topological verification
- `test_poll_knot_experiment.py`, `test_quantum_engine_helpers.py` — job polling and engine helpers
- `test_ajl_invariant.py` — path model invariant and output formatting checks

## Development checks

Use Node.js `22.19.0` (or any `22.x`) before running front end checks:

```bash
nvm use 22.19.0
```

```bash
npm run lint
npm test
npm run test:backend
npm run test:e2e
npm run build
```

`npm run test:all` runs lint, front end unit tests, backend unit tests, and the mocked Playwright E2E suite.
