import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import quantum_engine

try:
    from fastapi.testclient import TestClient
    import main as backend_main
    _TEST_IMPORT_ERROR = None
except ModuleNotFoundError as exc:
    TestClient = None  # type: ignore[assignment]
    backend_main = None
    _TEST_IMPORT_ERROR = exc


TREFOIL_BRAID = "s1 s2^-1 s1 s2^-1"
FIGURE_EIGHT_BRAID = "s1 s2^-1 s1 s2 s1^-1 s2"


class SimulatorEngineSubmitTests(unittest.TestCase):
    """Tests for run_simulator_experiment() return value and side effects."""

    def setUp(self):
        quantum_engine._simulator_result_store.clear()

    def tearDown(self):
        quantum_engine._simulator_result_store.clear()

    def test_returns_submitted_status(self):
        result = quantum_engine.run_simulator_experiment(TREFOIL_BRAID, shots=256)
        self.assertEqual(result["status"], "SUBMITTED")

    def test_job_id_has_sim_prefix(self):
        result = quantum_engine.run_simulator_experiment(TREFOIL_BRAID, shots=256)
        self.assertTrue(result["job_id"].startswith(quantum_engine._SIM_JOB_ID_PREFIX))

    def test_backend_name_is_qiskit_simulator(self):
        result = quantum_engine.run_simulator_experiment(TREFOIL_BRAID, shots=256)
        self.assertEqual(result["backend"], quantum_engine.SIMULATOR_BACKEND_NAME)

    def test_no_ibm_credentials_in_submit_response(self):
        result = quantum_engine.run_simulator_experiment(TREFOIL_BRAID, shots=256)
        self.assertIsNone(result["runtime_channel_used"])
        self.assertIsNone(result["runtime_instance_used"])

    def test_includes_closure_method(self):
        result = quantum_engine.run_simulator_experiment(
            TREFOIL_BRAID, shots=256, closure_method="plat"
        )
        self.assertEqual(result["closure_method"], "plat")

    def test_includes_circuit_summary_with_expected_keys(self):
        result = quantum_engine.run_simulator_experiment(TREFOIL_BRAID, shots=256)
        summary = result["circuit_summary"]
        for key in ("depth", "size", "width", "num_qubits", "num_clbits",
                    "two_qubit_gate_count", "measurement_count", "operation_counts", "signature"):
            self.assertIn(key, summary)

    def test_circuit_summary_qubit_count_matches_braid(self):
        # Trefoil uses s1, s2 → strand_count=3 → 3+1=4 qubits
        result = quantum_engine.run_simulator_experiment(TREFOIL_BRAID, shots=256)
        self.assertGreaterEqual(result["circuit_summary"]["num_qubits"], 4)

    def test_stores_result_in_result_store(self):
        result = quantum_engine.run_simulator_experiment(TREFOIL_BRAID, shots=256)
        self.assertIn(result["job_id"], quantum_engine._simulator_result_store)

    def test_each_run_produces_unique_job_id(self):
        first = quantum_engine.run_simulator_experiment(TREFOIL_BRAID, shots=128)
        second = quantum_engine.run_simulator_experiment(TREFOIL_BRAID, shots=128)
        self.assertNotEqual(first["job_id"], second["job_id"])

    def test_rejects_braid_with_only_one_generator_type(self):
        with self.assertRaises(ValueError):
            quantum_engine.run_simulator_experiment("s1 s1 s1", shots=256)

    def test_rejects_braid_with_fewer_than_three_tokens(self):
        with self.assertRaises(ValueError):
            quantum_engine.run_simulator_experiment("s1 s2", shots=256)

    def test_rejects_invalid_closure_method(self):
        with self.assertRaises(ValueError):
            quantum_engine.run_simulator_experiment(
                TREFOIL_BRAID, shots=256, closure_method="invalid"
            )

    def test_works_with_trace_closure(self):
        result = quantum_engine.run_simulator_experiment(
            TREFOIL_BRAID, shots=256, closure_method="trace"
        )
        self.assertEqual(result["status"], "SUBMITTED")

    def test_works_with_plat_closure(self):
        result = quantum_engine.run_simulator_experiment(
            TREFOIL_BRAID, shots=256, closure_method="plat"
        )
        self.assertEqual(result["status"], "SUBMITTED")

    def test_works_with_figure_eight_braid(self):
        result = quantum_engine.run_simulator_experiment(FIGURE_EIGHT_BRAID, shots=256)
        self.assertEqual(result["status"], "SUBMITTED")


