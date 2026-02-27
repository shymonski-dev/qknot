# Q-Knot

Front end plus Python back end for submitting a simplified knot-evaluation circuit to IBM Quantum hardware.

## What runs where

- Front end: React and Vite (`http://localhost:3000`)
- Back end: FastAPI (`http://localhost:8000`)
- IBM hardware access: handled by the Python back end through `qiskit-ibm-runtime`

## Prerequisites

- Option one (container): Docker Desktop
- Option two (desktop launcher): Node.js 22.x and Python 3.10, 3.11, or 3.12

Notes:
- The pinned quantum packages in `backend/requirements.txt` may not install on very new Python releases.
- A real IBM Quantum token is required for hardware runs.
- Some IBM accounts also require a runtime instance identifier.
- Front end commands enforce Node.js 22.x and fail fast on unsupported versions.

## Quick start (container, no Python setup)

From the repository root:

```bash
docker compose up --build
```

Open `http://localhost:8000`.

What this does:
- Builds the front end inside the container image
- Installs backend dependencies inside the container image
- Serves both user interface and API from one container on port `8000`

Stop with `Ctrl + C`, then run `docker compose down`.

## Quick start (desktop standalone)

From the repository root:

```bash
npm install
npm run start:standalone
```

What this does:
- Automatically creates `backend/.venv` when needed
- Installs or refreshes backend Python dependencies when `backend/requirements.txt` changes
- Uses existing `dist` output, or builds it if missing
- Starts a single standalone runtime on `http://localhost:8000`

You can stop with `Ctrl + C`.

If your machine has multiple Python versions and you want to force one:

```bash
QKNOT_PYTHON=python3.12 npm run start:standalone
```

If you need to force a fresh front end build before start:

```bash
QKNOT_FORCE_FRONTEND_BUILD=1 npm run start:standalone
```

## Desktop launcher packaging

From the repository root:

```bash
npm install
npm run package:desktop
```

This creates platform launcher files in `release/desktop`:
- `start-macos.command`
- `start-linux.sh`
- `start-windows.bat`

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

## Running against IBM hardware

In the `Execution & Results` screen:

1. Paste your IBM Quantum token.
2. Keep `Python Backend URL` as `http://localhost:8000` unless your back end is elsewhere.
3. Choose a runtime channel:
   - `Auto` tries platform, cloud, then legacy for compatibility with different `qiskit-ibm-runtime` client versions.
   - You can select a specific channel if your environment requires it.
4. Provide `Runtime Instance` if your account requires one.
5. Set shots.
6. Run the job.

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

## Development checks

Use Node.js `22.19.0` (or any `22.x`) before running front end checks:

```bash
nvm use 22.19.0
```

```bash
npm run lint
npm test
npm run test:backend
```
