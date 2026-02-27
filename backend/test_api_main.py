import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from fastapi import HTTPException
    from fastapi.testclient import TestClient
    from pydantic import ValidationError
    import main as backend_main
    _TEST_IMPORT_ERROR = None
except ModuleNotFoundError as exc:
    HTTPException = Exception  # type: ignore[assignment]
    TestClient = None  # type: ignore[assignment]
    ValidationError = Exception  # type: ignore[assignment]
    backend_main = None
    _TEST_IMPORT_ERROR = exc


def _valid_request(**overrides):
    if backend_main is None:
        raise RuntimeError("backend.main could not be imported for tests.")
    payload = {
        "ibm_token": " token-value ",
        "backend_name": " ibm_kyiv ",
        "braid_word": " s1 s2^-1 ",
        "shots": 1024,
        "optimization_level": 2,
        "runtime_channel": "ibm_quantum_platform",
        "runtime_instance": "  hub/group/project  ",
    }
    payload.update(overrides)
    return backend_main.ExperimentRequest(**payload)


def _valid_poll_request(**overrides):
    if backend_main is None:
        raise RuntimeError("backend.main could not be imported for tests.")
    payload = {
        "ibm_token": " token-value ",
        "job_id": " job-123 ",
        "runtime_channel": "ibm_quantum_platform",
        "runtime_instance": "  hub/group/project  ",
    }
    payload.update(overrides)
    return backend_main.PollJobRequest(**payload)


def _valid_runtime_service_request(**overrides):
    if backend_main is None:
        raise RuntimeError("backend.main could not be imported for tests.")
    payload = {
        "ibm_token": " token-value ",
        "runtime_channel": "ibm_quantum_platform",
        "runtime_instance": "  hub/group/project  ",
    }
    payload.update(overrides)
    return backend_main.RuntimeServiceRequest(**payload)


@unittest.skipIf(_TEST_IMPORT_ERROR is not None, f"FastAPI backend test dependencies unavailable: {_TEST_IMPORT_ERROR}")
class ExperimentRequestModelTests(unittest.TestCase):
    def test_normalizes_string_fields(self):
        req = _valid_request()
        self.assertEqual(req.ibm_token, "token-value")
        self.assertEqual(req.backend_name, "ibm_kyiv")
        self.assertEqual(req.braid_word, "s1 s2^-1")
        self.assertEqual(req.runtime_instance, "hub/group/project")

    def test_blank_runtime_instance_becomes_none(self):
        req = _valid_request(runtime_instance="   ")
        self.assertIsNone(req.runtime_instance)

    def test_rejects_invalid_shots(self):
        with self.assertRaises(ValidationError):
            _valid_request(shots=0)

    def test_rejects_invalid_optimization_level(self):
        with self.assertRaises(ValidationError):
            _valid_request(optimization_level=9)


@unittest.skipIf(_TEST_IMPORT_ERROR is not None, f"FastAPI backend test dependencies unavailable: {_TEST_IMPORT_ERROR}")
class PollJobRequestModelTests(unittest.TestCase):
    def test_normalizes_string_fields(self):
        req = _valid_poll_request()
        self.assertEqual(req.ibm_token, "token-value")
        self.assertEqual(req.job_id, "job-123")
        self.assertEqual(req.runtime_instance, "hub/group/project")

    def test_blank_runtime_instance_becomes_none(self):
        req = _valid_poll_request(runtime_instance="   ")
        self.assertIsNone(req.runtime_instance)


@unittest.skipIf(_TEST_IMPORT_ERROR is not None, f"FastAPI backend test dependencies unavailable: {_TEST_IMPORT_ERROR}")
class RuntimeServiceRequestModelTests(unittest.TestCase):
    def test_normalizes_string_fields(self):
        req = _valid_runtime_service_request()
        self.assertEqual(req.ibm_token, "token-value")
        self.assertEqual(req.runtime_instance, "hub/group/project")

    def test_blank_runtime_instance_becomes_none(self):
        req = _valid_runtime_service_request(runtime_instance="   ")
        self.assertIsNone(req.runtime_instance)


