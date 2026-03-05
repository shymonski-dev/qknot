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
- Add Playwright browser E2E test suite (11 mocked tests, 2 live smoke tests).
- Add optional live hardware smoke run workflow.
- Exit criteria: release checklist is green with published runbook.

## Phase 8: Research-grade Invariant Engine
- Replace parity-based braid gate templates with a path model representation implementation.
- Replace heuristic Jones output with root-of-unity invariant evaluation output.
- Preserve submit and poll compatibility by carrying braid metadata into completed result formatting.
- Exit criteria: invariant evaluator and output format are wired into simulator and runtime result paths with test coverage.

## Status
- Phase 1: completed (unsupported Node versions now fail fast and global front end test cleanup is centralized).
- Phase 2: completed (real knot ingestion route, validation, user interface wiring, and user interface tests are in working tree).
- Phase 3: completed (backend verification route and evidence model are active with back end and front end tests).
- Phase 4: completed (backend circuit generation route returns circuit summaries, and execution submit enforces signature consistency with generated metadata).
- Phase 5: completed (parser accepts expanded braid tokens, verification handles multi-strand connectivity checks, and execution blocks invalid non-contiguous braid problems before submit).
- Phase 6: completed (container path uses committed frontend distribution for faster builds, repository ships launcher files for macOS Linux and Windows, and standalone startup works through Python-only launcher flow without local Node requirement).
- Phase 7: completed (release checklist and runbook are published, mocked end to end submit poll backend check is added, Playwright E2E suite added with 11 mocked tests and 2 live smoke tests, and live hardware smoke run completed against ibm_fez with Jones polynomial result returned).
- Phase 8: completed (generator matrix formula corrected to ρ(σᵢ) = a·I + a⁻¹·P — unitary and invertible; AJL tests pass with no skips; standalone smoke confirms jones_value_real is non-null; 119 backend tests green).

## Phase 9: Research Extensions

### Phase 9a: Larger Knots
- Add `database_knotinfo==0.6` dependency (KnotInfo database, 2,979 knots up to 13+ crossings).
- Add three functions to `quantum_engine.py`: `_parse_knotinfo_braid_notation`, `_parse_knotinfo_dt_key`, `_load_knotinfo_catalog`.
- Update `compile_dowker_notation` to a 3-tier lookup: hardcoded catalog → KnotInfo → deterministic fallback.
- Add `KnotInfoCatalogTests` to `test_knot_ingestion.py`; add cross-representation Jones test to `test_ajl_invariant.py`.
- The quantum engine (path model basis, circuit construction) is already general for any strand count — no changes needed there.
- Hilbert space dimensions: 3 strands→3, 6 strands→13, 8 strands→34; circuit grows to ~6-7 qubits for 12-crossing knots.
- Status: completed (129 backend tests, all green; correct braid words verified: trefoil s1 s2 s1 s2, figure-eight s1 s2^-1 s1 s2^-1, cinquefoil s1 s1 s1 s1 s1 s2).

### Phase 9b: Zero-Noise Extrapolation
- Global gate folding at scale factors [1, 3, 5] via `_fold_gates`; Richardson extrapolation via `_richardson_extrapolate`.
- IBM hardware jobs submit three folded circuits as one batch; result includes `zne_ancilla_expectation`, `zne_classical_reference`, and deviation fields.
- Classical noiseless reference `Re(U[0,0])` provided by `_compute_classical_ancilla_expectation`.
- No new dependencies; no frontend changes; simulator path unchanged.
- Status: completed (139 backend tests, all green).

### Phase 9c: HOMFLY-PT Polynomial
- Stitch Jones evaluations at multiple roots of unity into the two-variable HOMFLY-PT polynomial.
- No settled quantum algorithm exists — genuine research frontier.
- Blocked on Phase 9a and 9b.
- Status: not started.
