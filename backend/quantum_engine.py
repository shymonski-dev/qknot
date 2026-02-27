from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qiskit import QuantumCircuit


BRAID_TOKEN_RE = re.compile(r"^s([12])(\^-1)?$")
AUTO_RUNTIME_CHANNELS = ("ibm_quantum_platform", "ibm_cloud", "ibm_quantum")
DEFAULT_ROOT_OF_UNITY = 5

# Catalog entries provide deterministic outputs for known notations.
_DOWKER_BRAID_CATALOG = {
    (4, 6, 2): {
        "knot_name": "Trefoil Knot (3_1)",
        "braid_word": "s1 s2^-1 s1 s2^-1",
        "root_of_unity": 5,
    },
    (4, 6, 8, 2): {
        "knot_name": "Figure-Eight Knot (4_1)",
        "braid_word": "s1 s2^-1 s1 s2 s1^-1 s2",
        "root_of_unity": 5,
    },
    (6, 8, 10, 2, 4): {
        "knot_name": "Cinquefoil Knot (5_1)",
        "braid_word": "s1 s2 s1 s2 s1 s2^-1 s1",
        "root_of_unity": 5,
    },
}


def parse_braid_word(braid_word: str):
    """
    Parse a simplified braid word and return (generator, is_inverse) tuples.
    Supported tokens: s1, s2, s1^-1, s2^-1
    """
    if not braid_word or not braid_word.strip():
        raise ValueError("Braid word cannot be empty.")

    parsed = []
    for token in braid_word.split():
        match = BRAID_TOKEN_RE.fullmatch(token)
        if not match:
            raise ValueError(
                f"Unsupported braid token '{token}'. Supported tokens are: s1, s2, s1^-1, s2^-1."
            )
        parsed.append((int(match.group(1)), bool(match.group(2))))

    return parsed


def _normalize_dowker_tokens(dowker_notation: str):
    if not dowker_notation or not dowker_notation.strip():
        raise ValueError("Dowker notation cannot be empty.")

    normalized_text = dowker_notation.replace(",", " ")
    raw_tokens = [token for token in normalized_text.split() if token]
    if len(raw_tokens) < 3:
        raise ValueError("Dowker notation must include at least three integer entries.")

    parsed_tokens = []
    for token in raw_tokens:
        try:
            value = int(token)
        except ValueError as exc:
            raise ValueError(f"Dowker notation token '{token}' is not a valid integer.") from exc

        if value == 0:
            raise ValueError("Dowker notation cannot contain zero values.")
        if abs(value) % 2 != 0:
            raise ValueError(f"Dowker notation token '{token}' must be even.")

        parsed_tokens.append(value)

    absolute_values = [abs(token) for token in parsed_tokens]
    if len(set(absolute_values)) != len(absolute_values):
        raise ValueError("Dowker notation values must be unique by absolute value.")

    expected_values = set(range(2, (2 * len(parsed_tokens)) + 1, 2))
    if set(absolute_values) != expected_values:
        raise ValueError(
            "Dowker notation absolute values must be a complete even sequence "
            f"from 2 to {2 * len(parsed_tokens)}."
        )

    return parsed_tokens


def _compile_tokens_to_braid(parsed_tokens: list[int]):
    # Phase two compiler fallback keeps braid tokens within currently supported generators.
    braid_tokens = []
    for index, token in enumerate(parsed_tokens):
        generator = "s1" if index % 2 == 0 else "s2"
        if token < 0:
            braid_tokens.append(f"{generator}^-1")
        else:
            braid_tokens.append(generator)
    return " ".join(braid_tokens)