class SimulatorEngineResultTests(unittest.TestCase):
    """Tests for get_simulator_result() retrieval and result structure."""

    def setUp(self):
        quantum_engine._simulator_result_store.clear()

    def tearDown(self):
        quantum_engine._simulator_result_store.clear()

    def _submit_and_get(self, braid_word=TREFOIL_BRAID, shots=512, **kwargs):
        submit = quantum_engine.run_simulator_experiment(braid_word, shots=shots, **kwargs)
        return quantum_engine.get_simulator_result(submit["job_id"]), submit["job_id"]

    def test_retrieved_result_has_completed_status(self):
        result, _ = self._submit_and_get()
        self.assertEqual(result["status"], "COMPLETED")

    def test_retrieved_job_id_matches_submitted_job_id(self):
        result, job_id = self._submit_and_get()
        self.assertEqual(result["job_id"], job_id)

    def test_retrieved_backend_is_qiskit_simulator(self):
        result, _ = self._submit_and_get()
        self.assertEqual(result["backend"], quantum_engine.SIMULATOR_BACKEND_NAME)

    def test_retrieved_result_has_no_ibm_credentials(self):
        result, _ = self._submit_and_get()
        self.assertIsNone(result["runtime_channel_used"])
        self.assertIsNone(result["runtime_instance_used"])

    def test_counts_is_non_empty_list(self):
        result, _ = self._submit_and_get()
        self.assertIsInstance(result["counts"], list)
        self.assertGreater(len(result["counts"]), 0)

    def test_count_entries_have_name_and_probability(self):
        result, _ = self._submit_and_get()
        for entry in result["counts"]:
            self.assertIn("name", entry)
            self.assertIn("probability", entry)

    def test_probabilities_sum_to_one(self):
        result, _ = self._submit_and_get(shots=1024)
        total = sum(item["probability"] for item in result["counts"])
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_expectation_value_is_float_in_valid_range(self):
        result, _ = self._submit_and_get()
        ev = result["expectation_value"]
        self.assertIsInstance(ev, float)
        self.assertGreaterEqual(ev, -1.0)
        self.assertLessEqual(ev, 1.0)

    def test_jones_polynomial_has_expected_format(self):
        result, _ = self._submit_and_get()
        poly = result["jones_polynomial"]
        self.assertIsInstance(poly, str)
        self.assertTrue(poly.startswith("V(t) ="))

    def test_raises_for_unknown_job_id(self):
        with self.assertRaises(ValueError) as ctx:
            quantum_engine.get_simulator_result("sim-doesnotexist")
        self.assertIn("sim-doesnotexist", str(ctx.exception))

    def test_raises_for_non_sim_job_id(self):
        with self.assertRaises(ValueError):
            quantum_engine.get_simulator_result("ibm-real-job-abc")

    def test_figure_eight_produces_completed_result(self):
        result, _ = self._submit_and_get(braid_word=FIGURE_EIGHT_BRAID)
        self.assertEqual(result["status"], "COMPLETED")
        self.assertGreater(len(result["counts"]), 0)

    def test_plat_closure_produces_completed_result(self):
        result, _ = self._submit_and_get(closure_method="plat")
        self.assertEqual(result["status"], "COMPLETED")

    def test_multiple_jobs_stored_independently(self):
        s1 = quantum_engine.run_simulator_experiment(TREFOIL_BRAID, shots=128)
        s2 = quantum_engine.run_simulator_experiment(FIGURE_EIGHT_BRAID, shots=128)
        r1 = quantum_engine.get_simulator_result(s1["job_id"])
        r2 = quantum_engine.get_simulator_result(s2["job_id"])
        self.assertEqual(r1["job_id"], s1["job_id"])
        self.assertEqual(r2["job_id"], s2["job_id"])
        self.assertNotEqual(r1["job_id"], r2["job_id"])


