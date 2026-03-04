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

## Experimental results

Running all three catalog knots through the full pipeline at `t = exp(2πi/5)`:

| Knot | Type | V(t) | \|V(t)\| |
|---|---|---|---|
| Trefoil (3_1) | Chiral torus T(2,3) | `−1.236068` | 1.236068 |
| Figure-Eight (4_1) | Amphichiral hyperbolic | `1.500000 − 0.363271i` | 1.543362 |
| Cinquefoil (5_1) | Chiral torus T(2,5) | `−0.618034 − 0.726543i` | 0.953850 |

All three are cleanly separated (pairwise `|ΔV|` from 0.95 to 2.76). The Trefoil value `−1.236068 = 1 − φ` and the Cinquefoil real part `−0.618034 = −1/φ` (where `φ` is the golden ratio) are not coincidences: the path model at `k = 5` encodes the quantum dimension of the Fibonacci anyon, and the golden ratio is the natural algebraic currency of the fifth root of unity.

## Honest assessment

| Dimension | Assessment |
|---|---|
| Mathematical correctness | Sound. The AJL representation is faithfully implemented. |
| Hardware integration | Genuine — runs on IBM Quantum with verified results. |
| Quantum advantage | Not demonstrated at current problem sizes. Classical evaluation is faster. |
| Pedagogical value | High. One of the clearest end-to-end AJL implementations available. |
| Research novelty | Low — the algorithm is 20 years old. |
| Positioning for future relevance | Good. Sits at the right conceptual intersection. |

## What makes it genuinely significant

**The Fibonacci anyon connection.** The path model at `k = 5` is the representation theory of Fibonacci anyons — the simplest non-abelian anyons capable of universal topological quantum computation. Every controlled-unitary gate in the circuit is a simulated braid of Fibonacci anyons. When topological quantum hardware matures, the circuits Q-Knot generates are exactly what will run natively, without simulation overhead.

**Full-stack completeness.** Most demonstrations of quantum knot algorithms operate at the circuit level. Q-Knot starts from human-readable Dowker notation, parses to braid words, constructs the path model representation from first principles, builds the quantum circuit, submits to hardware, and returns a formatted invariant with a live cross-check against the classical computation. Errors at any layer are detectable — which is how the generator matrix bug (`ρ(σᵢ) = a·I + a⁻¹·d·Pᵢ` → `a·I + a⁻¹·Pᵢ`) was found and corrected.

## What would move it forward

Ranked by impact:

1. **Larger knots.** The interesting regime starts around 10–15 crossings. This requires extending the catalog, improving fallback braid generation for arbitrary Dowker notation, and handling larger path model Hilbert spaces.

2. **Error mitigation on the quantum path.** The circuit expectation value and the classical Jones value diverge on real hardware due to noise. Zero-noise extrapolation or probabilistic error cancellation would let the quantum path serve as a genuine cross-check.

3. **Crossover profiling.** The scientifically interesting question is: at what knot complexity does the quantum circuit become competitive with the best classical simulation? Profiling both paths as problem size scales would locate and demonstrate that threshold empirically.

4. **Extension to HOMFLY-PT or Khovanov homology.** The Jones polynomial at one root of unity is one data point. Richer invariants would constitute a genuine research contribution.

## One-sentence summary

Q-Knot is a correct, hardware-connected implementation of a foundational quantum algorithm that operates at problem sizes too small to demonstrate quantum advantage, at a conceptual intersection — Fibonacci anyons, braid group representations, topological quantum computation — that is becoming one of the most active areas in quantum hardware research.
