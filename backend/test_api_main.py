import os
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
        "backend_name": " ibm_kyiv ",
        "braid_word": " s1 s2^-1 ",
        "shots": 1024,
        "optimization_level": 2,
        "closure_method": "trace",
        "runtime_channel": "ibm_quantum_platform",
        "runtime_instance": "  hub/group/project  ",
    }
    payload.update(overrides)
    return backend_main.ExperimentRequest(**payload)


def _valid_poll_request(**overrides):
    if backend_main is None:
        raise RuntimeError("backend.main could not be imported for tests.")
    payload = {
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
        "runtime_channel": "ibm_quantum_platform",
        "runtime_instance": "  hub/group/project  ",
    }
    payload.update(overrides)
    return backend_main.RuntimeServiceRequest(**payload)


def _valid_knot_ingestion_request(**overrides):
    if backend_main is None:
        raise RuntimeError("backend.main could not be imported for tests.")
    payload = {
        "dowker_notation": " 4 6 2 ",
    }
    payload.update(overrides)
    return backend_main.KnotIngestionRequest(**payload)


def _valid_knot_verification_request(**overrides):
    if backend_main is None:
        raise RuntimeError("backend.main could not be imported for tests.")
    payload = {
        "braid_word": " s1 s2^-1 s1 ",
    }
    payload.update(overrides)
    return backend_main.KnotVerificationRequest(**payload)


def _valid_circuit_generation_request(**overrides):
    if backend_main is None:
        raise RuntimeError("backend.main could not be imported for tests.")
    payload = {
        "braid_word": " s1 s2^-1 s1 ",
        "optimization_level": 2,
        "closure_method": "trace",
        "target_backend": " ibm_kyiv ",
    }
    payload.update(overrides)
    return backend_main.CircuitGenerationRequest(**payload)


@unittest.skipIf(_TEST_IMPORT_ERROR is not None, f"FastAPI backend test dependencies unavailable: {_TEST_IMPORT_ERROR}")
class ExperimentRequestModelTests(unittest.TestCase):
    def test_normalizes_string_fields(self):
        req = _valid_request()
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

    def test_accepts_expanded_generator_tokens(self):
        req = _valid_request(braid_word=" s1 s2^-1 s3 s4^-1 ")
        self.assertEqual(req.braid_word, "s1 s2^-1 s3 s4^-1")


@unittest.skipIf(_TEST_IMPORT_ERROR is not None, f"FastAPI backend test dependencies unavailable: {_TEST_IMPORT_ERROR}")
class PollJobRequestModelTests(unittest.TestCase):
    def test_normalizes_string_fields(self):
        req = _valid_poll_request()
        self.assertEqual(req.job_id, "job-123")
        self.assertEqual(req.runtime_instance, "hub/group/project")

    def test_blank_runtime_instance_becomes_none(self):
        req = _valid_poll_request(runtime_instance="   ")
        self.assertIsNone(req.runtime_instance)


@unittest.skipIf(_TEST_IMPORT_ERROR is not None, f"FastAPI backend test dependencies unavailable: {_TEST_IMPORT_ERROR}")
class RuntimeServiceRequestModelTests(unittest.TestCase):
    def test_normalizes_string_fields(self):
        req = _valid_runtime_service_request()
        self.assertEqual(req.runtime_instance, "hub/group/project")

    def test_blank_runtime_instance_becomes_none(self):
        req = _valid_runtime_service_request(runtime_instance="   ")
        self.assertIsNone(req.runtime_instance)


@unittest.skipIf(_TEST_IMPORT_ERROR is not None, f"FastAPI backend test dependencies unavailable: {_TEST_IMPORT_ERROR}")
class KnotIngestionRequestModelTests(unittest.TestCase):
    def test_normalizes_string_fields(self):
        req = _valid_knot_ingestion_request()
        self.assertEqual(req.dowker_notation, "4 6 2")

    def test_rejects_blank_dowker_notation(self):
        with self.assertRaises(ValidationError):
            _valid_knot_ingestion_request(dowker_notation="   ")


@unittest.skipIf(_TEST_IMPORT_ERROR is not None, f"FastAPI backend test dependencies unavailable: {_TEST_IMPORT_ERROR}")
class KnotVerificationRequestModelTests(unittest.TestCase):
    def test_normalizes_string_fields(self):
        req = _valid_knot_verification_request()
        self.assertEqual(req.braid_word, "s1 s2^-1 s1")

    def test_rejects_blank_braid_word(self):
        with self.assertRaises(ValidationError):
            _valid_knot_verification_request(braid_word="   ")


