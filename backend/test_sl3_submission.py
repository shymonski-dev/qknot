"""Phase 10b: sl_3 hardware submission path tests.

Tests _compute_sl3_classical_reference, submit_sl3_experiment,
poll_sl3_experiment_result, and the /api/knot/sl3/submit and
/api/knot/sl3/poll API routes.
"""
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import numpy as np
    _HAS_NUMPY = True
except ModuleNotFoundError:
    _HAS_NUMPY = False

import quantum_engine

TREFOIL_BRAID = "s1 s2 s1 s2"
FIG8_BRAID = "s1 s2^-1 s1 s2^-1"


# ---------------------------------------------------------------------------
# Minimal IBM mock helpers (matches pattern from test_submit_poll_end_to_end)
# ---------------------------------------------------------------------------

class _CountsContainer:
    def __init__(self, counts):
        self._counts = counts

    def get_counts(self):
        return self._counts


class _PubResult:
    class Data:
        c = _CountsContainer({"0": 80, "1": 20})
    data = Data()


class _Backend:
    name = "ibm_fez"


class _StatusValue:
    def __init__(self, name: str):
        self.name = name


class _RuntimeJob:
    def __init__(self, *, job_id: str, status_sequence: list, backend=None, pub_result=None):
        self._job_id = job_id
        self._status_sequence = list(status_sequence)
        self._backend = backend or _Backend()
        self._pub_result = pub_result or _PubResult()
        self._call_count = 0

    def job_id(self):
        return self._job_id

    def status(self):
        idx = min(self._call_count, len(self._status_sequence) - 1)
        self._call_count += 1
        return _StatusValue(self._status_sequence[idx])

    def backend(self):
        return self._backend

    def result(self):
        return [self._pub_result]


class _RuntimeService:
    def __init__(self, job):
        self._job = job
        self.requested_job_ids = []

    def job(self, job_id):
        self.requested_job_ids.append(job_id)
        return self._job


# ---------------------------------------------------------------------------
# Classical reference tests
# ---------------------------------------------------------------------------

@unittest.skipIf(not _HAS_NUMPY, "numpy required")
class Sl3ClassicalReferenceTests(unittest.TestCase):

    def test_returns_float(self):
        val = quantum_engine._compute_sl3_classical_reference(TREFOIL_BRAID)
        self.assertIsInstance(val, float)

    def test_is_deterministic(self):
        a = quantum_engine._compute_sl3_classical_reference(TREFOIL_BRAID)
        b = quantum_engine._compute_sl3_classical_reference(TREFOIL_BRAID)
        self.assertAlmostEqual(a, b, places=12)

    def test_trefoil_and_fig8_differ(self):
        t = quantum_engine._compute_sl3_classical_reference(TREFOIL_BRAID)
        f = quantum_engine._compute_sl3_classical_reference(FIG8_BRAID)
        self.assertNotAlmostEqual(t, f, places=4,
            msg="Trefoil and figure-eight sl_3 references should differ")

    def test_bounded_between_minus_one_and_one(self):
        """Re(U'[0,0]) must lie in [-1, 1] since U' is built from a unitary."""
        val = quantum_engine._compute_sl3_classical_reference(TREFOIL_BRAID)
        self.assertGreaterEqual(val, -1.0 - 1e-9)
        self.assertLessEqual(val, 1.0 + 1e-9)

    def test_different_root_of_unity_gives_different_value(self):
        v5 = quantum_engine._compute_sl3_classical_reference(TREFOIL_BRAID, root_of_unity=5)
        v7 = quantum_engine._compute_sl3_classical_reference(TREFOIL_BRAID, root_of_unity=7)
        self.assertNotAlmostEqual(v5, v7, places=4)


# ---------------------------------------------------------------------------
# submit_sl3_experiment (mocked IBM)
# ---------------------------------------------------------------------------

