import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import quantum_engine


class FoldGatesTests(unittest.TestCase):
    def _simple_circuit(self):
        from qiskit import QuantumCircuit
        qc = QuantumCircuit(2, 1)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure(0, 0)
        return qc

    def test_scale_factor_1_returns_same_gate_count(self):
        qc = self._simple_circuit()
        folded = quantum_engine._fold_gates(qc, scale_factor=1)
        self.assertEqual(len(folded.data), len(qc.data))

    def test_scale_factor_3_increases_gate_count(self):
        qc = self._simple_circuit()
        folded = quantum_engine._fold_gates(qc, scale_factor=3)
        # Each non-measure gate (H, CX = 2 gates) gains 2 extra ops → 2*2=4 extra + 1 measure = 7 total
        # Original: H, CX, measure = 3
        # Folded 3x: H, H†, H, CX, CX†, CX, measure = 7
        self.assertGreater(len(folded.data), len(qc.data))

    def test_scale_factor_5_increases_gate_count_more_than_3(self):
        qc = self._simple_circuit()
        folded_3 = quantum_engine._fold_gates(qc, scale_factor=3)
        folded_5 = quantum_engine._fold_gates(qc, scale_factor=5)
        self.assertGreater(len(folded_5.data), len(folded_3.data))

    def test_measurement_gates_are_not_folded(self):
        from qiskit import QuantumCircuit
        qc = QuantumCircuit(1, 1)
        qc.measure(0, 0)
        folded = quantum_engine._fold_gates(qc, scale_factor=3)
        # Measure-only circuit: no additional gates added
        self.assertEqual(len(folded.data), 1)


class RichardsonExtrapolateTests(unittest.TestCase):
    def test_constant_function_extrapolates_to_constant(self):
        result = quantum_engine._richardson_extrapolate([1.0, 3.0, 5.0], [0.7, 0.7, 0.7])
        self.assertAlmostEqual(result, 0.7, places=10)

    def test_linear_function_extrapolates_to_correct_zero(self):
        # f(x) = 0.8 - 0.1*x → f(1)=0.7, f(3)=0.5, f(5)=0.3, f(0)=0.8
        result = quantum_engine._richardson_extrapolate([1.0, 3.0, 5.0], [0.7, 0.5, 0.3])
        self.assertAlmostEqual(result, 0.8, places=10)

    def test_two_point_extrapolation_works(self):
        # f(x) = 0.6 - 0.1*x → f(0) = 0.6
        result = quantum_engine._richardson_extrapolate([1.0, 3.0], [0.5, 0.3])
        self.assertAlmostEqual(result, 0.6, places=10)


class ClassicalAncillaExpectationTests(unittest.TestCase):
    def test_returns_float_for_trefoil(self):
        value = quantum_engine._compute_classical_ancilla_expectation("s1 s2 s1 s2")
        self.assertIsInstance(value, float)

    def test_value_in_valid_hadamard_test_range(self):
        # Re(U[0,0]) for any unitary U must satisfy |Re(U[0,0])| <= 1
        value = quantum_engine._compute_classical_ancilla_expectation("s1 s2 s1 s2")
        self.assertGreaterEqual(value, -1.0)
        self.assertLessEqual(value, 1.0)

    def test_trefoil_and_figure_eight_differ(self):
        trefoil_ref = quantum_engine._compute_classical_ancilla_expectation("s1 s2 s1 s2")
        figure_eight_ref = quantum_engine._compute_classical_ancilla_expectation("s1 s2^-1 s1 s2^-1")
        self.assertNotAlmostEqual(trefoil_ref, figure_eight_ref, places=5)


if __name__ == "__main__":
    unittest.main()
