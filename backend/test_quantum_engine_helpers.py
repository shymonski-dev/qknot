import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))

from quantum_engine import (
    create_runtime_service,
    create_sampler_for_backend,
    extract_counts_from_pub_result,
    resolve_backend_name,
    select_backend,
)


class _CountsContainer:
    def __init__(self, counts):
        self._counts = counts

    def get_counts(self):
        return self._counts


class _PubResultWithC:
    class Data:
        c = _CountsContainer({"0": 7, "1": 3})

    data = Data()


class _PubResultWithMeas:
    class Data:
        meas = _CountsContainer({"00": 5, "11": 5})

    data = Data()


class _PubResultJoinData:
    class Data:
        pass

    data = Data()

    @staticmethod
    def join_data():
        return _CountsContainer({"0": 4})


class _BackendNameProperty:
    name = "ibm_test_backend"


class _BackendNameMethod:
    @staticmethod
    def name():
        return "ibm_method_backend"


class _RuntimeServiceFactory:
    def __init__(self, outcomes):
        self._outcomes = outcomes
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self._outcomes.get(kwargs["channel"], ("ok", {"service": kwargs["channel"]}))
        kind, value = outcome
        if kind == "raise":
            raise value
        return value


class _LeastBusyServiceSupportsMinQubits:
    def __init__(self):
        self.calls = []

    def least_busy(self, **kwargs):
        self.calls.append(("least_busy", kwargs))
        return "least-busy-backend"

    def backend(self, name):
        self.calls.append(("backend", name))
        return f"backend:{name}"


class _LeastBusyServiceNoMinQubits:
    def __init__(self):
        self.calls = []

    def least_busy(self, **kwargs):
        self.calls.append(("least_busy", kwargs))
        if "min_num_qubits" in kwargs:
            raise TypeError("unexpected keyword argument 'min_num_qubits'")
        return "least-busy-backend"

    def backend(self, name):
        self.calls.append(("backend", name))
        raise RuntimeError("backend unavailable")


class _ModeOnlySampler:
    def __init__(self, *, mode):
        self.mode = mode


class _BackendKwOnlySampler:
    def __init__(self, *args, **kwargs):
        if "mode" in kwargs:
            raise TypeError("mode not supported")
        if "backend" in kwargs and not args:
            self.backend = kwargs["backend"]
            return
        raise TypeError("invalid constructor")


class _PositionalOnlySampler:
    def __init__(self, *args, **kwargs):
        if kwargs:
            raise TypeError("keyword arguments not supported")
        if len(args) != 1:
            raise TypeError("expected one positional backend")
        self.backend = args[0]


class QuantumEngineHelperTests(unittest.TestCase):
    def test_extract_counts_uses_c_register(self):
        counts = extract_counts_from_pub_result(_PubResultWithC())
        self.assertEqual(counts, {"0": 7, "1": 3})

    def test_extract_counts_uses_meas_register(self):
        counts = extract_counts_from_pub_result(_PubResultWithMeas())
        self.assertEqual(counts, {"00": 5, "11": 5})

    def test_extract_counts_falls_back_to_join_data(self):
        counts = extract_counts_from_pub_result(_PubResultJoinData())
        self.assertEqual(counts, {"0": 4})

    def test_extract_counts_raises_when_no_measurements_found(self):
        class EmptyPubResult:
            class Data:
                pass

            data = Data()

        with self.assertRaisesRegex(ValueError, "Unable to extract measurement counts"):
            extract_counts_from_pub_result(EmptyPubResult())

    def test_resolve_backend_name_supports_property(self):
        self.assertEqual(resolve_backend_name(_BackendNameProperty()), "ibm_test_backend")

    def test_resolve_backend_name_supports_method(self):
        self.assertEqual(resolve_backend_name(_BackendNameMethod()), "ibm_method_backend")

    def test_create_runtime_service_uses_explicit_channel_and_instance(self):
        factory = _RuntimeServiceFactory(
            {"ibm_cloud": ("ok", {"service": "cloud-service"})}
        )

        service, channel = create_runtime_service(
            QiskitRuntimeService=factory,
            token="token",
            runtime_channel="ibm_cloud",
            runtime_instance="instance-id",
        )

        self.assertEqual(service, {"service": "cloud-service"})
        self.assertEqual(channel, "ibm_cloud")
        self.assertEqual(factory.calls[0]["channel"], "ibm_cloud")
        self.assertEqual(factory.calls[0]["instance"], "instance-id")

    def test_create_runtime_service_auto_falls_back_to_supported_channel(self):
        factory = _RuntimeServiceFactory(
            {
                "ibm_quantum_platform": ("raise", Exception("Unknown channel 'ibm_quantum_platform'")),
                "ibm_cloud": ("ok", {"service": "cloud-service"}),
            }
        )

        service, channel = create_runtime_service(
            QiskitRuntimeService=factory,
            token="token",
            runtime_channel=None,
            runtime_instance=None,
        )

        self.assertEqual(service, {"service": "cloud-service"})
        self.assertEqual(channel, "ibm_cloud")
        self.assertEqual([call["channel"] for call in factory.calls[:2]], ["ibm_quantum_platform", "ibm_cloud"])

    def test_create_runtime_service_rejects_unsupported_explicit_channel_constructor(self):
        factory = _RuntimeServiceFactory(
            {"ibm_quantum_platform": ("raise", TypeError("channel argument not supported"))}
        )

        with self.assertRaisesRegex(ValueError, "does not support the selected runtime channel"):
            create_runtime_service(
                QiskitRuntimeService=factory,
                token="token",
                runtime_channel="ibm_quantum_platform",
                runtime_instance=None,
            )

    def test_select_backend_uses_named_backend(self):
        service = _LeastBusyServiceSupportsMinQubits()
        backend = select_backend(service, "ibm_kyiv")
        self.assertEqual(backend, "backend:ibm_kyiv")

    def test_select_backend_falls_back_to_least_busy_without_min_num_qubits_support(self):
        service = _LeastBusyServiceNoMinQubits()
        backend = select_backend(service, "least_busy")
        self.assertEqual(backend, "least-busy-backend")
        least_busy_calls = [call for call in service.calls if call[0] == "least_busy"]
        self.assertEqual(len(least_busy_calls), 2)
        self.assertIn("min_num_qubits", least_busy_calls[0][1])
        self.assertNotIn("min_num_qubits", least_busy_calls[1][1])

    def test_select_backend_named_backend_failure_falls_back_to_least_busy(self):
        service = _LeastBusyServiceNoMinQubits()
        backend = select_backend(service, "ibm_missing")
        self.assertEqual(backend, "least-busy-backend")

    def test_create_sampler_prefers_mode_constructor(self):
        sampler = create_sampler_for_backend(_ModeOnlySampler, "backend-a")
        self.assertEqual(sampler.mode, "backend-a")

    def test_create_sampler_falls_back_to_backend_keyword(self):
        sampler = create_sampler_for_backend(_BackendKwOnlySampler, "backend-b")
        self.assertEqual(sampler.backend, "backend-b")

    def test_create_sampler_falls_back_to_positional_constructor(self):
        sampler = create_sampler_for_backend(_PositionalOnlySampler, "backend-c")
        self.assertEqual(sampler.backend, "backend-c")


if __name__ == "__main__":
    unittest.main()