@unittest.skipIf(not _HAS_NUMPY, "numpy required")
class Sl3SubmitTests(unittest.TestCase):

    def _make_mocks(self, job_id="sl3-test-001", status="SUBMITTED"):
        job = _RuntimeJob(job_id=job_id, status_sequence=[status])
        fake_qiskit_module = types.SimpleNamespace(
            QiskitRuntimeService=object,
            SamplerV2=object,
        )
        return job, fake_qiskit_module

    def test_submit_returns_required_fields(self):
        job, fake_module = self._make_mocks()
        with patch.dict(sys.modules, {"qiskit_ibm_runtime": fake_module}):
            with patch.object(quantum_engine, "create_runtime_service",
                              return_value=(_RuntimeService(job), "ibm_cloud")):
                with patch.object(quantum_engine, "select_backend",
                                  return_value=_Backend()):
                    with patch.object(quantum_engine, "create_sampler_for_backend",
                                      return_value=_make_mock_sampler(job)):
                        with patch("qiskit.transpile", return_value=_make_fake_transpiled()):
                            result = quantum_engine.submit_sl3_experiment(
                                token="tok",
                                backend_name="ibm_fez",
                                braid_word=TREFOIL_BRAID,
                                shots=512,
                            )
        for field in ("job_id", "backend", "status", "sl_n", "root_of_unity",
                      "braid_word", "circuit_qubits"):
            self.assertIn(field, result, f"Missing field: {field}")

    def test_submit_sl_n_is_3(self):
        job, fake_module = self._make_mocks()
        with patch.dict(sys.modules, {"qiskit_ibm_runtime": fake_module}):
            with patch.object(quantum_engine, "create_runtime_service",
                              return_value=(_RuntimeService(job), "ibm_cloud")):
                with patch.object(quantum_engine, "select_backend",
                                  return_value=_Backend()):
                    with patch.object(quantum_engine, "create_sampler_for_backend",
                                      return_value=_make_mock_sampler(job)):
                        with patch("qiskit.transpile", return_value=_make_fake_transpiled()):
                            result = quantum_engine.submit_sl3_experiment(
                                token="tok",
                                backend_name="ibm_fez",
                                braid_word=TREFOIL_BRAID,
                                shots=512,
                            )
        self.assertEqual(result["sl_n"], 3)

    def test_submit_stores_metadata(self):
        job, fake_module = self._make_mocks(job_id="sl3-meta-001")
        with patch.dict(sys.modules, {"qiskit_ibm_runtime": fake_module}):
            with patch.object(quantum_engine, "create_runtime_service",
                              return_value=(_RuntimeService(job), "ibm_cloud")):
                with patch.object(quantum_engine, "select_backend",
                                  return_value=_Backend()):
                    with patch.object(quantum_engine, "create_sampler_for_backend",
                                      return_value=_make_mock_sampler(job)):
                        with patch("qiskit.transpile", return_value=_make_fake_transpiled()):
                            quantum_engine.submit_sl3_experiment(
                                token="tok",
                                backend_name="ibm_fez",
                                braid_word=TREFOIL_BRAID,
                                shots=512,
                            )
        meta = quantum_engine._runtime_job_metadata_store.get("sl3-meta-001", {})
        self.assertEqual(meta.get("experiment_type"), "sl3")
        self.assertEqual(meta.get("braid_word"), TREFOIL_BRAID)

    def test_submit_braid_word_recorded_in_result(self):
        job, fake_module = self._make_mocks()
        with patch.dict(sys.modules, {"qiskit_ibm_runtime": fake_module}):
            with patch.object(quantum_engine, "create_runtime_service",
                              return_value=(_RuntimeService(job), "ibm_cloud")):
                with patch.object(quantum_engine, "select_backend",
                                  return_value=_Backend()):
                    with patch.object(quantum_engine, "create_sampler_for_backend",
                                      return_value=_make_mock_sampler(job)):
                        with patch("qiskit.transpile", return_value=_make_fake_transpiled()):
                            result = quantum_engine.submit_sl3_experiment(
                                token="tok",
                                backend_name="ibm_fez",
                                braid_word=TREFOIL_BRAID,
                                shots=512,
                            )
        self.assertEqual(result["braid_word"], TREFOIL_BRAID)


# ---------------------------------------------------------------------------
# poll_sl3_experiment_result (mocked IBM)
# ---------------------------------------------------------------------------

