import sys
import unittest
from pathlib import Path

try:
    import numpy as np
except ModuleNotFoundError:
    np = None


sys.path.insert(0, str(Path(__file__).resolve().parent))

import quantum_engine


class NumpyAvailabilityTest(unittest.TestCase):
    def test_numpy_is_importable(self):
        """Phase 8 gate: numpy must be present for AJL invariant evaluation."""
        try:
            import numpy  # noqa: F401
        except ModuleNotFoundError:
            self.fail("numpy is not installed — AJL invariant engine cannot run")


@unittest.skipIf(np is None, "numpy is required for Aharonov Jones Landau invariant tests")
class AharonovJonesLandauInvariantTests(unittest.TestCase):
    def test_returns_complex_value_for_valid_braid(self):
        value = quantum_engine.evaluate_jones_at_root_of_unity("s1 s2^-1 s1 s2^-1")
        self.assertIsInstance(value, complex)

    def test_is_deterministic_for_same_braid(self):
        first_value = quantum_engine.evaluate_jones_at_root_of_unity("s1 s2^-1 s1 s2^-1")
        second_value = quantum_engine.evaluate_jones_at_root_of_unity("s1 s2^-1 s1 s2^-1")
        self.assertAlmostEqual(first_value.real, second_value.real, places=12)
        self.assertAlmostEqual(first_value.imag, second_value.imag, places=12)

    def test_distinguishes_trefoil_and_figure_eight_braids(self):
        trefoil_value = quantum_engine.evaluate_jones_at_root_of_unity("s1 s2^-1 s1 s2^-1")
        figure_eight_value = quantum_engine.evaluate_jones_at_root_of_unity("s1 s2^-1 s1 s2 s1^-1 s2")
        self.assertGreater(abs(trefoil_value - figure_eight_value), 1e-8)

    def test_generator_matrix_is_unitary(self):
        context = quantum_engine._build_ajl_context(3, quantum_engine.DEFAULT_ROOT_OF_UNITY)
        matrix = quantum_engine._compute_generator_matrix(context, generator=1, is_inverse=False)
        identity = np.eye(matrix.shape[0], dtype=complex)
        self.assertTrue(np.allclose(matrix.conjugate().T @ matrix, identity, atol=1e-9))

    def test_output_formatter_reports_evaluation_point(self):
        value = quantum_engine.evaluate_jones_at_root_of_unity("s1 s2^-1 s1 s2^-1")
        text = quantum_engine._format_jones_output(value, quantum_engine.DEFAULT_ROOT_OF_UNITY)
        self.assertTrue(text.startswith("V(t) ="))
        self.assertIn("exp(2*pi*i/5)", text)

    def test_knotinfo_figure_eight_jones_value_matches_mathematical_value(self):
        """Phase 9a gate: KnotInfo figure-eight braid gives the known mathematical Jones value.

        V_{4_1}(exp(2πi/5)) = t^{-2} - t^{-1} + 1 - t + t^2 at t=exp(2πi/5) = -1.236068 + 0i.
        The figure-eight is amphichiral so its Jones polynomial is real at this root.
        """
        catalog = quantum_engine._load_knotinfo_catalog()
        entry = catalog.get((4, 6, 8, 2))
        self.assertIsNotNone(entry, "Figure-Eight (4,6,8,2) must be in KnotInfo catalog")

        v = quantum_engine.evaluate_jones_at_root_of_unity(entry["braid_word"])

        self.assertAlmostEqual(v.real, -1.2360679774997898, places=5,
            msg="KnotInfo figure-eight Jones real part must match mathematical value")
        self.assertAlmostEqual(v.imag, 0.0, places=5,
            msg="Figure-eight Jones value must be real (amphichiral knot)")


if __name__ == "__main__":
    unittest.main()
