# Q-Knot

Front end plus Python back end for submitting a simplified knot-evaluation circuit to IBM Quantum hardware.

## What runs where

- Front end: React and Vite (`http://localhost:3000`)
- Back end: FastAPI (`http://localhost:8000`)
- IBM hardware access: handled by the Python back end through `qiskit-ibm-runtime`

## Prerequisites

- Node.js 22.x
- Python 3.10, 3.11, or 3.12 recommended

Notes:
- The pinned quantum packages in `backend/requirements.txt` may not install on very new Python releases.
- A real IBM Quantum token is required for hardware runs.
- Some IBM accounts also require a runtime instance identifier.

## Quick start (standalone local testing)

From the repository root:

```bash
npm install
npm run dev:standalone
```

What this does:
- Automatically creates `backend/.venv` when needed
- Installs or refreshes backend Python dependencies when `backend/requirements.txt` changes
- Starts the Python backend on `http://localhost:8000`
- Starts the user interface on `http://localhost:3000`

You can stop both services with `Ctrl + C`.

If your machine has multiple Python versions and you want to force one:

```bash
QKNOT_PYTHON=python3.12 npm run dev:standalone
```

## Manual local setup

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

## Development checks

```bash
npm run lint
npm test
npm run test:backend
```
