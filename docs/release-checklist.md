# Release Checklist

Last validated: 2026-02-27
Gate status: green

## Phase Seven Required Checks

- [x] Backend mocked end to end submission and polling check is present: `backend/test_submit_poll_end_to_end.py`.
- [x] Frontend execution screen submit and poll behavior checks are present: `src/components/__tests__/ExecutionResults.test.tsx`.
- [x] Full host test sequence passes: `npm run test:all`.
- [x] Packaged container flow starts and serves both user interface and application programming interface.
- [x] Published release runbook exists: `docs/release-runbook.md`.

## Optional Live Hardware Smoke Check

- [ ] Run live hardware smoke workflow when valid credentials are available.
  - Script: `scripts/run-live-hardware-smoke.py`
  - Runbook section: `docs/release-runbook.md`