@unittest.skipIf(not _HAS_NUMPY, "numpy required")
class Sl3PollTests(unittest.TestCase):

    def _seed_metadata(self, job_id, braid_word=TREFOIL_BRAID, root_of_unity=5):
        quantum_engine._runtime_job_metadata_store[job_id] = {
            "experiment_type": "sl3",
            "sl_n": 3,
            "braid_word": braid_word,
            "root_of_unity": root_of_unity,
        }

    def test_running_poll_returns_in_progress_status(self):
        job = _RuntimeJob(job_id="sl3-poll-run", status_sequence=["RUNNING"])
        self._seed_metadata("sl3-poll-run")
        service = _RuntimeService(job)
        with patch.object(quantum_engine, "create_runtime_service",
                          return_value=(service, "ibm_cloud")):
            result = quantum_engine.poll_sl3_experiment_result(
                token="tok", job_id="sl3-poll-run"
            )
        self.assertEqual(result["status"], "RUNNING")
        self.assertNotIn("hadamard_expectation", result)

    def test_completed_poll_returns_expected_fields(self):
        job = _RuntimeJob(job_id="sl3-poll-done", status_sequence=["DONE"])
        self._seed_metadata("sl3-poll-done")
        service = _RuntimeService(job)
        with patch.object(quantum_engine, "create_runtime_service",
                          return_value=(service, "ibm_cloud")):
            result = quantum_engine.poll_sl3_experiment_result(
                token="tok", job_id="sl3-poll-done"
            )
        self.assertEqual(result["status"], "COMPLETED")
        for field in ("hadamard_expectation", "classical_reference", "deviation",
                      "counts", "sl_n", "root_of_unity", "braid_word"):
            self.assertIn(field, result, f"Missing field: {field}")

    def test_completed_poll_hadamard_expectation_in_range(self):
        """Counts 80:20 → expectation = (80-20)/100 = 0.6."""
        job = _RuntimeJob(job_id="sl3-poll-exp", status_sequence=["DONE"])
        self._seed_metadata("sl3-poll-exp")
        service = _RuntimeService(job)
        with patch.object(quantum_engine, "create_runtime_service",
                          return_value=(service, "ibm_cloud")):
            result = quantum_engine.poll_sl3_experiment_result(
                token="tok", job_id="sl3-poll-exp"
            )
        self.assertAlmostEqual(result["hadamard_expectation"], 0.6, places=5)

    def test_completed_poll_classical_reference_is_float(self):
        job = _RuntimeJob(job_id="sl3-poll-ref", status_sequence=["DONE"])
        self._seed_metadata("sl3-poll-ref")
        service = _RuntimeService(job)
        with patch.object(quantum_engine, "create_runtime_service",
                          return_value=(service, "ibm_cloud")):
            result = quantum_engine.poll_sl3_experiment_result(
                token="tok", job_id="sl3-poll-ref"
            )
        self.assertIsInstance(result["classical_reference"], float)

    def test_completed_poll_clears_metadata(self):
        job = _RuntimeJob(job_id="sl3-poll-clear", status_sequence=["DONE"])
        self._seed_metadata("sl3-poll-clear")
        service = _RuntimeService(job)
        with patch.object(quantum_engine, "create_runtime_service",
                          return_value=(service, "ibm_cloud")):
            quantum_engine.poll_sl3_experiment_result(
                token="tok", job_id="sl3-poll-clear"
            )
        self.assertNotIn("sl3-poll-clear", quantum_engine._runtime_job_metadata_store)

    def test_failed_poll_returns_error_status(self):
        job = _RuntimeJob(job_id="sl3-poll-fail", status_sequence=["ERROR"])
        self._seed_metadata("sl3-poll-fail")
        service = _RuntimeService(job)
        with patch.object(quantum_engine, "create_runtime_service",
                          return_value=(service, "ibm_cloud")):
            result = quantum_engine.poll_sl3_experiment_result(
                token="tok", job_id="sl3-poll-fail"
            )
        self.assertIn(result["status"], ("ERROR", "FAILED", "CANCELLED"))


# ---------------------------------------------------------------------------
# API route tests
# ---------------------------------------------------------------------------

