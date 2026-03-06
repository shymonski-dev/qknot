"""Phase 10a: Hecke algebra HOMFLY-PT evaluation tests.

Tests the classical Ocneanu-trace computation on H_n(q) permutation basis.
Cross-checks against KnotInfo stored HOMFLY-PT strings.
"""
import cmath
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import quantum_engine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _knotinfo_homfly_at(v_val, z_val=1.0):
    """Return a (v, z) evaluator for KnotInfo HOMFLY strings."""
    def evaluate(homfly_str):
        return quantum_engine._evaluate_homfly_string(homfly_str, v_val, z_val)
    return evaluate


def _our_homfly_complex(braid_word, root_of_unity=5):
    result = quantum_engine.evaluate_homfly_at_q(braid_word, root_of_unity)
    return complex(result["real"], result["imag"])


def _v_val(root_of_unity):
    return cmath.exp(1j * cmath.pi / root_of_unity)


# ---------------------------------------------------------------------------
# Hecke algebra internals
# ---------------------------------------------------------------------------

class HeckeInternalsTests(unittest.TestCase):
    def _q_z(self, k=5):
        v = _v_val(k)
        return v ** 2, v

    def test_right_multiply_identity_by_Ti_increases_length(self):
        """T_e * T_0 = T_{s0} (length increases)."""
        q, z = self._q_z()
        identity = (0, 1)
        elem = {identity: complex(1)}
        result = quantum_engine._hecke_right_multiply(elem, 0, False, q, z)
        self.assertIn((1, 0), result)
        self.assertAlmostEqual(abs(result[(1, 0)]), 1.0, places=12)

    def test_right_multiply_descent_applies_hecke_relation(self):
        """T_{s0} * T_0 = z*T_{s0} + q*T_e (length decreases)."""
        q, z = self._q_z()
        elem = {(1, 0): complex(1)}
        result = quantum_engine._hecke_right_multiply(elem, 0, False, q, z)
        self.assertIn((1, 0), result)
        self.assertIn((0, 1), result)
        self.assertAlmostEqual(abs(result[(1, 0)] - z), 0, places=12)
        self.assertAlmostEqual(abs(result[(0, 1)] - q), 0, places=12)

    def test_right_multiply_inverse_long_to_short(self):
        """T_{s0} * T_0^{-1} = T_e (length decreases: inverse reverts)."""
        q, z = self._q_z()
        elem = {(1, 0): complex(1)}
        result = quantum_engine._hecke_right_multiply(elem, 0, True, q, z)
        self.assertIn((0, 1), result)
        self.assertAlmostEqual(abs(result[(0, 1)]), 1.0, places=12)

    def test_trace_identity_H2(self):
        """tr_2(T_e) = (1-q)/z."""
        q, z = self._q_z()
        val = quantum_engine._hecke_trace_basis((0, 1), q, z)
        expected = (1 - q) / z
        self.assertAlmostEqual(val.real, expected.real, places=10)
        self.assertAlmostEqual(val.imag, expected.imag, places=10)

    def test_trace_s0_H2(self):
        """tr_2(T_{s0}) = 1."""
        q, z = self._q_z()
        val = quantum_engine._hecke_trace_basis((1, 0), q, z)
        self.assertAlmostEqual(val.real, 1.0, places=10)
        self.assertAlmostEqual(val.imag, 0.0, places=10)

    def test_trace_long_element_H3(self):
        """tr_3(T_{long}) = (z^2 + q - q^2)/z."""
        q, z = self._q_z()
        # long element of S_3: (2,1,0)
        val = quantum_engine._hecke_trace_basis((2, 1, 0), q, z)
        expected = (z ** 2 + q - q ** 2) / z
        self.assertAlmostEqual(val.real, expected.real, places=10)
        self.assertAlmostEqual(val.imag, expected.imag, places=10)

    def test_build_hecke_context_fields(self):
        q, z = self._q_z()
        ctx = quantum_engine._build_hecke_context(3, q, z)
        self.assertEqual(ctx["strand_count"], 3)
        self.assertEqual(ctx["identity"], (0, 1, 2))
        self.assertAlmostEqual(abs(ctx["q"] - q), 0, places=12)

    def test_compute_hecke_generator_matrix_out_of_range(self):
        q, z = self._q_z()
        ctx = quantum_engine._build_hecke_context(2, q, z)
        with self.assertRaises(ValueError):
            quantum_engine._compute_hecke_generator_matrix(ctx, 2, False)


# ---------------------------------------------------------------------------
# HOMFLY-PT evaluation
# ---------------------------------------------------------------------------

