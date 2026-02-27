# Seven Phase Delivery Plan

## Phase 1: Test Infrastructure Reliability
- Fix front end test runner hang.
- Enforce deterministic test lifecycle cleanup.
- Exit criteria: `npm test` exits reliably on clean machines.

## Phase 2: Real Knot Ingestion
- Replace mocked notation to braid conversion with backend driven parsing.
- Add structured validation and user interface error handling.
- Exit criteria: real notation parsing with deterministic outputs.

## Phase 3: Real Verification
- Replace simulated verification with backend computed checks.
- Return verification evidence and pass or fail status.
- Exit criteria: verification reflects computed results.

## Phase 4: Real Circuit Generation
- Generate circuits from parsed braid data in backend.
- Render real generated circuit metadata in user interface.
- Exit criteria: generated and submitted circuit data match.

## Phase 5: Expanded Braid Support
- Support generators beyond one and two, including inverse tokens.
- Validate knot problem input before job submission.
- Exit criteria: parser accepts expanded language and rejects invalid inputs clearly.

## Phase 6: Packaged Distribution
- Provide container and desktop packaging options.
- Remove manual Python setup burden for testers.
- Exit criteria: fresh machine can run app and submit jobs with packaged flow.

## Phase 7: Release Gate
- Add end to end mocked submission and polling checks.
- Add optional live hardware smoke run workflow.
- Exit criteria: release checklist is green with published runbook.

## Status
- Phase 1: completed (unsupported Node versions now fail fast and global front end test cleanup is centralized).
- Phase 2: completed (real knot ingestion route, validation, user interface wiring, and user interface tests are in working tree).
- Phase 3: completed (backend verification route and evidence model are active with back end and front end tests).
- Phase 4: completed (backend circuit generation route returns circuit summaries, and execution submit enforces signature consistency with generated metadata).