@unittest.skipIf(_TEST_IMPORT_ERROR is not None, f"FastAPI backend test dependencies unavailable: {_TEST_IMPORT_ERROR}")
class CircuitGenerationRequestModelTests(unittest.TestCase):
    def test_normalizes_string_fields(self):
        req = _valid_circuit_generation_request()
        self.assertEqual(req.braid_word, "s1 s2^-1 s1")
        self.assertEqual(req.target_backend, "ibm_kyiv")
        self.assertEqual(req.closure_method, "trace")

    def test_blank_target_backend_becomes_none(self):
        req = _valid_circuit_generation_request(target_backend="   ")
        self.assertIsNone(req.target_backend)

    def test_rejects_blank_braid_word(self):
        with self.assertRaises(ValidationError):
            _valid_circuit_generation_request(braid_word="   ")

    def test_accepts_expanded_generator_tokens(self):
        req = _valid_circuit_generation_request(braid_word=" s1 s2 s3^-1 s4 ")
        self.assertEqual(req.braid_word, "s1 s2 s3^-1 s4")


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

        with (
            patch.dict(os.environ, {"IBM_QUANTUM_TOKEN": "token-value"}, clear=False),
            patch.object(backend_main, "run_in_threadpool", run_in_threadpool_mock),
        ):
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
                "trace",
                "ibm_quantum_platform",
                "hub/group/project",
            ),
        )

    async def test_run_experiment_maps_value_error_to_422(self):
        req = _valid_request()
        run_in_threadpool_mock = AsyncMock(side_effect=ValueError("Unsupported braid token 's9'."))

        with (
            patch.dict(os.environ, {"IBM_QUANTUM_TOKEN": "token-value"}, clear=False),
            patch.object(backend_main, "run_in_threadpool", run_in_threadpool_mock),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await backend_main.run_experiment(req)

        self.assertEqual(ctx.exception.status_code, 422)
        self.assertEqual(ctx.exception.detail, "Unsupported braid token 's9'.")

    async def test_run_experiment_maps_unexpected_error_to_500(self):
        req = _valid_request()
        run_in_threadpool_mock = AsyncMock(side_effect=RuntimeError("hardware unavailable"))

        with (
            patch.dict(os.environ, {"IBM_QUANTUM_TOKEN": "token-value"}, clear=False),
            patch.object(backend_main, "run_in_threadpool", run_in_threadpool_mock),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await backend_main.run_experiment(req)

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertEqual(ctx.exception.detail, "hardware unavailable")

    async def test_health_endpoint(self):
        self.assertEqual(await backend_main.health(), {"status": "ok"})


@unittest.skipIf(_TEST_IMPORT_ERROR is not None, f"FastAPI backend test dependencies unavailable: {_TEST_IMPORT_ERROR}")
class BackendCredentialResolutionTests(unittest.TestCase):
    def test_prefers_primary_backend_token_variable(self):
        with patch.dict(
            os.environ,
            {
                "IBM_QUANTUM_TOKEN": "primary-token",
                "QKNOT_IBM_TOKEN": "fallback-token",
            },
            clear=True,
        ):
            self.assertEqual(backend_main._resolve_ibm_token(), "primary-token")

    def test_uses_legacy_token_variable_as_fallback(self):
        with patch.dict(os.environ, {"QKNOT_IBM_TOKEN": "fallback-token"}, clear=True):
            self.assertEqual(backend_main._resolve_ibm_token(), "fallback-token")

    def test_raises_when_no_backend_token_exists(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                backend_main._resolve_ibm_token()


@unittest.skipIf(_TEST_IMPORT_ERROR is not None, f"FastAPI backend test dependencies unavailable: {_TEST_IMPORT_ERROR}")
class SubmitPollRouteSequenceTests(unittest.TestCase):
    def setUp(self):
        self._env_patch = patch.dict(os.environ, {"IBM_QUANTUM_TOKEN": "token-value"}, clear=False)
        self._env_patch.start()

    def tearDown(self):
        self._env_patch.stop()

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
                    "backend_name": " ibm_kyiv ",
                    "braid_word": " s1 s2^-1 ",
                    "shots": 1024,
                    "optimization_level": 2,
                    "closure_method": "trace",
                    "runtime_channel": "ibm_quantum_platform",
                    "runtime_instance": "  hub/group/project  ",
                },
            )
            self.assertEqual(submit_response.status_code, 200)
            self.assertEqual(submit_response.json(), submit_response_payload)

            poll_response = client.post(
                "/api/jobs/poll",
                json={
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
                "trace",
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

    def test_knot_ingestion_route_uses_expected_threadpool_target(self):
        client = TestClient(backend_main.app)

        ingestion_payload = {
            "dowker_notation_normalized": "4 6 2",
            "crossing_count": 3,
            "knot_name": "Trefoil Knot (3_1)",
            "braid_word": "s1 s2^-1 s1 s2^-1",
            "root_of_unity": 5,
            "is_catalog_match": True,
        }

        run_in_threadpool_mock = AsyncMock(return_value=ingestion_payload)

        with patch.object(backend_main, "run_in_threadpool", run_in_threadpool_mock):
            response = client.post(
                "/api/knot/ingest",
                json={
                    "dowker_notation": " 4 6 2 ",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), ingestion_payload)
        run_in_threadpool_mock.assert_awaited_once()
        args = run_in_threadpool_mock.await_args.args
        self.assertIs(args[0], backend_main.compile_dowker_notation)
        self.assertEqual(args[1:], ("4 6 2",))

    def test_knot_ingestion_route_maps_value_error_to_422(self):
        client = TestClient(backend_main.app)
        run_in_threadpool_mock = AsyncMock(side_effect=ValueError("Dowker notation token '3' must be even."))

        with patch.object(backend_main, "run_in_threadpool", run_in_threadpool_mock):
            response = client.post(
                "/api/knot/ingest",
                json={
                    "dowker_notation": "4 3 2",
                },
            )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json(), {"detail": "Dowker notation token '3' must be even."})

    def test_knot_verification_route_uses_expected_threadpool_target(self):
        client = TestClient(backend_main.app)

        verification_payload = {
            "is_verified": True,
            "status": "verified",
            "detail": "Topological verification passed with connected three-strand braid evidence.",
            "evidence": {
                "token_count": 4,
                "generator_counts": {"s1": 2, "s2": 2},
                "inverse_count": 2,
                "net_writhe": 0,
                "generator_switches": 3,
                "alternation_ratio": 1.0,
                "strand_connectivity": "connected-3-strand",
            },
        }

        run_in_threadpool_mock = AsyncMock(return_value=verification_payload)

        with patch.object(backend_main, "run_in_threadpool", run_in_threadpool_mock):
            response = client.post(
                "/api/knot/verify",
                json={
                    "braid_word": " s1 s2^-1 s1 s2^-1 ",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), verification_payload)
        run_in_threadpool_mock.assert_awaited_once()
        args = run_in_threadpool_mock.await_args.args
        self.assertIs(args[0], backend_main.verify_topological_mapping)
        self.assertEqual(args[1:], ("s1 s2^-1 s1 s2^-1",))

    def test_knot_verification_route_maps_value_error_to_422(self):
        client = TestClient(backend_main.app)
        run_in_threadpool_mock = AsyncMock(side_effect=ValueError("Unsupported braid token 'x3'."))

        with patch.object(backend_main, "run_in_threadpool", run_in_threadpool_mock):
            response = client.post(
                "/api/knot/verify",
                json={
                    "braid_word": "s1 x3",
                },
            )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json(), {"detail": "Unsupported braid token 'x3'."})

    def test_knot_circuit_generation_route_uses_expected_threadpool_target(self):
        client = TestClient(backend_main.app)

        generation_payload = {
            "target_backend": "ibm_kyiv",
            "optimization_level": 2,
            "closure_method": "trace",
            "braid_word": "s1 s2^-1 s1",
            "circuit_summary": {
                "depth": 12,
                "size": 20,
                "width": 4,
                "num_qubits": 3,
                "num_clbits": 1,
                "two_qubit_gate_count": 6,
                "measurement_count": 1,
                "operation_counts": {"cx": 4, "cp": 2, "h": 2, "measure": 1},
                "signature": "abc123",
            },
        }

        run_in_threadpool_mock = AsyncMock(return_value=generation_payload)

        with patch.object(backend_main, "run_in_threadpool", run_in_threadpool_mock):
            response = client.post(
                "/api/knot/circuit/generate",
                json={
                    "braid_word": " s1 s2^-1 s1 ",
                    "optimization_level": 2,
                    "closure_method": "trace",
                    "target_backend": " ibm_kyiv ",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), generation_payload)
        run_in_threadpool_mock.assert_awaited_once()
        args = run_in_threadpool_mock.await_args.args
        self.assertIs(args[0], backend_main.generate_knot_circuit_artifact)
        self.assertEqual(args[1:], ("s1 s2^-1 s1", 2, "trace", "ibm_kyiv"))

    def test_knot_circuit_generation_route_maps_value_error_to_422(self):
        client = TestClient(backend_main.app)
        run_in_threadpool_mock = AsyncMock(side_effect=ValueError("Closure method must be either 'trace' or 'plat'."))

        with patch.object(backend_main, "run_in_threadpool", run_in_threadpool_mock):
            response = client.post(
                "/api/knot/circuit/generate",
                json={
                    "braid_word": "s1 s2^-1 s1",
                    "optimization_level": 2,
                    "closure_method": "trace",
                    "target_backend": "ibm_kyiv",
                },
            )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json(), {"detail": "Closure method must be either 'trace' or 'plat'."})

    def test_submit_route_returns_server_error_when_token_env_is_missing(self):
        client = TestClient(backend_main.app)
        with patch.dict(os.environ, {}, clear=True):
            response = client.post(
                "/api/jobs/submit",
                json={
                    "backend_name": " ibm_kyiv ",
                    "braid_word": " s1 s2^-1 ",
                    "shots": 1024,
                    "optimization_level": 2,
                    "closure_method": "trace",
                },
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json(),
            {
                "detail": "Backend is missing IBM credentials. Set IBM_QUANTUM_TOKEN before calling runtime routes.",
            },
        )


if __name__ == "__main__":
    unittest.main()