class HomflyEvaluationTests(unittest.TestCase):
    def test_returns_dict_with_required_fields(self):
        result = quantum_engine.evaluate_homfly_at_q("s1 s2 s1 s2")
        for field in ("real", "imag", "v_val_real", "v_val_imag", "z_homfly",
                      "q_hecke_real", "q_hecke_imag", "root_of_unity"):
            self.assertIn(field, result)

    def test_returns_complex_value(self):
        result = quantum_engine.evaluate_homfly_at_q("s1 s2 s1 s2")
        val = complex(result["real"], result["imag"])
        self.assertIsInstance(val, complex)

    def test_is_deterministic(self):
        a = quantum_engine.evaluate_homfly_at_q("s1 s2 s1 s2")
        b = quantum_engine.evaluate_homfly_at_q("s1 s2 s1 s2")
        self.assertAlmostEqual(a["real"], b["real"], places=12)
        self.assertAlmostEqual(a["imag"], b["imag"], places=12)

    def test_distinguishes_trefoil_and_figure_eight(self):
        trefoil = _our_homfly_complex("s1 s2 s1 s2")
        fig8 = _our_homfly_complex("s1 s2^-1 s1 s2^-1")
        self.assertGreater(abs(trefoil - fig8), 1e-6)

    def test_trefoil_matches_knotinfo_homfly_string(self):
        """Our trace at (v, z=1) must equal KnotInfo polynomial at same (v, z=1)."""
        k = 5
        v = _v_val(k)
        braid = "s1 s2 s1 s2"
        homfly_str = "(2*v^2-v^4)+(v^2)*z^2"
        our_val = _our_homfly_complex(braid, k)
        ki_val = quantum_engine._evaluate_homfly_string(homfly_str, v, complex(1))
        self.assertAlmostEqual(our_val.real, ki_val.real, places=5,
            msg="Trefoil HOMFLY real part must match KnotInfo string")
        self.assertAlmostEqual(our_val.imag, ki_val.imag, places=5,
            msg="Trefoil HOMFLY imag part must match KnotInfo string")

    def test_figure_eight_matches_knotinfo_homfly_string(self):
        """Figure-eight HOMFLY at (v, z=1) matches KnotInfo string."""
        k = 5
        v = _v_val(k)
        braid = "s1 s2^-1 s1 s2^-1"
        homfly_str = "(v^(-2)-1+v^2)+(-1)*z^2"
        our_val = _our_homfly_complex(braid, k)
        ki_val = quantum_engine._evaluate_homfly_string(homfly_str, v, complex(1))
        self.assertAlmostEqual(our_val.real, ki_val.real, places=5,
            msg="Figure-eight HOMFLY real part must match KnotInfo string")
        self.assertAlmostEqual(our_val.imag, ki_val.imag, places=5,
            msg="Figure-eight HOMFLY imag part must match KnotInfo string")

    def test_cinquefoil_matches_knotinfo_homfly_string(self):
        """Cinquefoil HOMFLY at (v, z=1) matches KnotInfo string."""
        k = 5
        v = _v_val(k)
        braid = "s1 s1 s1 s1 s1 s2"
        homfly_str = "(3*v^4-2*v^6)+(4*v^4-v^6)*z^2+(v^4)*z^4"
        our_val = _our_homfly_complex(braid, k)
        ki_val = quantum_engine._evaluate_homfly_string(homfly_str, v, complex(1))
        self.assertAlmostEqual(our_val.real, ki_val.real, places=5,
            msg="Cinquefoil HOMFLY real part must match KnotInfo string")
        self.assertAlmostEqual(our_val.imag, ki_val.imag, places=5,
            msg="Cinquefoil HOMFLY imag part must match KnotInfo string")

    def test_evaluate_homfly_string_unknot_constant(self):
        """Unknot HOMFLY = 1 (trivially, by convention)."""
        v = _v_val(5)
        val = quantum_engine._evaluate_homfly_string("1", v, complex(1))
        self.assertAlmostEqual(val.real, 1.0, places=12)

    def test_evaluate_homfly_string_trefoil_numeric(self):
        """KnotInfo string evaluator gives known numeric for trefoil at v=2, z=1."""
        val = quantum_engine._evaluate_homfly_string("(2*v^2-v^4)+(v^2)*z^2", 2.0, 1.0)
        # -16 + 8 + 4*1 = -4
        self.assertAlmostEqual(val.real, -4.0, places=10)

    def test_knotinfo_catalog_homfly_strings_are_parseable(self):
        """All hardcoded catalog HOMFLY strings must be numerically evaluable."""
        v = _v_val(5)
        for entry in quantum_engine._DOWKER_BRAID_CATALOG.values():
            homfly_str = entry.get("homfly_pt")
            if homfly_str:
                val = quantum_engine._evaluate_homfly_string(homfly_str, v, complex(1))
                self.assertIsInstance(val, complex)


if __name__ == "__main__":
    unittest.main()