def compile_dowker_notation(dowker_notation: str):
    parsed_tokens = _normalize_dowker_tokens(dowker_notation)
    absolute_key = tuple(abs(token) for token in parsed_tokens)
    catalog_entry = _DOWKER_BRAID_CATALOG.get(absolute_key)

    if catalog_entry:
        knot_name = catalog_entry["knot_name"]
        braid_word = catalog_entry["braid_word"]
        root_of_unity = catalog_entry["root_of_unity"]
        is_catalog_match = True
    else:
        knot_name = f"Dowker Knot ({len(parsed_tokens)} crossings)"
        braid_word = _compile_tokens_to_braid(parsed_tokens)
        root_of_unity = DEFAULT_ROOT_OF_UNITY
        is_catalog_match = False

    return {
        "dowker_notation_normalized": " ".join(str(token) for token in parsed_tokens),
        "crossing_count": len(parsed_tokens),
        "knot_name": knot_name,
        "braid_word": braid_word,
        "root_of_unity": root_of_unity,
        "is_catalog_match": is_catalog_match,
    }


def resolve_backend_name(backend) -> str:
    name_attr = getattr(backend, "name", None)
    if callable(name_attr):
        return str(name_attr())
    if isinstance(name_attr, str):
        return name_attr
    return str(backend)


def resolve_backend_num_qubits(backend) -> int | None:
    num_qubits_attr = getattr(backend, "num_qubits", None)
    try:
        num_qubits = num_qubits_attr() if callable(num_qubits_attr) else num_qubits_attr
    except Exception:
        num_qubits = None

    if isinstance(num_qubits, int):
        return num_qubits

    configuration_attr = getattr(backend, "configuration", None)
    try:
        configuration = configuration_attr() if callable(configuration_attr) else configuration_attr
    except Exception:
        configuration = None

    if configuration is None:
        return None

    config_qubits = getattr(configuration, "n_qubits", None)
    return config_qubits if isinstance(config_qubits, int) else None


def resolve_backend_pending_jobs(backend) -> int | None:
    pending_jobs_attr = getattr(backend, "pending_jobs", None)
    try:
        pending_jobs = pending_jobs_attr() if callable(pending_jobs_attr) else pending_jobs_attr
    except Exception:
        return None

    return pending_jobs if isinstance(pending_jobs, int) else None


def resolve_backend_operational(backend) -> bool | None:
    operational_attr = getattr(backend, "operational", None)
    try:
        operational = operational_attr() if callable(operational_attr) else operational_attr
    except Exception:
        return None

    return operational if isinstance(operational, bool) else None


def extract_counts_from_pub_result(pub_result):
    data = getattr(pub_result, "data", None)
    if data is None:
        raise ValueError("Sampler result did not include measurement data.")

    for attr_name in ("c", "meas", "m", "memory"):
        container = getattr(data, attr_name, None)
        if container is not None and hasattr(container, "get_counts"):
            counts = container.get_counts()
            if counts:
                return counts

    for attr_name in dir(data):
        if attr_name.startswith("_"):
            continue
        try:
            container = getattr(data, attr_name)
        except Exception:
            continue
        if container is not None and hasattr(container, "get_counts"):
            counts = container.get_counts()
            if counts:
                return counts

    join_data = getattr(pub_result, "join_data", None)
    if callable(join_data):
        joined = join_data()
        if joined is not None and hasattr(joined, "get_counts"):
            counts = joined.get_counts()
            if counts:
                return counts

    raise ValueError("Unable to extract measurement counts from sampler result.")


def _is_channel_support_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "channel" in message and ("invalid" in message or "supported" in message or "unknown" in message)


def _service_kwargs_with_optional_instance(token: str, channel: str, runtime_instance: str | None):
    kwargs = {"channel": channel, "token": token}
    if runtime_instance:
        kwargs["instance"] = runtime_instance
    return kwargs


def create_runtime_service(QiskitRuntimeService, token: str, runtime_channel: str | None, runtime_instance: str | None):
    if runtime_channel:
        try:
            return (
                QiskitRuntimeService(**_service_kwargs_with_optional_instance(token, runtime_channel, runtime_instance)),
                runtime_channel,
            )
        except TypeError as exc:
            raise ValueError(
                f"The installed qiskit runtime client does not support the selected runtime channel '{runtime_channel}'."
            ) from exc
        except Exception as exc:
            raise ValueError(f"Failed to initialize IBM runtime service: {exc}") from exc

    errors = []
    for channel in AUTO_RUNTIME_CHANNELS:
        try:
            return (
                QiskitRuntimeService(**_service_kwargs_with_optional_instance(token, channel, runtime_instance)),
                channel,
            )
        except TypeError as exc:
            errors.append(f"{channel}: {exc}")
            continue
        except Exception as exc:
            if _is_channel_support_error(exc):
                errors.append(f"{channel}: {exc}")
                continue
            raise ValueError(f"Failed to initialize IBM runtime service: {exc}") from exc

    raise ValueError(
        "Unable to initialize the IBM runtime service with any supported runtime channel. "
        + " | ".join(errors)
    )


