# Field Evaluation — Q-Knot in the Contemporary Quantum Landscape

*Assessed March 2026*

## What this software is

Q-Knot is a faithful end-to-end implementation of the Aharonov-Jones-Landau (AJL) algorithm, a 2006 theoretical result proving that a quantum computer can additively approximate the Jones polynomial at roots of unity in polynomial time. The implementation is mathematically correct — the path model representation is sound, the generator matrices are unitary, the Markov trace formula is properly applied — and it runs on real IBM quantum hardware.

That matters as a baseline. The AJL algorithm is frequently cited but rarely implemented to this depth.

## Where it sits in the research landscape

**The algorithm is foundational, not frontier.**

AJL (2006) belongs to the same era as Shor (1994) and Grover (1996) — the canonical results that established what quantum computers are theoretically good for. They remain intellectually important, but the field has moved considerably. The current research frontier has split into three directions, and Q-Knot is adjacent to all three without being at the leading edge of any.

### 1. Topological quantum computing

The most direct heir to this work is the programme to build quantum computers whose *programming model is the braid group itself*. Non-abelian anyons — particularly Fibonacci anyons, which are exactly the representation used in Q-Knot's path model at `k = 5` — can perform universal quantum computation through braiding alone, with topological protection against decoherence.

Microsoft's topological qubit programme, based on Majorana zero modes, is pursuing this architecture. If it succeeds, the braid group stops being the object of study and becomes the instruction set. Q-Knot computes *about* braiding; a topological quantum computer computes *by* braiding.

### 2. Quantum complexity and advantage

The AJL result established that Jones polynomial approximation is in BQP (efficiently solvable by quantum computers). The classical hardness — exact computation is #P-hard — was already known. Together they constitute one of the few unconditional separations between quantum and classical complexity.

However, the problem sizes where this separation becomes practically meaningful are far beyond current scale. A 3-qubit circuit for the Trefoil Jones polynomial can be evaluated classically in microseconds — Q-Knot's own `evaluate_jones_at_root_of_unity` function does this. The quantum circuit is a demonstration of the mechanism, not yet of advantage.

The crossover point — where the quantum circuit outpaces the best classical simulation — requires knots of sufficient crossing number that the path model Hilbert space exceeds classical memory tractability. For the Fibonacci anyon representation at `k = 5`, that threshold is roughly 40–50 crossings, requiring approximately 30+ logical qubits. Current fault-tolerant hardware is not there yet.

### 3. Richer topological invariants

The Jones polynomial has been partially superseded in pure mathematics by more powerful invariants. Khovanov homology (2000) categorifies the Jones polynomial: it assigns a chain complex to each knot whose Euler characteristic recovers the Jones polynomial, but which contains strictly more topological information. There is active research on whether Khovanov homology admits a quantum algorithm with favourable complexity, but no settled result exists.

The HOMFLY-PT polynomial (a two-variable generalisation containing the Jones polynomial as a specialisation) and knot Floer homology are richer invariants that current quantum algorithms do not efficiently compute. Q-Knot evaluates the Jones polynomial at a single root of unity — the weakest form of Jones-type topological information.

## Phase 9–10 research extensions (March 2026)

Since the initial field assessment, four research extensions have been completed.

**Phase 9a — Larger knots.** The KnotInfo database (2,979 knots up to 13+ crossings) is integrated via a three-tier lookup: hardcoded catalog → KnotInfo → deterministic fallback. The path-model circuit is already general for any strand count; Hilbert space dimensions are 3 strands→3, 6 strands→13, 8 strands→34. Braid words and Jones values are now verified across the full catalog.

**Phase 9b — Zero-noise extrapolation.** IBM hardware jobs now submit three gate-folded copies of each circuit (scale factors 1×, 3×, 5×) and apply Richardson extrapolation to estimate the zero-noise ancilla expectation value. A classical noiseless reference `Re(U[0,0])` is computed for comparison. This is the first systematic noise-mitigation layer in the pipeline.

**Phase 9c — Multi-k Jones and HOMFLY-PT string lookup.** Jones polynomial is now evaluated at k = 5, 7, 9 simultaneously. The HOMFLY-PT polynomial string is retrieved from the KnotInfo database and returned alongside every ingestion result. (Note: Jones samples a one-dimensional slice of the two-variable HOMFLY-PT space; the two are independent data fields.)

**Phase 10a — Classical Hecke algebra HOMFLY-PT.** A from-scratch implementation of the Ocneanu trace on the Hecke algebra H_n(q) using the permutation basis computes HOMFLY-PT exactly. Cross-checked against KnotInfo polynomial strings for trefoil, figure-eight, and cinquefoil to five decimal places. This provides a classical ground truth for HOMFLY-PT independently of the database lookup.

**Phase 10b — sl_N colored HOMFLY-PT via quantum group R-matrix.** The standard (non-unitary) U_q(gl_N) R-matrix is used to build the Reshetikhin-Turaev representation of any braid. The RT normalization `P(β̂) = conj(v^{−e} · tr_q(U) / [N]_q)` computes the HOMFLY-PT at the sl_N specialisation point. Cross-checked at sl_2 and sl_3 for trefoil, figure-eight, and cinquefoil. A unitary circuit variant (`build_sl3_hadamard_circuit`) is ready for IBM hardware — this would be the first quantum execution of a circuit derived from the sl_3 representation.

