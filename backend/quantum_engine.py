from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qiskit import QuantumCircuit


BRAID_TOKEN_RE = re.compile(r"^s([1-9]\d*)(\^-1)?$")
AUTO_RUNTIME_CHANNELS = ("ibm_quantum_platform", "ibm_cloud", "ibm_quantum")
DEFAULT_ROOT_OF_UNITY = 5
DEFAULT_CLOSURE_METHOD = "trace"

SIMULATOR_BACKEND_NAME = "qiskit_simulator"
_SIM_JOB_ID_PREFIX = "sim-"
_simulator_result_store: dict[str, dict] = {}
_runtime_job_metadata_store: dict[str, dict] = {}

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
    Parse a braid word and return (generator, is_inverse) tuples.
    Supported token pattern: sN or sN^-1, where N is a positive integer.
    """
    if not braid_word or not braid_word.strip():
        raise ValueError("Braid word cannot be empty.")

    parsed = []
    for token in braid_word.split():
        match = BRAID_TOKEN_RE.fullmatch(token)
        if not match:
            raise ValueError(
                f"Unsupported braid token '{token}'. Supported tokens follow sN or sN^-1, where N is a positive integer."
            )
        parsed.append((int(match.group(1)), bool(match.group(2))))

    return parsed


def analyze_braid_word(braid_word: str):
    parsed_braid = parse_braid_word(braid_word)

    token_count = len(parsed_braid)
    generator_count_by_index: dict[int, int] = {}
    inverse_count = 0
    net_writhe = 0
    generator_switches = 0
    previous_generator = None

    for generator, is_inverse in parsed_braid:
        generator_count_by_index[generator] = generator_count_by_index.get(generator, 0) + 1
        if is_inverse:
            inverse_count += 1
            net_writhe -= 1
        else:
            net_writhe += 1

        if previous_generator is not None and previous_generator != generator:
            generator_switches += 1
        previous_generator = generator

    sorted_generator_indices = sorted(generator_count_by_index.keys())
    max_generator_index = sorted_generator_indices[-1]
    expected_generator_indices = list(range(1, max_generator_index + 1))
    missing_generator_indices = [
        generator_index
        for generator_index in expected_generator_indices
        if generator_index not in generator_count_by_index
    ]
    unique_generator_count = len(sorted_generator_indices)
    strand_count = max_generator_index + 1
    is_contiguous_generator_range = len(missing_generator_indices) == 0
    alternation_ratio = generator_switches / max(token_count - 1, 1)

    if unique_generator_count >= 2 and is_contiguous_generator_range:
        strand_connectivity = f"connected-{strand_count}-strand"
    else:
        strand_connectivity = f"partial-{strand_count}-strand"

    return {
        "parsed_braid": parsed_braid,
        "token_count": token_count,
        "generator_counts": {
            f"s{generator_index}": generator_count_by_index[generator_index]
            for generator_index in sorted_generator_indices
        },
        "inverse_count": inverse_count,
        "net_writhe": net_writhe,
        "generator_switches": generator_switches,
        "alternation_ratio": round(alternation_ratio, 3),
        "unique_generator_count": unique_generator_count,
        "max_generator_index": max_generator_index,
        "strand_count": strand_count,
        "missing_generators": [f"s{generator_index}" for generator_index in missing_generator_indices],
        "is_contiguous_generator_range": is_contiguous_generator_range,
        "strand_connectivity": strand_connectivity,
        "required_qubits": _required_ajl_qubits(strand_count, DEFAULT_ROOT_OF_UNITY),
    }


def validate_braid_problem_input(braid_word: str):
    analysis = analyze_braid_word(braid_word)

    if analysis["token_count"] < 3:
        raise ValueError("Braid word must contain at least three generators before execution.")

    if analysis["unique_generator_count"] < 2:
        raise ValueError("Braid word must include at least two distinct generators before execution.")

    if not analysis["is_contiguous_generator_range"]:
        missing_generators = ", ".join(analysis["missing_generators"])
        raise ValueError(
            "Braid word must use contiguous generators from s1 through "
            f"s{analysis['max_generator_index']}. Missing: {missing_generators}."
        )

    return analysis


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
    # Fallback mapping expands generator usage with notation size while remaining deterministic.
    strand_count = max(3, (len(parsed_tokens) // 2) + 2)
    max_generator = strand_count - 1
    braid_tokens = []
    for index, token in enumerate(parsed_tokens):
        generator = f"s{(index % max_generator) + 1}"
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


def verify_topological_mapping(braid_word: str):
    analysis = analyze_braid_word(braid_word)
    evidence = {
        "token_count": analysis["token_count"],
        "generator_counts": analysis["generator_counts"],
        "inverse_count": analysis["inverse_count"],
        "net_writhe": analysis["net_writhe"],
        "generator_switches": analysis["generator_switches"],
        "alternation_ratio": analysis["alternation_ratio"],
        "unique_generator_count": analysis["unique_generator_count"],
        "max_generator_index": analysis["max_generator_index"],
        "strand_count": analysis["strand_count"],
        "missing_generators": analysis["missing_generators"],
        "strand_connectivity": analysis["strand_connectivity"],
    }

    if analysis["token_count"] < 3:
        return {
            "is_verified": False,
            "status": "failed",
            "detail": "Verification failed: braid word must contain at least three generators.",
            "evidence": evidence,
        }

    if analysis["unique_generator_count"] < 2:
        return {
            "is_verified": False,
            "status": "failed",
            "detail": (
                "Verification failed: braid word must include at least two distinct generators "
                "to demonstrate strand connectivity."
            ),
            "evidence": evidence,
        }

    if not analysis["is_contiguous_generator_range"]:
        missing_generators = ", ".join(analysis["missing_generators"])
        return {
            "is_verified": False,
            "status": "failed",
            "detail": (
                "Verification failed: braid word must use contiguous generators from s1 through "
                f"s{analysis['max_generator_index']}. Missing: {missing_generators}."
            ),
            "evidence": evidence,
        }

    return {
        "is_verified": True,
        "status": "verified",
        "detail": (
            "Topological verification passed with connected "
            f"{analysis['strand_count']}-strand braid evidence."
        ),
        "evidence": evidence,
    }


def _validate_closure_method(closure_method: str):
    if closure_method not in {"trace", "plat"}:
        raise ValueError("Closure method must be either 'trace' or 'plat'.")


@lru_cache(maxsize=128)
def _path_model_basis(strand_count: int, root_of_unity: int) -> tuple[tuple[int, ...], ...]:
    if strand_count < 2:
        raise ValueError("Braid problems require at least two strands.")
    if root_of_unity < 5:
        raise ValueError("Root of unity must be at least 5 for stable path model evaluation.")

    basis = [(1,)]
    max_vertex = root_of_unity - 1

    for _ in range(strand_count):
        next_basis = []
        for path in basis:
            current_vertex = path[-1]
            lower_vertex = current_vertex - 1
            upper_vertex = current_vertex + 1
            if lower_vertex >= 1:
                next_basis.append(path + (lower_vertex,))
            if upper_vertex <= max_vertex:
                next_basis.append(path + (upper_vertex,))
        basis = next_basis

    if not basis:
        raise ValueError(
            "No admissible path basis exists for the requested strand count and root of unity."
        )

    return tuple(basis)


def _build_path_lambda_values(root_of_unity: int):
    import numpy as np

    lambda_values = np.zeros(root_of_unity, dtype=float)
    for vertex in range(1, root_of_unity):
        lambda_values[vertex] = float(np.sin(np.pi * vertex / root_of_unity))
    return lambda_values


def _build_temperley_lieb_projector(path_basis: tuple[tuple[int, ...], ...], lambda_values, generator: int):
    import numpy as np

    dimension = len(path_basis)
    strand_count = len(path_basis[0]) - 1
    if generator < 1 or generator >= strand_count:
        raise ValueError(f"Unsupported braid generator index: s{generator}")

    projector = np.zeros((dimension, dimension), dtype=complex)
    grouped_indices: dict[tuple[int, ...], list[int]] = {}

    for basis_index, path in enumerate(path_basis):
        outside_vertices = path[:generator] + path[generator + 1 :]
        grouped_indices.setdefault(outside_vertices, []).append(basis_index)

    for indices in grouped_indices.values():
        reference_path = path_basis[indices[0]]
        left_vertex = reference_path[generator - 1]
        right_vertex = reference_path[generator + 1]
        if left_vertex != right_vertex:
            continue

        normalization = lambda_values[left_vertex]
        if normalization <= 0:
            raise ValueError("Invalid path model normalization encountered.")

        for row_index in indices:
            row_middle_vertex = path_basis[row_index][generator]
            for column_index in indices:
                column_middle_vertex = path_basis[column_index][generator]
                coefficient = float(
                    np.sqrt(lambda_values[row_middle_vertex] * lambda_values[column_middle_vertex])
                    / normalization
                )
                projector[row_index, column_index] = coefficient

    return projector


def _build_ajl_context(strand_count: int, root_of_unity: int):
    import numpy as np

    path_basis = _path_model_basis(strand_count, root_of_unity)
    dimension = len(path_basis)
    work_qubits = max(1, (dimension - 1).bit_length())

    lambda_values = _build_path_lambda_values(root_of_unity)
    path_weights = np.array([lambda_values[path[-1]] for path in path_basis], dtype=float)
    markov_normalizer = float(path_weights.sum())
    if markov_normalizer <= 0:
        raise ValueError("Invalid Markov trace normalization encountered.")

    tl_projectors = {
        generator: _build_temperley_lieb_projector(path_basis, lambda_values, generator)
        for generator in range(1, strand_count)
    }

    a_parameter = 1j * np.exp(-1j * np.pi / (2 * root_of_unity))
    d_parameter = float(2 * np.cos(np.pi / root_of_unity))

    return {
        "path_basis": path_basis,
        "representation_dimension": dimension,
        "work_qubits": work_qubits,
        "path_weights": path_weights,
        "markov_normalizer": markov_normalizer,
        "tl_projectors": tl_projectors,
        "a_parameter": complex(a_parameter),
        "d_parameter": d_parameter,
        "strand_count": strand_count,
        "root_of_unity": root_of_unity,
    }


def _required_ajl_qubits(strand_count: int, root_of_unity: int) -> int:
    path_basis = _path_model_basis(strand_count, root_of_unity)
    work_qubits = max(1, (len(path_basis) - 1).bit_length())
    return 1 + work_qubits


def _compute_generator_matrix(ajl_context: dict, generator: int, is_inverse: bool):
    import numpy as np

    representation_dimension = ajl_context["representation_dimension"]
    identity = np.eye(representation_dimension, dtype=complex)

    projector = ajl_context["tl_projectors"].get(generator)
    if projector is None:
        raise ValueError(f"Unsupported braid generator index: s{generator}")

    temperley_lieb_generator = ajl_context["d_parameter"] * projector
    a_parameter = ajl_context["a_parameter"]
    a_inverse = 1 / a_parameter

    if is_inverse:
        return a_inverse * identity + a_parameter * temperley_lieb_generator

    return a_parameter * identity + a_inverse * temperley_lieb_generator


def _compute_braid_representation_matrix(parsed_braid: list[tuple[int, bool]], ajl_context: dict):
    import numpy as np

    representation_dimension = ajl_context["representation_dimension"]
    matrix = np.eye(representation_dimension, dtype=complex)

    for generator, is_inverse in parsed_braid:
        generator_matrix = _compute_generator_matrix(ajl_context, generator, is_inverse)
        matrix = generator_matrix @ matrix

    return matrix


def evaluate_jones_at_root_of_unity(
    braid_word: str,
    root_of_unity: int = DEFAULT_ROOT_OF_UNITY,
    closure_method: str = DEFAULT_CLOSURE_METHOD,
) -> complex:
    import numpy as np

    _validate_closure_method(closure_method)
    braid_analysis = validate_braid_problem_input(braid_word)
    ajl_context = _build_ajl_context(braid_analysis["strand_count"], root_of_unity)

    representation_matrix = _compute_braid_representation_matrix(
        braid_analysis["parsed_braid"],
        ajl_context,
    )

    weighted_trace = complex(
        np.dot(
            ajl_context["path_weights"],
            np.diag(representation_matrix),
        )
        / ajl_context["markov_normalizer"]
    )

    bracket_value = (ajl_context["d_parameter"] ** (braid_analysis["strand_count"] - 1)) * weighted_trace

    # The current invariant evaluation path uses the Markov trace closure for both request modes.
    _ = closure_method

    jones_value = ((-ajl_context["a_parameter"]) ** (-3 * braid_analysis["net_writhe"])) * bracket_value
    return complex(jones_value)


def _format_complex_value(value: complex, precision: int = 6) -> str:
    real_part = float(value.real)
    imaginary_part = float(value.imag)

    if abs(imaginary_part) < 10 ** (-(precision + 1)):
        return f"{real_part:.{precision}f}"

    sign = "+" if imaginary_part >= 0 else "-"
    return f"{real_part:.{precision}f} {sign} {abs(imaginary_part):.{precision}f}i"


def _format_jones_output(value: complex, root_of_unity: int) -> str:
    return f"V(t) = {_format_complex_value(value)} at t = exp(2*pi*i/{root_of_unity})"


def build_knot_circuit(
    braid_word: str,
    closure_method: str = DEFAULT_CLOSURE_METHOD,
    root_of_unity: int = DEFAULT_ROOT_OF_UNITY,
):
    from qiskit import QuantumCircuit

    _validate_closure_method(closure_method)
    braid_analysis = validate_braid_problem_input(braid_word)
    parsed_braid = braid_analysis["parsed_braid"]
    strand_count = braid_analysis["strand_count"]

    ajl_context = _build_ajl_context(strand_count, root_of_unity)
    work_qubits = ajl_context["work_qubits"]

    qc = QuantumCircuit(1 + work_qubits, 1)
    work_register = list(range(1, 1 + work_qubits))

    qc.h(0)

    for generator, is_inverse in parsed_braid:
        apply_braid_generator(
            qc,
            ancilla=0,
            work_register=work_register,
            generator=generator,
            is_inverse=is_inverse,
            ajl_context=ajl_context,
        )

    if closure_method == "trace":
        qc.h(0)
    else:
        qc.sdg(0)
        qc.h(0)

    qc.measure(0, 0)
    return qc


def _serialize_operation_counts(operation_counts):
    return {
        str(operation): int(count)
        for operation, count in sorted(
            operation_counts.items(),
            key=lambda item: str(item[0]),
        )
    }


def _count_two_qubit_gates(operation_counts: dict[str, int]):
    two_qubit_gate_names = {
        "cx",
        "cz",
        "cp",
        "swap",
        "ecr",
        "rzz",
        "rxx",
        "ryy",
        "iswap",
        "crx",
        "cry",
        "crz",
    }
    return sum(
        count
        for gate_name, count in operation_counts.items()
        if gate_name in two_qubit_gate_names
    )


def summarize_transpiled_circuit(
    transpiled_circuit,
    *,
    braid_word: str,
    optimization_level: int,
    closure_method: str,
):
    operation_counts = _serialize_operation_counts(transpiled_circuit.count_ops())
    depth = int(transpiled_circuit.depth() or 0)
    size = int(transpiled_circuit.size() or 0)
    width = int(transpiled_circuit.width() or 0)
    num_qubits = int(transpiled_circuit.num_qubits)
    num_clbits = int(transpiled_circuit.num_clbits)
    two_qubit_gate_count = _count_two_qubit_gates(operation_counts)
    measurement_count = int(operation_counts.get("measure", 0))

    signature_payload = {
        "braid_word": braid_word,
        "closure_method": closure_method,
        "optimization_level": optimization_level,
        "depth": depth,
        "size": size,
        "width": width,
        "num_qubits": num_qubits,
        "num_clbits": num_clbits,
        "two_qubit_gate_count": two_qubit_gate_count,
        "measurement_count": measurement_count,
        "operation_counts": operation_counts,
    }
    signature_source = json.dumps(signature_payload, sort_keys=True)
    signature = hashlib.sha256(signature_source.encode("utf-8")).hexdigest()[:16]

    return {
        "depth": depth,
        "size": size,
        "width": width,
        "num_qubits": num_qubits,
        "num_clbits": num_clbits,
        "two_qubit_gate_count": two_qubit_gate_count,
        "measurement_count": measurement_count,
        "operation_counts": operation_counts,
        "signature": signature,
    }


def generate_knot_circuit_artifact(
    braid_word: str,
    optimization_level: int = 3,
    closure_method: str = DEFAULT_CLOSURE_METHOD,
    target_backend: str | None = None,
):
    if optimization_level < 0 or optimization_level > 3:
        raise ValueError("Optimization level must be between 0 and 3.")
    _validate_closure_method(closure_method)
    validate_braid_problem_input(braid_word)

    from qiskit import transpile

    logical_circuit = build_knot_circuit(
        braid_word=braid_word,
        closure_method=closure_method,
    )
    transpiled_circuit = transpile(logical_circuit, optimization_level=optimization_level)
    circuit_summary = summarize_transpiled_circuit(
        transpiled_circuit,
        braid_word=braid_word,
        optimization_level=optimization_level,
        closure_method=closure_method,
    )

    return {
        "target_backend": target_backend or "unspecified",
        "optimization_level": optimization_level,
        "closure_method": closure_method,
        "braid_word": braid_word,
        "circuit_summary": circuit_summary,
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
    braid_word: str | None = None,
    closure_method: str = DEFAULT_CLOSURE_METHOD,
    root_of_unity: int = DEFAULT_ROOT_OF_UNITY,
):
    result = job.result()
    pub_result = result[0]
    counts = extract_counts_from_pub_result(pub_result)
    formatted_counts, expectation = _format_counts_and_expectation(counts)

    jones_value = None
    if braid_word:
        try:
            jones_value = evaluate_jones_at_root_of_unity(
                braid_word=braid_word,
                root_of_unity=root_of_unity,
                closure_method=closure_method,
            )
            jones_poly = _format_jones_output(jones_value, root_of_unity)
        except Exception:
            jones_poly = (
                "V(t) = unavailable: path model evaluation failed; "
                f"ancilla expectation={expectation:.6f}"
            )
    else:
        jones_poly = (
            "V(t) = unavailable: missing braid metadata for path model evaluation; "
            f"ancilla expectation={expectation:.6f}"
        )

    return {
        "job_id": resolve_job_id(job),
        "backend": backend_name_hint or resolve_job_backend_name(job) or "unknown",
        "runtime_channel_used": channel_used,
        "runtime_instance_used": runtime_instance,
        "counts": formatted_counts,
        "expectation_value": expectation,
        "jones_polynomial": jones_poly,
        "jones_value_real": float(jones_value.real) if jones_value is not None else None,
        "jones_value_imag": float(jones_value.imag) if jones_value is not None else None,
        "jones_root_of_unity": root_of_unity,
        "status": "COMPLETED",
    }


def _build_and_submit_knot_job(
    token: str,
    backend_name: str,
    braid_word: str,
    shots: int,
    optimization_level: int = 3,
    closure_method: str = DEFAULT_CLOSURE_METHOD,
    runtime_channel: str | None = None,
    runtime_instance: str | None = None,
):
    from qiskit import transpile
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler

    _validate_closure_method(closure_method)
    braid_analysis = validate_braid_problem_input(braid_word)

    service, channel_used = create_runtime_service(
        QiskitRuntimeService=QiskitRuntimeService,
        token=token,
        runtime_channel=runtime_channel,
        runtime_instance=runtime_instance,
    )

    backend = select_backend(service, backend_name)
    backend_num_qubits = resolve_backend_num_qubits(backend)
    required_qubits = braid_analysis["required_qubits"]
    if backend_num_qubits is not None and backend_num_qubits < required_qubits:
        raise ValueError(
            f"Selected backend '{resolve_backend_name(backend)}' has {backend_num_qubits} qubits, "
            f"but the braid word requires at least {required_qubits} qubits."
        )
    logical_circuit = build_knot_circuit(
        braid_word=braid_word,
        closure_method=closure_method,
    )
    transpiled_qc = transpile(logical_circuit, backend=backend, optimization_level=optimization_level)
    circuit_summary = summarize_transpiled_circuit(
        transpiled_qc,
        braid_word=braid_word,
        optimization_level=optimization_level,
        closure_method=closure_method,
    )
    sampler = create_sampler_for_backend(Sampler, backend)
    job = sampler.run([transpiled_qc], shots=shots)

    return job, backend, channel_used, circuit_summary


def apply_braid_generator(
    qc: QuantumCircuit,
    ancilla: int,
    work_register: list[int],
    generator: int,
    is_inverse: bool,
    ajl_context: dict,
):
    """
    Apply a controlled braid generator using the path model representation.
    """
    import numpy as np
    from qiskit.circuit.library import UnitaryGate

    if generator < 1:
        raise ValueError(f"Unsupported braid generator index: s{generator}")

    generator_matrix = _compute_generator_matrix(ajl_context, generator, is_inverse)

    work_qubit_count = len(work_register)
    full_dimension = 1 << work_qubit_count
    representation_dimension = ajl_context["representation_dimension"]

    embedded_unitary = np.eye(full_dimension, dtype=complex)
    embedded_unitary[:representation_dimension, :representation_dimension] = generator_matrix

    gate_label = f"s{generator}{'^-1' if is_inverse else ''}"
    controlled_gate = UnitaryGate(embedded_unitary, label=gate_label).control(1)
    qc.append(controlled_gate, [ancilla, *work_register])


def submit_knot_experiment(
    token: str,
    backend_name: str,
    braid_word: str,
    shots: int,
    optimization_level: int = 3,
    closure_method: str = DEFAULT_CLOSURE_METHOD,
    runtime_channel: str | None = None,
    runtime_instance: str | None = None,
):
    job, backend, channel_used, circuit_summary = _build_and_submit_knot_job(
        token=token,
        backend_name=backend_name,
        braid_word=braid_word,
        shots=shots,
        optimization_level=optimization_level,
        closure_method=closure_method,
        runtime_channel=runtime_channel,
        runtime_instance=runtime_instance,
    )

    job_id = resolve_job_id(job)
    _runtime_job_metadata_store[job_id] = {
        "braid_word": braid_word,
        "closure_method": closure_method,
        "root_of_unity": DEFAULT_ROOT_OF_UNITY,
    }

    status = resolve_job_status(job)
    if status == "UNKNOWN":
        status = "SUBMITTED"

    return {
        "job_id": job_id,
        "backend": resolve_backend_name(backend),
        "runtime_channel_used": channel_used,
        "runtime_instance_used": runtime_instance,
        "closure_method": closure_method,
        "circuit_summary": circuit_summary,
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

    resolved_job_id = resolve_job_id(job)
    status = resolve_job_status(job)
    backend_name = resolve_job_backend_name(job)

    if status in FAILED_JOB_STATUSES:
        error_message = resolve_job_error_message(job)
        response = {
            "job_id": resolved_job_id,
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
            "job_id": resolved_job_id,
            "backend": backend_name or "unknown",
            "runtime_channel_used": channel_used,
            "runtime_instance_used": runtime_instance,
            "status": status,
        }

    runtime_metadata = _runtime_job_metadata_store.get(resolved_job_id, {})

    try:
        completed_result = format_completed_job_result(
            job=job,
            channel_used=channel_used,
            runtime_instance=runtime_instance,
            backend_name_hint=backend_name,
            braid_word=runtime_metadata.get("braid_word"),
            closure_method=runtime_metadata.get("closure_method", DEFAULT_CLOSURE_METHOD),
            root_of_unity=runtime_metadata.get("root_of_unity", DEFAULT_ROOT_OF_UNITY),
        )
        _runtime_job_metadata_store.pop(resolved_job_id, None)
        return completed_result
    except Exception as exc:
        if status and status not in COMPLETED_JOB_STATUSES:
            return {
                "job_id": resolved_job_id,
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
    closure_method: str = DEFAULT_CLOSURE_METHOD,
    runtime_channel: str | None = None,
    runtime_instance: str | None = None,
):
    """
    Submits a knot evaluation circuit to IBM Quantum hardware using Qiskit Runtime.
    """
    job, backend, channel_used, _ = _build_and_submit_knot_job(
        token=token,
        backend_name=backend_name,
        braid_word=braid_word,
        shots=shots,
        optimization_level=optimization_level,
        closure_method=closure_method,
        runtime_channel=runtime_channel,
        runtime_instance=runtime_instance,
    )

    return format_completed_job_result(
        job=job,
        channel_used=channel_used,
        runtime_instance=runtime_instance,
        backend_name_hint=resolve_backend_name(backend),
        braid_word=braid_word,
        closure_method=closure_method,
        root_of_unity=DEFAULT_ROOT_OF_UNITY,
    )


def run_simulator_experiment(
    braid_word: str,
    shots: int,
    optimization_level: int = 3,
    closure_method: str = DEFAULT_CLOSURE_METHOD,
) -> dict:
    """
    Runs a knot evaluation circuit locally using Qiskit's StatevectorSampler.
    No IBM token or network access required. Results are stored in-process and
    retrievable via get_simulator_result().
    """
    import uuid
    from qiskit import transpile
    from qiskit.primitives import StatevectorSampler

    _validate_closure_method(closure_method)
    braid_analysis = validate_braid_problem_input(braid_word)

    logical_circuit = build_knot_circuit(braid_word=braid_word, closure_method=closure_method)
    transpiled_circuit = transpile(logical_circuit, optimization_level=optimization_level)
    circuit_summary = summarize_transpiled_circuit(
        transpiled_circuit,
        braid_word=braid_word,
        optimization_level=optimization_level,
        closure_method=closure_method,
    )

    sampler = StatevectorSampler()
    primitive_result = sampler.run([(transpiled_circuit,)], shots=shots).result()
    pub_result = primitive_result[0]
    counts = extract_counts_from_pub_result(pub_result)
    formatted_counts, expectation = _format_counts_and_expectation(counts)

    jones_value = None
    try:
        jones_value = evaluate_jones_at_root_of_unity(
            braid_word=braid_word,
            root_of_unity=DEFAULT_ROOT_OF_UNITY,
            closure_method=closure_method,
        )
        jones_poly = _format_jones_output(jones_value, DEFAULT_ROOT_OF_UNITY)
    except Exception:
        jones_poly = (
            "V(t) = unavailable: path model evaluation failed; "
            f"ancilla expectation={expectation:.6f}"
        )

    job_id = f"{_SIM_JOB_ID_PREFIX}{uuid.uuid4().hex[:12]}"

    _simulator_result_store[job_id] = {
        "job_id": job_id,
        "backend": SIMULATOR_BACKEND_NAME,
        "runtime_channel_used": None,
        "runtime_instance_used": None,
        "counts": formatted_counts,
        "expectation_value": expectation,
        "jones_polynomial": jones_poly,
        "jones_value_real": float(jones_value.real) if jones_value is not None else None,
        "jones_value_imag": float(jones_value.imag) if jones_value is not None else None,
        "jones_root_of_unity": DEFAULT_ROOT_OF_UNITY,
        "status": "COMPLETED",
    }

    _ = braid_analysis  # used for validation only

    return {
        "job_id": job_id,
        "backend": SIMULATOR_BACKEND_NAME,
        "runtime_channel_used": None,
        "runtime_instance_used": None,
        "closure_method": closure_method,
        "circuit_summary": circuit_summary,
        "status": "SUBMITTED",
    }


def get_simulator_result(job_id: str) -> dict:
    """
    Retrieves a previously computed simulator result by job ID.
    Raises ValueError if the job ID is not found in the in-process store.
    """
    result = _simulator_result_store.get(job_id)
    if result is None:
        raise ValueError(f"No simulator result found for job '{job_id}'.")
    return result
