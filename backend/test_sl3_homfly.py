"""Phase 10b: sl_N colored HOMFLY-PT via quantum group R-matrix.

Tests the unitary R-matrix construction for sl_N fundamental representation,
the sl_N Markov trace (quantum group trace), and cross-checks against
KnotInfo HOMFLY-PT strings at the sl_2 and sl_3 specialization points.

Cross-check convention (KnotInfo): v^{-1}*P(L+) - v*P(L-) = z*P(L0).
sl_N evaluation point: v = q^N, z = q - q^{-1}, q = exp(2*pi*i/k).
"""
import cmath
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import numpy as np
    _HAS_NUMPY = True
except ModuleNotFoundError:
    _HAS_NUMPY = False

import quantum_engine

# ---------------------------------------------------------------------------
# Reference values — KnotInfo strings evaluated at sl_N specialization points
# ---------------------------------------------------------------------------

def _knotinfo_at_sln(homfly_str: str, sl_n: int, k: int = 5) -> complex:
    """Evaluate a KnotInfo HOMFLY string at the sl_N evaluation point."""
    q = cmath.exp(2j * cmath.pi / k)
    v = q ** sl_n
    z = q - 1 / q
    return quantum_engine._evaluate_homfly_string(homfly_str, v, z)


TREFOIL_BRAID = "s1 s2 s1 s2"
FIG8_BRAID    = "s1 s2^-1 s1 s2^-1"
CINQ_BRAID    = "s1 s1 s1 s1 s1 s2"

TREFOIL_HOMFLY = "(2*v^2-v^4)+(v^2)*z^2"
FIG8_HOMFLY    = "(v^(-2)-1+v^2)+(-1)*z^2"
CINQ_HOMFLY    = "(3*v^4-2*v^6)+(4*v^4-v^6)*z^2+(v^4)*z^4"


# ---------------------------------------------------------------------------
# R-matrix and helper tests
# ---------------------------------------------------------------------------

@unittest.skipIf(not _HAS_NUMPY, "numpy required")
class SlNMatrixTests(unittest.TestCase):

    def _q(self, k=5):
        return cmath.exp(2j * cmath.pi / k)

    def test_swap_sl2_shape(self):
        S = quantum_engine._build_sln_swap(2)
        self.assertEqual(S.shape, (4, 4))

    def test_swap_sl3_shape(self):
        S = quantum_engine._build_sln_swap(3)
        self.assertEqual(S.shape, (9, 9))

    def test_swap_is_involution(self):
        """SWAP^2 = I for both sl_2 and sl_3."""
        for n in (2, 3):
            S = quantum_engine._build_sln_swap(n)
            self.assertTrue(np.allclose(S @ S, np.eye(n * n), atol=1e-12))

    def test_r_matrix_sl2_shape(self):
        q = self._q()
        R = quantum_engine._build_sln_r_matrix(2, q)
        self.assertEqual(R.shape, (4, 4))

    def test_r_matrix_sl3_shape(self):
        q = self._q()
        R = quantum_engine._build_sln_r_matrix(3, q)
        self.assertEqual(R.shape, (9, 9))

    def test_r_matrix_sl2_unitary(self):
        """sl_2 R-matrix is unitary at root of unity."""
        q = self._q()
        R = quantum_engine._build_sln_r_matrix(2, q)
        self.assertTrue(np.allclose(R.conj().T @ R, np.eye(4), atol=1e-12))

    def test_r_matrix_sl3_unitary(self):
        """sl_3 R-matrix is unitary at root of unity."""
        q = self._q()
        R = quantum_engine._build_sln_r_matrix(3, q)
        self.assertTrue(np.allclose(R.conj().T @ R, np.eye(9), atol=1e-12))

    def test_r_matrix_hecke_relation(self):
        """(R - q*I)(R + q^{-1}*I) = 0 for sl_3 R-matrix."""
        q = self._q()
        R = quantum_engine._build_sln_r_matrix(3, q)
        I = np.eye(9, dtype=complex)
        result = (R - q * I) @ (R + (1 / q) * I)
        self.assertTrue(np.allclose(result, np.zeros((9, 9)), atol=1e-12))

    def test_r_matrix_eigenvalues(self):
        """R has eigenvalues q (x 6 on Sym) and -q^{-1} (x 3 on Anti) for sl_3."""
        q = self._q()
        R = quantum_engine._build_sln_r_matrix(3, q)
        evals = np.linalg.eigvals(R)
        evals_sorted = sorted(evals, key=lambda x: (round(x.real, 6), round(x.imag, 6)))
        expected_q = q
        expected_minus_qinv = -1 / q
        q_count = sum(1 for e in evals if abs(e - expected_q) < 1e-9)
        anti_count = sum(1 for e in evals if abs(e - expected_minus_qinv) < 1e-9)
        self.assertEqual(q_count, 6, "Should have 6 eigenvalues equal to q (Sym² sector)")
        self.assertEqual(anti_count, 3, "Should have 3 eigenvalues equal to -q^{-1} (Λ² sector)")

    def test_quantum_dim_sl2(self):
        """[2]_q = q + q^{-1} = 2*cos(2*pi/k)."""
        q = self._q()
        qd = quantum_engine._sln_quantum_dim(2, q)
        expected = q + 1 / q
        self.assertAlmostEqual(abs(qd - expected), 0, places=12)

    def test_quantum_dim_sl3(self):
        """[3]_q = q^2 + 1 + q^{-2}."""
        q = self._q()
        qd = quantum_engine._sln_quantum_dim(3, q)
        expected = q ** 2 + 1 + q ** (-2)
        self.assertAlmostEqual(abs(qd - expected), 0, places=12)

    def test_quantum_trace_identity_normalizes(self):
        """tr_q(I^{⊗n}) = [N]_q^n for sl_3, n=2."""
        q = self._q()
        sl_n, n = 3, 2
        U = np.eye(sl_n ** n, dtype=complex)
        tr = quantum_engine._sln_quantum_trace(U, sl_n, n, q)
        expected = quantum_engine._sln_quantum_dim(sl_n, q) ** n
        self.assertAlmostEqual(abs(tr - expected), 0, places=10)

    def test_braid_unitary_is_unitary_sl3(self):
        """The braid unitary for the trefoil is unitary in sl_3."""
        q = self._q()
        U, _ = quantum_engine._build_sln_braid_unitary(TREFOIL_BRAID, 3, q)
        n = U.shape[0]
        self.assertTrue(np.allclose(U.conj().T @ U, np.eye(n), atol=1e-10))

    def test_braid_unitary_is_unitary_sl2(self):
        """The braid unitary for the figure-eight is unitary in sl_2."""
        q = self._q()
        U, _ = quantum_engine._build_sln_braid_unitary(FIG8_BRAID, 2, q)
        n = U.shape[0]
        self.assertTrue(np.allclose(U.conj().T @ U, np.eye(n), atol=1e-10))

    def test_embed_two_site_shape_3strand(self):
        """Embedded 2-site gate has correct shape for 3-strand sl_3."""
        sl_n = 3
        op = np.eye(9, dtype=complex)
        full = quantum_engine._embed_two_site_gate(op, 0, 3, sl_n)
        self.assertEqual(full.shape, (27, 27))
        full2 = quantum_engine._embed_two_site_gate(op, 1, 3, sl_n)
        self.assertEqual(full2.shape, (27, 27))