@unittest.skipIf(_TEST_IMPORT_ERROR is not None, f"FastAPI backend test dependencies unavailable: {_TEST_IMPORT_ERROR}")
class ApiHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_run_experiment_success_passes_expected_arguments(self):
        req = _valid_request()
        expected = {
            "job_id": "abc123",
            "backend": "ibm_kyiv",
            "counts": [{"name": "00", "probability": 1.0}],
            "expectation_value": 1.0,
            "jones_polynomial": "V(t) = 1.000t^-4 + t^-3 + t^-1",
            "status": "COMPLETED",
        }

        run_in_threadpool_mock = AsyncMock(return_value=expected)

        with patch.object(backend_main, "run_in_threadpool", run_in_threadpool_mock):
            result = await backend_main.run_experiment(req)

        self.assertEqual(result, expected)
        run_in_threadpool_mock.assert_awaited_once()
        args = run_in_threadpool_mock.await_args.args
        self.assertIs(args[0], backend_main.run_knot_experiment)
        self.assertEqual(
            args[1:],
            (
                "token-value",
                "ibm_kyiv",
                "s1 s2^-1",
                1024,
                2,
                "ibm_quantum_platform",
                "hub/group/project",
            ),
        )

    async def test_run_experiment_maps_value_error_to_422(self):
        req = _valid_request()
        run_in_threadpool_mock = AsyncMock(side_effect=ValueError("Unsupported braid token 's9'."))

        with patch.object(backend_main, "run_in_threadpool", run_in_threadpool_mock):
            with self.assertRaises(HTTPException) as ctx:
                await backend_main.run_experiment(req)

        self.assertEqual(ctx.exception.status_code, 422)
        self.assertEqual(ctx.exception.detail, "Unsupported braid token 's9'.")

    async def test_run_experiment_maps_unexpected_error_to_500(self):
        req = _valid_request()
        run_in_threadpool_mock = AsyncMock(side_effect=RuntimeError("hardware unavailable"))

        with patch.object(backend_main, "run_in_threadpool", run_in_threadpool_mock):
            with self.assertRaises(HTTPException) as ctx:
                await backend_main.run_experiment(req)

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertEqual(ctx.exception.detail, "hardware unavailable")

    async def test_health_endpoint(self):
        self.assertEqual(await backend_main.health(), {"status": "ok"})