class Sl3ApiRouteTests(unittest.TestCase):

    def _get_client(self):
        from fastapi.testclient import TestClient
        try:
            from backend.main import app
        except ImportError:
            from main import app
        return TestClient(app)

    def test_sl3_submit_requires_token(self):
        client = self._get_client()
        with patch.dict(os.environ, {}, clear=True):
            resp = client.post("/api/knot/sl3/submit", json={
                "backend_name": "ibm_fez",
                "braid_word": TREFOIL_BRAID,
                "shots": 128,
            })
        self.assertEqual(resp.status_code, 500)
        self.assertIn("IBM", resp.json()["detail"])

    def test_sl3_poll_requires_token(self):
        client = self._get_client()
        with patch.dict(os.environ, {}, clear=True):
            resp = client.post("/api/knot/sl3/poll", json={"job_id": "some-job-id"})
        self.assertEqual(resp.status_code, 500)
        self.assertIn("IBM", resp.json()["detail"])

    def test_sl3_submit_rejects_blank_braid(self):
        client = self._get_client()
        with patch.dict(os.environ, {"IBM_QUANTUM_TOKEN": "test-token"}):
            resp = client.post("/api/knot/sl3/submit", json={
                "backend_name": "ibm_fez",
                "braid_word": "   ",
                "shots": 128,
            })
        self.assertEqual(resp.status_code, 422)

    def test_sl3_submit_rejects_zero_shots(self):
        client = self._get_client()
        with patch.dict(os.environ, {"IBM_QUANTUM_TOKEN": "test-token"}):
            resp = client.post("/api/knot/sl3/submit", json={
                "backend_name": "ibm_fez",
                "braid_word": TREFOIL_BRAID,
                "shots": 0,
            })
        self.assertEqual(resp.status_code, 422)

    @unittest.skipIf(not _HAS_NUMPY, "numpy required")
    def test_sl3_submit_calls_submit_function(self):
        client = self._get_client()
        fake_result = {
            "job_id": "sl3-api-001",
            "backend": "ibm_fez",
            "status": "SUBMITTED",
            "sl_n": 3,
            "root_of_unity": 5,
            "braid_word": TREFOIL_BRAID,
            "circuit_qubits": 7,
            "runtime_channel_used": "ibm_cloud",
            "runtime_instance_used": None,
        }
        try:
            from backend import main as main_module
        except ImportError:
            import main as main_module
        with patch.dict(os.environ, {"IBM_QUANTUM_TOKEN": "test-token"}):
            with patch.object(main_module, "submit_sl3_experiment",
                              return_value=fake_result):
                resp = client.post("/api/knot/sl3/submit", json={
                    "backend_name": "ibm_fez",
                    "braid_word": TREFOIL_BRAID,
                    "shots": 128,
                })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["job_id"], "sl3-api-001")
        self.assertEqual(data["sl_n"], 3)

    @unittest.skipIf(not _HAS_NUMPY, "numpy required")
    def test_sl3_poll_calls_poll_function(self):
        client = self._get_client()
        fake_result = {
            "job_id": "sl3-api-001",
            "backend": "ibm_fez",
            "status": "COMPLETED",
            "sl_n": 3,
            "root_of_unity": 5,
            "braid_word": TREFOIL_BRAID,
            "counts": [],
            "hadamard_expectation": 0.6,
            "classical_reference": 0.55,
            "deviation": 0.05,
            "runtime_channel_used": "ibm_cloud",
            "runtime_instance_used": None,
        }
        try:
            from backend import main as main_module
        except ImportError:
            import main as main_module
        with patch.dict(os.environ, {"IBM_QUANTUM_TOKEN": "test-token"}):
            with patch.object(main_module, "poll_sl3_experiment_result",
                              return_value=fake_result):
                resp = client.post("/api/knot/sl3/poll",
                                   json={"job_id": "sl3-api-001"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "COMPLETED")
        self.assertIn("hadamard_expectation", data)


# ---------------------------------------------------------------------------
# Helpers for mocking transpile + sampler
# ---------------------------------------------------------------------------

def _make_fake_transpiled():
    """Minimal object with num_qubits that Sampler.run accepts."""
    class FakeTranspiled:
        num_qubits = 7
    return FakeTranspiled()


def _make_mock_sampler(job):
    class FakeSampler:
        def run(self, circuits, shots=None):
            return job
    return FakeSampler()


if __name__ == "__main__":
    unittest.main()