# ---------------------------------------------------------------------------
# HOMFLY-PT evaluation tests
# ---------------------------------------------------------------------------

@unittest.skipIf(not _HAS_NUMPY, "numpy required")
class SlNHomflyEvalTests(unittest.TestCase):

    def test_returns_dict_with_required_fields(self):
        result = quantum_engine.evaluate_homfly_sln(TREFOIL_BRAID, sl_n=3)
        for field in ("real", "imag", "sl_n", "root_of_unity",
                      "v_real", "v_imag", "z_real", "z_imag"):
            self.assertIn(field, result)

    def test_sl_n_field_matches_argument(self):
        r2 = quantum_engine.evaluate_homfly_sln(TREFOIL_BRAID, sl_n=2)
        r3 = quantum_engine.evaluate_homfly_sln(TREFOIL_BRAID, sl_n=3)
        self.assertEqual(r2["sl_n"], 2)
        self.assertEqual(r3["sl_n"], 3)

    def test_is_deterministic(self):
        a = quantum_engine.evaluate_homfly_sln(TREFOIL_BRAID, sl_n=3)
        b = quantum_engine.evaluate_homfly_sln(TREFOIL_BRAID, sl_n=3)
        self.assertAlmostEqual(a["real"], b["real"], places=12)
        self.assertAlmostEqual(a["imag"], b["imag"], places=12)

    def test_sl2_trefoil_matches_knotinfo(self):
        """sl_2 evaluation matches KnotInfo HOMFLY at (v=q^2, z=q-q^{-1})."""
        result = quantum_engine.evaluate_homfly_sln(TREFOIL_BRAID, sl_n=2)
        ki = _knotinfo_at_sln(TREFOIL_HOMFLY, sl_n=2)
        self.assertAlmostEqual(result["real"], ki.real, places=5,
            msg="Trefoil sl_2 HOMFLY real part must match KnotInfo")
        self.assertAlmostEqual(result["imag"], ki.imag, places=5,
            msg="Trefoil sl_2 HOMFLY imag part must match KnotInfo")

    def test_sl3_trefoil_matches_knotinfo(self):
        """sl_3 evaluation matches KnotInfo HOMFLY at (v=q^3, z=q-q^{-1})."""
        result = quantum_engine.evaluate_homfly_sln(TREFOIL_BRAID, sl_n=3)
        ki = _knotinfo_at_sln(TREFOIL_HOMFLY, sl_n=3)
        self.assertAlmostEqual(result["real"], ki.real, places=5,
            msg="Trefoil sl_3 HOMFLY real part must match KnotInfo")
        self.assertAlmostEqual(result["imag"], ki.imag, places=5,
            msg="Trefoil sl_3 HOMFLY imag part must match KnotInfo")

    def test_sl2_fig8_matches_knotinfo(self):
        """sl_2 figure-eight matches KnotInfo at (v=q^2, z=q-q^{-1})."""
        result = quantum_engine.evaluate_homfly_sln(FIG8_BRAID, sl_n=2)
        ki = _knotinfo_at_sln(FIG8_HOMFLY, sl_n=2)
        self.assertAlmostEqual(result["real"], ki.real, places=5)
        self.assertAlmostEqual(result["imag"], ki.imag, places=5)

    def test_sl3_fig8_matches_knotinfo(self):
        """sl_3 figure-eight matches KnotInfo at (v=q^3, z=q-q^{-1})."""
        result = quantum_engine.evaluate_homfly_sln(FIG8_BRAID, sl_n=3)
        ki = _knotinfo_at_sln(FIG8_HOMFLY, sl_n=3)
        self.assertAlmostEqual(result["real"], ki.real, places=5)
        self.assertAlmostEqual(result["imag"], ki.imag, places=5)

    def test_sl3_cinquefoil_matches_knotinfo(self):
        """sl_3 cinquefoil matches KnotInfo at (v=q^3, z=q-q^{-1})."""
        result = quantum_engine.evaluate_homfly_sln(CINQ_BRAID, sl_n=3)
        ki = _knotinfo_at_sln(CINQ_HOMFLY, sl_n=3)
        self.assertAlmostEqual(result["real"], ki.real, places=5)
        self.assertAlmostEqual(result["imag"], ki.imag, places=5)

    def test_sl2_and_sl3_differ_for_trefoil(self):
        """sl_2 and sl_3 evaluations are different — new information from sl_3."""
        r2 = quantum_engine.evaluate_homfly_sln(TREFOIL_BRAID, sl_n=2)
        r3 = quantum_engine.evaluate_homfly_sln(TREFOIL_BRAID, sl_n=3)
        diff = abs(complex(r2["real"], r2["imag"]) - complex(r3["real"], r3["imag"]))
        self.assertGreater(diff, 1e-4,
            "sl_2 and sl_3 must give different HOMFLY values for the trefoil")

    def test_fig8_is_amphichiral_sl3_value_is_real(self):
        """Figure-eight is amphichiral: sl_3 HOMFLY should be real (imag ~ 0)."""
        result = quantum_engine.evaluate_homfly_sln(FIG8_BRAID, sl_n=3)
        self.assertAlmostEqual(result["imag"], 0.0, places=5,
            msg="Figure-eight sl_3 HOMFLY must be real (amphichiral knot)")

    def test_distinguishes_trefoil_and_fig8_sl3(self):
        """sl_3 distinguishes trefoil from figure-eight."""
        t = quantum_engine.evaluate_homfly_sln(TREFOIL_BRAID, sl_n=3)
        f = quantum_engine.evaluate_homfly_sln(FIG8_BRAID, sl_n=3)
        diff = abs(complex(t["real"], t["imag"]) - complex(f["real"], f["imag"]))
        self.assertGreater(diff, 1e-4)