@unittest.skipIf(
    _TEST_IMPORT_ERROR is not None,
    f"FastAPI backend test dependencies unavailable: {_TEST_IMPORT_ERROR}",
)
class SimulatorApiRouteTests(unittest.TestCase):
    """HTTP-level tests for the simulator routing in submit and poll endpoints."""

    def setUp(self):
        quantum_engine._simulator_result_store.clear()

    def tearDown(self):
        quantum_engine._simulator_result_store.clear()

    # --- submit routing ---

    def test_submit_with_simulator_backend_returns_200_without_ibm_token(self):
        client = TestClient(backend_main.app)
        with patch.dict(os.environ, {}, clear=True):
            response = client.post(
                "/api/jobs/submit",
                json={
                    "backend_name": "qiskit_simulator",
                    "braid_word": TREFOIL_BRAID,
                    "shots": 256,
                    "optimization_level": 1,
                    "closure_method": "trace",
                },
            )
        self.assertEqual(response.status_code, 200)

    def test_submit_with_simulator_backend_returns_submitted_status(self):
        client = TestClient(backend_main.app)
        with patch.dict(os.environ, {}, clear=True):
            response = client.post(
                "/api/jobs/submit",
                json={
                    "backend_name": "qiskit_simulator",
                    "braid_word": TREFOIL_BRAID,
                    "shots": 256,
                },
            )
        body = response.json()
        self.assertEqual(body["status"], "SUBMITTED")
        self.assertEqual(body["backend"], "qiskit_simulator")
        self.assertTrue(body["job_id"].startswith("sim-"))

    def test_submit_with_simulator_routes_to_run_simulator_experiment(self):
        client = TestClient(backend_main.app)
        sim_response = {
            "job_id": "sim-mocked001",
            "backend": "qiskit_simulator",
            "runtime_channel_used": None,
            "runtime_instance_used": None,
            "closure_method": "trace",
            "circuit_summary": {
                "depth": 5, "size": 5, "width": 4, "num_qubits": 3, "num_clbits": 1,
                "two_qubit_gate_count": 2, "measurement_count": 1,
                "operation_counts": {}, "signature": "abc",
            },
            "status": "SUBMITTED",
        }
        run_in_threadpool_mock = AsyncMock(return_value=sim_response)

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(backend_main, "run_in_threadpool", run_in_threadpool_mock):
                client.post(
                    "/api/jobs/submit",
                    json={
                        "backend_name": "qiskit_simulator",
                        "braid_word": TREFOIL_BRAID,
                        "shots": 256,
                    },
                )

        args = run_in_threadpool_mock.await_args.args
        self.assertIs(args[0], backend_main.run_simulator_experiment)
        self.assertIsNot(args[0], backend_main.submit_knot_experiment)

    def test_submit_with_simulator_passes_correct_arguments(self):
        client = TestClient(backend_main.app)
        run_in_threadpool_mock = AsyncMock(return_value={
            "job_id": "sim-args001", "backend": "qiskit_simulator",
            "runtime_channel_used": None, "runtime_instance_used": None,
            "closure_method": "plat", "circuit_summary": {
                "depth": 5, "size": 5, "width": 4, "num_qubits": 3, "num_clbits": 1,
                "two_qubit_gate_count": 2, "measurement_count": 1,
                "operation_counts": {}, "signature": "abc",
            }, "status": "SUBMITTED",
        })

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(backend_main, "run_in_threadpool", run_in_threadpool_mock):
                client.post(
                    "/api/jobs/submit",
                    json={
                        "backend_name": "qiskit_simulator",
                        "braid_word": TREFOIL_BRAID,
                        "shots": 512,
                        "optimization_level": 2,
                        "closure_method": "plat",
                    },
                )

        args = run_in_threadpool_mock.await_args.args
        self.assertEqual(args[1:], (TREFOIL_BRAID, 512, 2, "plat"))

    # --- poll routing ---

    def test_poll_with_sim_job_id_returns_200_without_ibm_token(self):
        client = TestClient(backend_main.app)
        # Seed the store directly so we can poll without a real submit round-trip
        job_id = "sim-directseed1"
        quantum_engine._simulator_result_store[job_id] = {
            "job_id": job_id, "backend": "qiskit_simulator",
            "runtime_channel_used": None, "runtime_instance_used": None,
            "counts": [{"name": "0", "probability": 1.0}],
            "expectation_value": 1.0,
            "jones_polynomial": "V(t) = 1.000t^-4 + t^-3 + t^-1",
            "status": "COMPLETED",
        }

        with patch.dict(os.environ, {}, clear=True):
            response = client.post("/api/jobs/poll", json={"job_id": job_id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "COMPLETED")

    def test_poll_with_sim_job_id_routes_to_get_simulator_result(self):
        client = TestClient(backend_main.app)
        completed_response = {
            "job_id": "sim-mocked002",
            "backend": "qiskit_simulator",
            "runtime_channel_used": None,
            "runtime_instance_used": None,
            "counts": [{"name": "0", "probability": 0.7}, {"name": "1", "probability": 0.3}],
            "expectation_value": 0.4,
            "jones_polynomial": "V(t) = 0.400t^-4 + t^-3 + t^-1",
            "status": "COMPLETED",
        }
        run_in_threadpool_mock = AsyncMock(return_value=completed_response)

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(backend_main, "run_in_threadpool", run_in_threadpool_mock):
                client.post("/api/jobs/poll", json={"job_id": "sim-mocked002"})

        args = run_in_threadpool_mock.await_args.args
        self.assertIs(args[0], backend_main.get_simulator_result)
        self.assertIsNot(args[0], backend_main.poll_knot_experiment_result)
        self.assertEqual(args[1], "sim-mocked002")

    def test_poll_unknown_sim_job_id_returns_422(self):
        client = TestClient(backend_main.app)
        with patch.dict(os.environ, {}, clear=True):
            response = client.post(
                "/api/jobs/poll", json={"job_id": "sim-doesnotexist"}
            )
        self.assertEqual(response.status_code, 422)

    # --- regression: IBM paths still require token ---

    def test_submit_with_ibm_backend_still_requires_token(self):
        client = TestClient(backend_main.app)
        with patch.dict(os.environ, {}, clear=True):
            response = client.post(
                "/api/jobs/submit",
                json={
                    "backend_name": "ibm_kyiv",
                    "braid_word": TREFOIL_BRAID,
                    "shots": 1024,
                },
            )
        self.assertEqual(response.status_code, 500)
        self.assertIn("IBM_QUANTUM_TOKEN", response.json()["detail"])

    def test_poll_with_ibm_job_id_still_requires_token(self):
        client = TestClient(backend_main.app)
        with patch.dict(os.environ, {}, clear=True):
            response = client.post(
                "/api/jobs/poll",
                json={"job_id": "ibm-real-job-12345"},
            )
        self.assertEqual(response.status_code, 500)
        self.assertIn("IBM_QUANTUM_TOKEN", response.json()["detail"])

    # --- full HTTP cycle ---

    def test_full_submit_then_poll_cycle(self):
        client = TestClient(backend_main.app)

        with patch.dict(os.environ, {}, clear=True):
            submit_resp = client.post(
                "/api/jobs/submit",
                json={
                    "backend_name": "qiskit_simulator",
                    "braid_word": TREFOIL_BRAID,
                    "shots": 512,
                    "optimization_level": 1,
                    "closure_method": "trace",
                },
            )
        self.assertEqual(submit_resp.status_code, 200)
        submit_body = submit_resp.json()
        self.assertEqual(submit_body["status"], "SUBMITTED")
        job_id = submit_body["job_id"]

        with patch.dict(os.environ, {}, clear=True):
            poll_resp = client.post("/api/jobs/poll", json={"job_id": job_id})
        self.assertEqual(poll_resp.status_code, 200)
        poll_body = poll_resp.json()

        self.assertEqual(poll_body["status"], "COMPLETED")
        self.assertEqual(poll_body["job_id"], job_id)
        self.assertEqual(poll_body["backend"], "qiskit_simulator")
        self.assertIsNone(poll_body["runtime_channel_used"])
        self.assertIsNone(poll_body["runtime_instance_used"])
        self.assertIn("jones_polynomial", poll_body)
        self.assertIsInstance(poll_body["expectation_value"], float)
        total_prob = sum(item["probability"] for item in poll_body["counts"])
        self.assertAlmostEqual(total_prob, 1.0, places=5)


if __name__ == "__main__":
    unittest.main()
