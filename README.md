# Q-Knot

Front end plus Python back end for submitting a simplified knot-evaluation circuit to IBM Quantum hardware.

## Current delivery status

- Phases one through seven are complete.
- Release gate status is green for required checks.
- Optional live hardware smoke run remains pending until valid IBM credentials are provided.
- Latest validated release gate commit: `a36709e`.

## What runs where

- Front end development server: React and Vite (`http://localhost:3000`)
- Standalone runtime: FastAPI serving both user interface and application programming interface (`http://localhost:8000`)
- IBM hardware access: handled by the Python back end through `qiskit-ibm-runtime`

## Prerequisites

- Option one (container): Docker Desktop
- Option two (desktop launcher): Python 3.10, 3.11, or 3.12

Notes:
- The pinned quantum packages in `backend/requirements.txt` may not install on very new Python releases.
- A real IBM Quantum token must be set in backend environment variable `IBM_QUANTUM_TOKEN` for hardware routes.
- Some IBM accounts also require a runtime instance identifier.
- Node.js 22.x is only required for development workflows and local front end rebuilds.
- Front end commands enforce Node.js 22.x and fail fast on unsupported versions.
- If front end source folders change, update the `@source` lines in `src/index.css` before running production builds.

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

## Running against IBM hardware

1. Set backend credentials before starting the standalone runtime:
   ```bash
   export IBM_QUANTUM_TOKEN="<your-token>"
   ```
2. In the `Execution & Results` screen, choose a runtime channel:
   - For the first live hardware run, select `ibm_cloud` explicitly.
   - `Auto` may fail on some runtime client versions before fallback is attempted.
3. Provide `Runtime Instance` if your account requires one.
4. Set shots.
5. Run the job.

Notes:
- The execution screen no longer accepts token input.
- The token must be provided to the backend process environment.

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

## Expanded braid support behavior

- Braid parsing now accepts tokens in the form `sN` and `sN^-1` for any positive integer `N`.
- Verification checks for contiguous generator ranges and reports missing generators in computed evidence.
- Circuit generation scales qubit width with the highest generator index in the braid word.
- Execution blocks invalid braid problems before submit, including too few tokens, one-generator braids, and non-contiguous generator ranges.

## Release gate artifacts

- Release checklist: `docs/release-checklist.md`
- Release runbook: `docs/release-runbook.md`
- Optional live hardware smoke workflow script: `scripts/run-live-hardware-smoke.py`

## Development checks

Use Node.js `22.19.0` (or any `22.x`) before running front end checks:

```bash
nvm use 22.19.0
```

```bash
npm run lint
npm test
npm run test:backend
npm run build
```