# ---------------------------------------------------------------------------
# Quantum circuit tests
# ---------------------------------------------------------------------------

class Sl3CircuitTests(unittest.TestCase):

    def test_circuit_builds_without_error(self):
        qc = quantum_engine.build_sl3_hadamard_circuit(TREFOIL_BRAID)
        self.assertIsNotNone(qc)

    def test_circuit_qubit_count_for_3_strand(self):
        """3-strand braid: 2*3 data qubits + 1 ancilla = 7 qubits."""
        qc = quantum_engine.build_sl3_hadamard_circuit(TREFOIL_BRAID)
        self.assertEqual(qc.num_qubits, 7)

    def test_circuit_has_one_classical_bit(self):
        qc = quantum_engine.build_sl3_hadamard_circuit(TREFOIL_BRAID)
        self.assertEqual(qc.num_clbits, 1)

    def test_circuit_fig8_builds(self):
        qc = quantum_engine.build_sl3_hadamard_circuit(FIG8_BRAID)
        self.assertIsNotNone(qc)

    def test_circuit_has_measure(self):
        qc = quantum_engine.build_sl3_hadamard_circuit(TREFOIL_BRAID)
        op_names = [inst.operation.name for inst in qc.data]
        self.assertIn("measure", op_names)

    def test_circuit_has_hadamard(self):
        qc = quantum_engine.build_sl3_hadamard_circuit(TREFOIL_BRAID)
        op_names = [inst.operation.name for inst in qc.data]
        self.assertIn("h", op_names)


if __name__ == "__main__":
    unittest.main()
