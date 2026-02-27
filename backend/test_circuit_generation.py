import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parent))

import quantum_engine


class _FakeTranspiledCircuit:
    def __init__(self, *, depth, size, width, num_qubits, num_clbits, operation_counts):
        self._depth = depth
        self._size = size
        self._width = width
        self.num_qubits = num_qubits
        self.num_clbits = num_clbits
        self._operation_counts = operation_counts

    def depth(self):
        return self._depth

    def size(self):
        return self._size

    def width(self):
        return self._width

    def count_ops(self):
        return self._operation_counts


class CircuitGenerationArtifactTests(unittest.TestCase):
    def _generate(self, *, closure_method: str):
        def fake_build_knot_circuit(*, braid_word, closure_method):
            return {
                "braid_word": braid_word,
                "closure_method": closure_method,
            }

        def fake_transpile(logical_circuit, optimization_level):
            if logical_circuit["closure_method"] == "trace":
                return _FakeTranspiledCircuit(
                    depth=12,
                    size=20,
                    width=4,
                    num_qubits=3,
                    num_clbits=1,
                    operation_counts={"cx": 4, "cp": 2, "h": 2, "measure": 1},
                )
            return _FakeTranspiledCircuit(
                depth=14,
                size=22,
                width=4,
                num_qubits=3,
                num_clbits=1,
                operation_counts={"cx": 5, "cp": 2, "h": 2, "sdg": 1, "measure": 1},
            )

        fake_qiskit = types.SimpleNamespace(transpile=fake_transpile)

        with patch.dict(sys.modules, {"qiskit": fake_qiskit}):
            with patch.object(quantum_engine, "build_knot_circuit", side_effect=fake_build_knot_circuit):
                return quantum_engine.generate_knot_circuit_artifact(
                    braid_word="s1 s2^-1 s1 s2^-1",
                    optimization_level=2,
                    closure_method=closure_method,
                    target_backend="ibm_kyiv",
                )

    def test_generates_circuit_summary_for_valid_braid(self):
        result = self._generate(closure_method="trace")

        self.assertEqual(result["target_backend"], "ibm_kyiv")
        self.assertEqual(result["optimization_level"], 2)
        self.assertEqual(result["closure_method"], "trace")
        self.assertEqual(result["braid_word"], "s1 s2^-1 s1 s2^-1")

        summary = result["circuit_summary"]
        self.assertEqual(summary["depth"], 12)
        self.assertEqual(summary["size"], 20)
        self.assertEqual(summary["width"], 4)
        self.assertEqual(summary["num_qubits"], 3)
        self.assertEqual(summary["num_clbits"], 1)
        self.assertEqual(summary["two_qubit_gate_count"], 6)
        self.assertEqual(summary["measurement_count"], 1)
        self.assertEqual(summary["operation_counts"]["cx"], 4)
        self.assertIsInstance(summary["signature"], str)
        self.assertEqual(len(summary["signature"]), 16)

    def test_closure_method_changes_circuit_signature(self):
        trace_result = self._generate(closure_method="trace")
        plat_result = self._generate(closure_method="plat")

        self.assertNotEqual(
            trace_result["circuit_summary"]["signature"],
            plat_result["circuit_summary"]["signature"],
        )

    def test_rejects_invalid_closure_method(self):
        with self.assertRaisesRegex(ValueError, "Closure method must be either 'trace' or 'plat'"):
            quantum_engine.generate_knot_circuit_artifact(
                braid_word="s1 s2^-1 s1",
                optimization_level=2,
                closure_method="invalid",
                target_backend="ibm_kyiv",
            )

    def test_rejects_non_contiguous_braid_word(self):
        with self.assertRaisesRegex(ValueError, "Missing: s2"):
            quantum_engine.generate_knot_circuit_artifact(
                braid_word="s1 s3 s1",
                optimization_level=2,
                closure_method="trace",
                target_backend="ibm_kyiv",
            )


if __name__ == "__main__":
    unittest.main()
