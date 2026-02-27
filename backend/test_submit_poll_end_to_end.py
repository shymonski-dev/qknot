import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parent))

import quantum_engine


class _CountsContainer:
    def __init__(self, counts):
        self._counts = counts

    def get_counts(self):
        return self._counts


class _PubResult:
    class Data:
        c = _CountsContainer({"0": 7, "1": 3})

    data = Data()


class _Backend:
    name = "ibm_kyiv"


class _StatusValue:
    def __init__(self, name: str):
        self.name = name


class _RuntimeJob:
    def __init__(self, *, job_id: str, status_sequence: list[str], backend=None, pub_result=None):
        self._job_id = job_id
        self._status_sequence = list(status_sequence)
        self._backend = backend if backend is not None else _Backend()
        self._pub_result = pub_result or _PubResult()
        self._status_call_count = 0

    def job_id(self):
        return self._job_id

    def status(self):
        index = min(self._status_call_count, len(self._status_sequence) - 1)
        self._status_call_count += 1
        return _StatusValue(self._status_sequence[index])

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


class SubmitPollEndToEndTests(unittest.TestCase):
    def test_submit_then_poll_reaches_completed_state(self):
        job = _RuntimeJob(
            job_id="job-e2e-001",
            status_sequence=["QUEUED", "RUNNING", "DONE"],
        )
        service = _RuntimeService(job)
        fake_qiskit_module = types.SimpleNamespace(QiskitRuntimeService=object)
        expected_circuit_summary = {
            "depth": 8,
            "size": 8,
            "width": 6,
            "num_qubits": 5,
            "num_clbits": 1,
            "two_qubit_gate_count": 5,
            "measurement_count": 1,
            "operation_counts": {"cp": 5, "h": 2, "measure": 1},
            "signature": "endtoend001",
        }

        with patch.dict(sys.modules, {"qiskit_ibm_runtime": fake_qiskit_module}):
            with patch.object(
                quantum_engine,
                "_build_and_submit_knot_job",
                return_value=(job, _Backend(), "ibm_cloud", expected_circuit_summary),
            ) as build_submit_mock:
                submitted = quantum_engine.submit_knot_experiment(
                    token="token-123",
                    backend_name="ibm_kyiv",
                    braid_word="s1 s2^-1 s3 s2 s1^-1",
                    shots=1024,
                    optimization_level=2,
                    closure_method="trace",
                    runtime_channel="ibm_cloud",
                    runtime_instance="hub/group/project",
                )

            self.assertEqual(submitted["job_id"], "job-e2e-001")
            self.assertEqual(submitted["status"], "QUEUED")
            self.assertEqual(submitted["runtime_channel_used"], "ibm_cloud")
            self.assertEqual(submitted["runtime_instance_used"], "hub/group/project")
            self.assertEqual(submitted["circuit_summary"], expected_circuit_summary)
            build_submit_mock.assert_called_once()

            with patch.object(
                quantum_engine,
                "create_runtime_service",
                return_value=(service, "ibm_cloud"),
            ) as create_service_mock:
                first_poll = quantum_engine.poll_knot_experiment_result(
                    token="token-123",
                    job_id="job-e2e-001",
                    runtime_channel="ibm_cloud",
                    runtime_instance="hub/group/project",
                )
                second_poll = quantum_engine.poll_knot_experiment_result(
                    token="token-123",
                    job_id="job-e2e-001",
                    runtime_channel="ibm_cloud",
                    runtime_instance="hub/group/project",
                )

            self.assertEqual(first_poll["status"], "RUNNING")
            self.assertEqual(second_poll["status"], "COMPLETED")
            self.assertEqual(second_poll["job_id"], "job-e2e-001")
            self.assertIn("counts", second_poll)
            self.assertAlmostEqual(sum(item["probability"] for item in second_poll["counts"]), 1.0)
            self.assertEqual(service.requested_job_ids, ["job-e2e-001", "job-e2e-001"])
            self.assertEqual(create_service_mock.call_count, 2)


if __name__ == "__main__":
    unittest.main()