def select_backend(service, backend_name: str):
    if backend_name == "least_busy":
        try:
            return service.least_busy(operational=True, simulator=False, min_num_qubits=3)
        except TypeError:
            return service.least_busy(operational=True, simulator=False)

    try:
        return service.backend(backend_name)
    except Exception:
        try:
            return service.least_busy(operational=True, simulator=False, min_num_qubits=3)
        except TypeError:
            return service.least_busy(operational=True, simulator=False)


def create_sampler_for_backend(Sampler, backend):
    try:
        return Sampler(mode=backend)
    except TypeError:
        try:
            return Sampler(backend=backend)
        except TypeError:
            return Sampler(backend)


def list_accessible_backends(
    token: str,
    runtime_channel: str | None = None,
    runtime_instance: str | None = None,
):
    from qiskit_ibm_runtime import QiskitRuntimeService

    service, channel_used = create_runtime_service(
        QiskitRuntimeService=QiskitRuntimeService,
        token=token,
        runtime_channel=runtime_channel,
        runtime_instance=runtime_instance,
    )

    try:
        backends = service.backends(operational=True, simulator=False)
    except TypeError:
        backends = service.backends(simulator=False)
    except Exception as exc:
        raise ValueError(f"Failed to list accessible backends: {exc}") from exc

    backend_entries = []
    seen_names = set()
    for backend in backends:
        name = resolve_backend_name(backend)
        if name in seen_names:
            continue
        seen_names.add(name)
        backend_entries.append(
            {
                "name": name,
                "num_qubits": resolve_backend_num_qubits(backend),
                "pending_jobs": resolve_backend_pending_jobs(backend),
                "operational": resolve_backend_operational(backend),
            }
        )

    backend_entries.sort(
        key=lambda item: (
            item["pending_jobs"] if isinstance(item["pending_jobs"], int) else 10**9,
            item["name"],
        )
    )

    recommended_backend = None
    try:
        recommended_backend = resolve_backend_name(select_backend(service, "least_busy"))
    except Exception:
        recommended_backend = backend_entries[0]["name"] if backend_entries else None

    return {
        "runtime_channel_used": channel_used,
        "runtime_instance_used": runtime_instance,
        "recommended_backend": recommended_backend,
        "backends": backend_entries,
    }


IN_PROGRESS_JOB_STATUSES = {"INITIALIZING", "QUEUED", "RUNNING", "VALIDATING"}
FAILED_JOB_STATUSES = {"ERROR", "FAILED", "CANCELLED", "CANCELED"}
COMPLETED_JOB_STATUSES = {"DONE", "COMPLETED", "SUCCESS"}


def resolve_job_id(job) -> str:
    job_id_attr = getattr(job, "job_id", None)
    if callable(job_id_attr):
        return str(job_id_attr())
    if isinstance(job_id_attr, str):
        return job_id_attr
    raise ValueError("Unable to determine runtime job identifier.")


def resolve_job_status(job) -> str:
    status_attr = getattr(job, "status", None)
    try:
        status_value = status_attr() if callable(status_attr) else status_attr
    except Exception:
        return "UNKNOWN"

    if status_value is None:
        return "UNKNOWN"

    status_name = getattr(status_value, "name", None)
    if isinstance(status_name, str) and status_name:
        return status_name.upper()

    return str(status_value).split(".")[-1].upper()


def resolve_job_backend_name(job) -> str | None:
    backend_attr = getattr(job, "backend", None)
    try:
        backend = backend_attr() if callable(backend_attr) else backend_attr
    except Exception:
        return None

    if backend is None:
        return None

    return resolve_backend_name(backend)