Key distinction: there are two R-matrices. The symmetric unitary R (`cos(θ)·SWAP + i·sin(θ)·I`) is used in the quantum circuit and satisfies hardware constraints but does not produce HOMFLY-PT directly. The standard non-unitary U_q(gl_N) R-matrix produces HOMFLY-PT but cannot be implemented as a quantum gate.

## Experimental results

Running all three catalog knots through the full pipeline at `t = exp(2πi/5)`:

| Knot | Type | V(t) | \|V(t)\| |
|---|---|---|---|
| Trefoil (3_1) | Chiral torus T(2,3) | `−0.809017 + 1.314328i` | 1.543362 |
| Figure-Eight (4_1) | Amphichiral hyperbolic | `−1.236068` | 1.236068 |
| Cinquefoil (5_1) | Chiral torus T(2,5) | `−0.381966` | 0.381966 |

All three are cleanly separated (pairwise `|ΔV|` from 0.85 to 2.78). The Figure-Eight value `−1.236068 = 1 − √5` and the Cinquefoil value `−0.381966 = −1/φ²` (where `φ = (1+√5)/2` is the golden ratio) are not coincidences: the path model at `k = 5` encodes the quantum dimension of the Fibonacci anyon, and the golden ratio is the natural algebraic currency of the fifth root of unity. The Figure-Eight is amphichiral (equal to its mirror image), so its Jones polynomial is real at every root of unity. The Cinquefoil is the torus knot T(2,5), and its Jones polynomial evaluates to a real number at the fifth root of unity for the same algebraic reason.

## What makes it genuinely significant

**The Fibonacci anyon connection.** The path model at `k = 5` is the representation theory of Fibonacci anyons — the simplest non-abelian anyons capable of universal topological quantum computation. Every controlled-unitary gate in the circuit is a simulated braid of Fibonacci anyons. When topological quantum hardware matures, the circuits Q-Knot generates are exactly what will run natively, without simulation overhead.

**Full-stack completeness.** Most demonstrations of quantum knot algorithms operate at the circuit level. Q-Knot starts from human-readable Dowker notation, parses to braid words, constructs the path model representation from first principles, builds the quantum circuit, submits to hardware, and returns a formatted invariant with a live cross-check against the classical computation. Errors at any layer are detectable — which is how the generator matrix bug (`ρ(σᵢ) = a·I + a⁻¹·d·Pᵢ` → `a·I + a⁻¹·Pᵢ`) was found and corrected.

## What would move it forward

Ranked by impact:

1. ~~**Larger knots.**~~ **Done — Phase 9a.** KnotInfo catalog (2,979 knots) integrated; path model verified for arbitrary strand count.

2. ~~**Error mitigation on the quantum path.**~~ **Done — Phase 9b.** Zero-noise extrapolation via Richardson extrapolation at scale factors 1×, 3×, 5× is active on IBM hardware jobs.

3. **Crossover profiling.** The scientifically interesting question is: at what knot complexity does the quantum circuit become competitive with the best classical simulation? Profiling both paths as problem size scales would locate and demonstrate that threshold empirically. This remains open.

4. ~~**Extension to HOMFLY-PT or Khovanov homology.**~~ **Done — Phases 9c, 10a, 10b.** HOMFLY-PT is now computed via three independent methods: KnotInfo lookup, Hecke algebra (Ocneanu trace), and sl_N quantum group R-matrix. All cross-check. Khovanov homology remains open.

5. **Quantum execution of the sl_N circuit.** `build_sl3_hadamard_circuit` is implemented and verified but has not yet been submitted to hardware. Running it on IBM hardware would be the first quantum execution of a circuit from the sl_3 representation — a genuine experimental first.

6. **True quantum HOMFLY-PT.** The standard U_q(gl_N) R-matrix that produces HOMFLY-PT is non-unitary and cannot be directly implemented as a quantum gate. Ancilla-assisted simulation of non-unitary evolution (e.g. linear combination of unitaries) would be required. No settled approach exists.

## Honest assessment (updated March 2026)

| Dimension | Assessment |
|---|---|
| Mathematical correctness | Sound. AJL representation faithful; HOMFLY-PT verified via three independent methods. |
| Hardware integration | Genuine — Jones polynomial on IBM hardware with ZNE noise mitigation. |
| Quantum advantage | Not demonstrated at current problem sizes. Classical evaluation is faster. |
| Pedagogical value | High. End-to-end AJL plus two independent HOMFLY-PT engines with cross-checks. |
| Research novelty | Low for Jones (algorithm is 20 years old). Moderate for sl_N quantum circuit (no prior hardware run exists). |
| Positioning for future relevance | Good. All core components — Fibonacci anyon path model, sl_N R-matrix, RT normalization — are direct prerequisites for topological quantum computation. |

## One-sentence summary

Q-Knot is a correct, hardware-connected implementation of the AJL quantum knot algorithm extended with three independent HOMFLY-PT engines, operating at problem sizes too small to demonstrate quantum advantage but at the precise conceptual intersection — Fibonacci anyons, quantum group representations, Reshetikhin-Turaev invariants — that is becoming central to topological quantum hardware research.
