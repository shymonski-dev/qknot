# Release Checklist

Last validated: 2026-02-27
Gate status: green
Validated commit: pending commit for backend credential and routing contract changes

## Latest validation evidence

- Host type check: `npm run lint` passed.
- Host full test sequence: `npm run test:all` passed.
- Host production build: `npm run build` passed.
- Backend suite: `python3 -m unittest discover -s backend -p "test_*.py"` passed.
- Packaged container flow: `docker compose up --build -d` passed with route checks for health, ingestion, verification, and circuit generation.
- Runtime submit route correctly blocks when backend token is not configured: `{"detail":"Backend is missing IBM credentials. Set IBM_QUANTUM_TOKEN before calling runtime routes."}`.
- Container teardown: `docker compose down` passed.

## Phase Seven Required Checks

- [x] Backend mocked end to end submission and polling check is present: `backend/test_submit_poll_end_to_end.py`.
- [x] Frontend execution screen submit and poll behavior checks are present: `src/components/__tests__/ExecutionResults.test.tsx`.
- [x] Full host test sequence passes: `npm run test:all`.
- [x] Packaged container flow starts and serves both user interface and application programming interface.
- [x] Published release runbook exists: `docs/release-runbook.md`.

## Optional Live Hardware Smoke Check

- [ ] Run live hardware smoke workflow with valid backend credentials.
  - Script: `scripts/run-live-hardware-smoke.py`
  - Runbook section: `docs/release-runbook.md`
  - Current preflight result without credentials: submit fails with backend token configuration error.