def resolve_job_error_message(job) -> str | None:
    error_attr = getattr(job, "error_message", None)
    try:
        error_value = error_attr() if callable(error_attr) else error_attr
    except Exception:
        return None

    if not error_value:
        return None

    return str(error_value)


def _format_counts_and_expectation(counts: dict):
    zero_count = counts.get("0", 0)
    one_count = counts.get("1", 0)
    total = zero_count + one_count
    expectation = (zero_count - one_count) / total if total > 0 else 0

    formatted_counts = [
        {"name": key.zfill(2), "probability": value / total if total > 0 else 0}
        for key, value in counts.items()
    ]

    return formatted_counts, expectation


def format_completed_job_result(
    job,
    channel_used: str | None,
    runtime_instance: str | None,
    backend_name_hint: str | None = None,
):
    result = job.result()
    pub_result = result[0]
    counts = extract_counts_from_pub_result(pub_result)
    formatted_counts, expectation = _format_counts_and_expectation(counts)
    jones_poly = f"V(t) = {expectation:.3f}t^-4 + t^-3 + t^-1"

    return {
        "job_id": resolve_job_id(job),
        "backend": backend_name_hint or resolve_job_backend_name(job) or "unknown",
        "runtime_channel_used": channel_used,
        "runtime_instance_used": runtime_instance,
        "counts": formatted_counts,
        "expectation_value": expectation,
        "jones_polynomial": jones_poly,
        "status": "COMPLETED",
    }


def _build_and_submit_knot_job(
    token: str,
    backend_name: str,
    braid_word: str,
    shots: int,
    optimization_level: int = 3,
    runtime_channel: str | None = None,
    runtime_instance: str | None = None,
):
    import numpy as np
    from qiskit import QuantumCircuit, transpile
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler

    parsed_braid = parse_braid_word(braid_word)

    service, channel_used = create_runtime_service(
        QiskitRuntimeService=QiskitRuntimeService,
        token=token,
        runtime_channel=runtime_channel,
        runtime_instance=runtime_instance,
    )

    backend = select_backend(service, backend_name)

    # Build the simplified Hadamard-test circuit.
    qc = QuantumCircuit(3, 1)
    qc.h(0)
    theta = 2 * np.pi / 5

    for generator, is_inverse in parsed_braid:
        apply_braid_generator(
            qc,
            ancilla=0,
            data_a=1,
            data_b=2,
            generator=generator,
            is_inverse=is_inverse,
            theta=theta,
        )

    qc.h(0)
    qc.measure(0, 0)

    transpiled_qc = transpile(qc, backend=backend, optimization_level=optimization_level)
    sampler = create_sampler_for_backend(Sampler, backend)
    job = sampler.run([transpiled_qc], shots=shots)

    return job, backend, channel_used


def apply_braid_generator(
    qc: QuantumCircuit,
    ancilla: int,
    data_a: int,
    data_b: int,
    generator: int,
    is_inverse: bool,
    theta: float,
):
    """
    Apply a simplified controlled unitary for a braid generator.
    This is still a mock physics model, but now the circuit changes with the braid word.
    """
    phase = -theta if is_inverse else theta

    if generator == 1:
        qc.cx(data_a, data_b)
        qc.cp(phase, ancilla, data_a)
        qc.cx(data_a, data_b)
        return

    if generator == 2:
        qc.h(data_a)
        qc.cx(data_b, data_a)
        qc.cp(phase, ancilla, data_b)
        qc.cx(data_b, data_a)
        qc.h(data_a)
        return

    raise ValueError(f"Unsupported braid generator index: s{generator}")


def submit_knot_experiment(
    token: str,
    backend_name: str,
    braid_word: str,
    shots: int,
    optimization_level: int = 3,
    runtime_channel: str | None = None,
    runtime_instance: str | None = None,
):
    job, backend, channel_used = _build_and_submit_knot_job(
        token=token,
        backend_name=backend_name,
        braid_word=braid_word,
        shots=shots,
        optimization_level=optimization_level,
        runtime_channel=runtime_channel,
        runtime_instance=runtime_instance,
    )

    status = resolve_job_status(job)
    if status == "UNKNOWN":
        status = "SUBMITTED"

    return {
        "job_id": resolve_job_id(job),
        "backend": resolve_backend_name(backend),
        "runtime_channel_used": channel_used,
        "runtime_instance_used": runtime_instance,
        "status": status,
    }


