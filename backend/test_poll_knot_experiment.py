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
    def __init__(self, *, job_id: str, status: str, backend=None, error_message=None, pub_result=None):
        self._job_id = job_id
        self._status = status
        self._backend = backend if backend is not None else _Backend()
        self._error_message = error_message
        self._pub_result = pub_result or _PubResult()

    def job_id(self):
        return self._job_id

    def status(self):
        return _StatusValue(self._status)

    def backend(self):
        return self._backend

    def error_message(self):
        return self._error_message

    def result(self):
        return [self._pub_result]


class _RuntimeService:
    def __init__(self, job):
        self._job = job
        self.requested_job_ids = []

    def job(self, job_id):
        self.requested_job_ids.append(job_id)
        return self._job


class PollKnotExperimentResultTests(unittest.TestCase):
    def _run_poll(self, job):
        fake_service = _RuntimeService(job)
        fake_qiskit_module = types.SimpleNamespace(QiskitRuntimeService=object)

        with patch.dict(sys.modules, {"qiskit_ibm_runtime": fake_qiskit_module}):
            with patch.object(
                quantum_engine,
                "create_runtime_service",
                return_value=(fake_service, "ibm_cloud"),
            ) as create_service_mock:
                result = quantum_engine.poll_knot_experiment_result(
                    token="token-123",
                    job_id="job-123",
                    runtime_channel="ibm_cloud",
                    runtime_instance="instance-1",
                )

        create_service_mock.assert_called_once()
        self.assertEqual(fake_service.requested_job_ids, ["job-123"])
        return result

    def test_returns_queued_status_payload(self):
        job = _RuntimeJob(job_id="job-123", status="QUEUED")
        result = self._run_poll(job)

        self.assertEqual(result["job_id"], "job-123")
        self.assertEqual(result["backend"], "ibm_kyiv")
        self.assertEqual(result["runtime_channel_used"], "ibm_cloud")
        self.assertEqual(result["runtime_instance_used"], "instance-1")
        self.assertEqual(result["status"], "QUEUED")
        self.assertNotIn("counts", result)

    def test_returns_failed_status_payload_with_detail(self):
        job = _RuntimeJob(job_id="job-123", status="FAILED", error_message="Calibration drift detected")
        result = self._run_poll(job)

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["detail"], "Calibration drift detected")
        self.assertEqual(result["job_id"], "job-123")

    def test_returns_completed_result_payload(self):
        job = _RuntimeJob(job_id="job-123", status="DONE")
        result = self._run_poll(job)

        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["job_id"], "job-123")
        self.assertEqual(result["backend"], "ibm_kyiv")
        self.assertEqual(result["runtime_channel_used"], "ibm_cloud")
        self.assertEqual(result["runtime_instance_used"], "instance-1")
        self.assertIn("counts", result)
        self.assertAlmostEqual(sum(item["probability"] for item in result["counts"]), 1.0)
        self.assertAlmostEqual(result["expectation_value"], 0.4)
        self.assertIn("V(t) =", result["jones_polynomial"])


if __name__ == "__main__":
    unittest.main()