@unittest.skipIf(_TEST_IMPORT_ERROR is not None, f"FastAPI backend test dependencies unavailable: {_TEST_IMPORT_ERROR}")
class SubmitPollRouteSequenceTests(unittest.TestCase):
    def test_submit_and_poll_routes_use_expected_threadpool_targets(self):
        client = TestClient(backend_main.app)

        submit_response_payload = {
            "job_id": "job-123",
            "backend": "ibm_kyiv",
            "runtime_channel_used": "ibm_quantum_platform",
            "runtime_instance_used": "hub/group/project",
            "status": "QUEUED",
        }
        poll_response_payload = {
            "job_id": "job-123",
            "backend": "ibm_kyiv",
            "runtime_channel_used": "ibm_quantum_platform",
            "runtime_instance_used": "hub/group/project",
            "counts": [{"name": "00", "probability": 1.0}],
            "expectation_value": 1.0,
            "jones_polynomial": "V(t) = 1.000t^-4 + t^-3 + t^-1",
            "status": "COMPLETED",
        }

        run_in_threadpool_mock = AsyncMock(side_effect=[submit_response_payload, poll_response_payload])

        with patch.object(backend_main, "run_in_threadpool", run_in_threadpool_mock):
            submit_response = client.post(
                "/api/jobs/submit",
                json={
                    "ibm_token": " token-value ",
                    "backend_name": " ibm_kyiv ",
                    "braid_word": " s1 s2^-1 ",
                    "shots": 1024,
                    "optimization_level": 2,
                    "runtime_channel": "ibm_quantum_platform",
                    "runtime_instance": "  hub/group/project  ",
                },
            )
            self.assertEqual(submit_response.status_code, 200)
            self.assertEqual(submit_response.json(), submit_response_payload)

            poll_response = client.post(
                "/api/jobs/poll",
                json={
                    "ibm_token": " token-value ",
                    "job_id": " job-123 ",
                    "runtime_channel": "ibm_quantum_platform",
                    "runtime_instance": "  hub/group/project  ",
                },
            )
            self.assertEqual(poll_response.status_code, 200)
            self.assertEqual(poll_response.json(), poll_response_payload)

        self.assertEqual(run_in_threadpool_mock.await_count, 2)

        first_args = run_in_threadpool_mock.await_args_list[0].args
        self.assertIs(first_args[0], backend_main.submit_knot_experiment)
        self.assertEqual(
            first_args[1:],
            (
                "token-value",
                "ibm_kyiv",
                "s1 s2^-1",
                1024,
                2,
                "ibm_quantum_platform",
                "hub/group/project",
            ),
        )

        second_args = run_in_threadpool_mock.await_args_list[1].args
        self.assertIs(second_args[0], backend_main.poll_knot_experiment_result)
        self.assertEqual(
            second_args[1:],
            (
                "token-value",
                "job-123",
                "ibm_quantum_platform",
                "hub/group/project",
            ),
        )

    def test_cancel_and_backends_routes_use_expected_threadpool_targets(self):
        client = TestClient(backend_main.app)

        cancel_response_payload = {
            "job_id": "job-123",
            "backend": "ibm_kyiv",
            "runtime_channel_used": "ibm_quantum_platform",
            "runtime_instance_used": "hub/group/project",
            "status": "CANCELLED",
            "detail": "Cancellation requested.",
        }
        backends_response_payload = {
            "runtime_channel_used": "ibm_quantum_platform",
            "runtime_instance_used": "hub/group/project",
            "recommended_backend": "ibm_kyiv",
            "backends": [
                {
                    "name": "ibm_kyiv",
                    "num_qubits": 127,
                    "pending_jobs": 2,
                    "operational": True,
                }
            ],
        }

        run_in_threadpool_mock = AsyncMock(side_effect=[cancel_response_payload, backends_response_payload])

        with patch.object(backend_main, "run_in_threadpool", run_in_threadpool_mock):
            cancel_response = client.post(
                "/api/jobs/cancel",
                json={
                    "ibm_token": " token-value ",
                    "job_id": " job-123 ",
                    "runtime_channel": "ibm_quantum_platform",
                    "runtime_instance": "  hub/group/project  ",
                },
            )
            self.assertEqual(cancel_response.status_code, 200)
            self.assertEqual(cancel_response.json(), cancel_response_payload)

            backends_response = client.post(
                "/api/backends",
                json={
                    "ibm_token": " token-value ",
                    "runtime_channel": "ibm_quantum_platform",
                    "runtime_instance": "  hub/group/project  ",
                },
            )
            self.assertEqual(backends_response.status_code, 200)
            self.assertEqual(backends_response.json(), backends_response_payload)

        self.assertEqual(run_in_threadpool_mock.await_count, 2)

        first_args = run_in_threadpool_mock.await_args_list[0].args
        self.assertIs(first_args[0], backend_main.cancel_knot_experiment)
        self.assertEqual(
            first_args[1:],
            (
                "token-value",
                "job-123",
                "ibm_quantum_platform",
                "hub/group/project",
            ),
        )

        second_args = run_in_threadpool_mock.await_args_list[1].args
        self.assertIs(second_args[0], backend_main.list_accessible_backends)
        self.assertEqual(
            second_args[1:],
            (
                "token-value",
                "ibm_quantum_platform",
                "hub/group/project",
            ),
        )


if __name__ == "__main__":
    unittest.main()