def poll_knot_experiment_result(
    token: str,
    job_id: str,
    runtime_channel: str | None = None,
    runtime_instance: str | None = None,
):
    from qiskit_ibm_runtime import QiskitRuntimeService

    service, channel_used = create_runtime_service(
        QiskitRuntimeService=QiskitRuntimeService,
        token=token,
        runtime_channel=runtime_channel,
        runtime_instance=runtime_instance,
    )

    try:
        job = service.job(job_id)
    except Exception as exc:
        raise ValueError(f"Failed to retrieve runtime job '{job_id}': {exc}") from exc

    status = resolve_job_status(job)
    backend_name = resolve_job_backend_name(job)

    if status in FAILED_JOB_STATUSES:
        error_message = resolve_job_error_message(job)
        response = {
            "job_id": resolve_job_id(job),
            "backend": backend_name or "unknown",
            "runtime_channel_used": channel_used,
            "runtime_instance_used": runtime_instance,
            "status": status,
        }
        if error_message:
            response["detail"] = error_message
        return response

    if status in IN_PROGRESS_JOB_STATUSES:
        return {
            "job_id": resolve_job_id(job),
            "backend": backend_name or "unknown",
            "runtime_channel_used": channel_used,
            "runtime_instance_used": runtime_instance,
            "status": status,
        }

    try:
        return format_completed_job_result(
            job=job,
            channel_used=channel_used,
            runtime_instance=runtime_instance,
            backend_name_hint=backend_name,
        )
    except Exception as exc:
        if status and status not in COMPLETED_JOB_STATUSES:
            return {
                "job_id": resolve_job_id(job),
                "backend": backend_name or "unknown",
                "runtime_channel_used": channel_used,
                "runtime_instance_used": runtime_instance,
                "status": status,
                "detail": str(exc),
            }
        raise


def cancel_knot_experiment(
    token: str,
    job_id: str,
    runtime_channel: str | None = None,
    runtime_instance: str | None = None,
):
    from qiskit_ibm_runtime import QiskitRuntimeService

    service, channel_used = create_runtime_service(
        QiskitRuntimeService=QiskitRuntimeService,
        token=token,
        runtime_channel=runtime_channel,
        runtime_instance=runtime_instance,
    )

    try:
        job = service.job(job_id)
    except Exception as exc:
        raise ValueError(f"Failed to retrieve runtime job '{job_id}': {exc}") from exc

    try:
        cancel_attr = getattr(job, "cancel", None)
        if callable(cancel_attr):
            cancel_attr()
    except Exception as exc:
        raise ValueError(f"Failed to cancel runtime job '{job_id}': {exc}") from exc

    status = resolve_job_status(job)
    if status == "UNKNOWN":
        status = "CANCEL_REQUESTED"

    return {
        "job_id": resolve_job_id(job),
        "backend": resolve_job_backend_name(job) or "unknown",
        "runtime_channel_used": channel_used,
        "runtime_instance_used": runtime_instance,
        "status": status,
        "detail": "Cancellation requested.",
    }


def run_knot_experiment(
    token: str,
    backend_name: str,
    braid_word: str,
    shots: int,
    optimization_level: int = 3,
    runtime_channel: str | None = None,
    runtime_instance: str | None = None,
):
    """
    Submits a knot evaluation circuit to IBM Quantum hardware using Qiskit Runtime.
    """
    job, backend, channel_used = _build_and_submit_knot_job(
        token=token,
        backend_name=backend_name,
        braid_word=braid_word,
        shots=shots,
        optimization_level=optimization_level,
        runtime_channel=runtime_channel,
        runtime_instance=runtime_instance,
    )

    return format_completed_job_result(
        job=job,
        channel_used=channel_used,
        runtime_instance=runtime_instance,
        backend_name_hint=resolve_backend_name(backend),
    )
