import sys
import unittest
from pathlib import Path

try:
    import numpy as np
except ModuleNotFoundError:
    np = None


sys.path.insert(0, str(Path(__file__).resolve().parent))

import quantum_engine


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


if __name__ == "__main__":
    unittest.main()
