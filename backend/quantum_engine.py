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
ZNE_SCALE_FACTORS = (1, 3, 5)
MULTI_K_ROOTS = (5, 7, 9)

SIMULATOR_BACKEND_NAME = "qiskit_simulator"
_SIM_JOB_ID_PREFIX = "sim-"
_simulator_result_store: dict[str, dict] = {}
_runtime_job_metadata_store: dict[str, dict] = {}
_knotinfo_catalog_cache: dict | None = None

# Catalog entries provide deterministic outputs for known notations.
# Catalog entries provide verified braid words for known knots.
# Braids verified against KnotInfo minimum representations and mathematical Jones values.
# Trefoil: T(3,2) 3-braid (= T(2,3), right-handed), V(exp(2πi/5)) = -0.809017 + 1.314328i
# Figure-eight: KnotInfo minimum braid, V(exp(2πi/5)) = -1.236068 (= 1 - √5, real, amphichiral)
# Cinquefoil: Markov stabilization of σ₁⁵, V(exp(2πi/5)) = -0.381966 (= -1/φ², real)
_DOWKER_BRAID_CATALOG = {
    (4, 6, 2): {
        "knot_name": "Trefoil Knot (3_1)",
        "braid_word": "s1 s2 s1 s2",
        "root_of_unity": 5,
        "homfly_pt": "(2*v^2-v^4)+(v^2)*z^2",
    },
    (4, 6, 8, 2): {
        "knot_name": "Figure-Eight Knot (4_1)",
        "braid_word": "s1 s2^-1 s1 s2^-1",
        "root_of_unity": 5,
        "homfly_pt": "(v^(-2)-1+v^2)+(-1)*z^2",
    },
    (6, 8, 10, 2, 4): {
        "knot_name": "Cinquefoil Knot (5_1)",
        "braid_word": "s1 s1 s1 s1 s1 s2",
        "root_of_unity": 5,
        "homfly_pt": "(3*v^4-2*v^6)+(4*v^4-v^6)*z^2+(v^4)*z^4",
    },
}


def _parse_knotinfo_braid_notation(notation: str) -> str:
    """Convert KnotInfo braid notation to Q-Knot sN/sN^-1 format.

    Accepts '{1,-2,1,-2}' or 'BR(n, {1,-2,1,-2})'. Positive n → sN, negative -n → sN^-1.
    """
    # Strip BR(n, {...}) wrapper if present
    notation = re.sub(r"^BR\(\d+,\s*", "", notation.strip()).rstrip(")")
    notation = notation.strip().lstrip("{").rstrip("}")
    tokens = []
    for part in notation.split(","):
        part = part.strip()
        if not part:
            continue
        n = int(part)
        if n > 0:
            tokens.append(f"s{n}")
        else:
            tokens.append(f"s{-n}^-1")
    if not tokens:
        raise ValueError(f"Empty braid notation from KnotInfo: {notation!r}")
    return " ".join(tokens)


def _parse_knotinfo_dt_key(dt_raw: str) -> tuple | None:
    """Convert KnotInfo DT notation string to normalized abs-value tuple catalog key.

    Accepts '[4, 6, 2]' format. Returns None if unparseable.
    """
    dt_raw = dt_raw.strip().lstrip("[{").rstrip("]}]")
    dt_raw = dt_raw.replace(",", " ")
    parts = dt_raw.split()
    if not parts:
        return None
    try:
        values = tuple(abs(int(p)) for p in parts if p)
    except ValueError:
        return None
    return values if values else None


def _load_knotinfo_catalog() -> dict:
    """Lazily load the KnotInfo database and index by normalized DT tuple.

    Returns {} if database_knotinfo is not installed.
    Cached after first call.
    """
    global _knotinfo_catalog_cache
    if _knotinfo_catalog_cache is not None:
        return _knotinfo_catalog_cache

    try:
        from database_knotinfo import link_list
    except ImportError:
        _knotinfo_catalog_cache = {}
        return _knotinfo_catalog_cache

    catalog = {}
    rows = link_list()
    for row in rows[1:]:
        try:
            dt_raw = row.get("dt_notation", "")
            braid_raw = row.get("braid_notation", "")
            if not dt_raw or not braid_raw:
                continue
            dt_key = _parse_knotinfo_dt_key(dt_raw)
            if dt_key is None:
                continue
            braid_word = _parse_knotinfo_braid_notation(braid_raw)
            homfly_raw = row.get("homfly_polynomial") or None
            catalog[dt_key] = {
                "knot_name": row.get("name", ""),
                "braid_word": braid_word,
                "braid_index": int(row["braid_index"]) if row.get("braid_index") else None,
                "root_of_unity": DEFAULT_ROOT_OF_UNITY,
                "homfly_pt": homfly_raw if homfly_raw else None,
            }
        except Exception:
            continue

    _knotinfo_catalog_cache = catalog
    return catalog


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

    # Tier 1: hardcoded catalog (Phase 8 verified entries, fast path)
    catalog_entry = _DOWKER_BRAID_CATALOG.get(absolute_key)
    if catalog_entry:
        return {
            "dowker_notation_normalized": " ".join(str(token) for token in parsed_tokens),
            "crossing_count": len(parsed_tokens),
            "knot_name": catalog_entry["knot_name"],
            "braid_word": catalog_entry["braid_word"],
            "braid_index": None,
            "root_of_unity": catalog_entry["root_of_unity"],
            "homfly_pt": catalog_entry.get("homfly_pt"),
            "is_catalog_match": True,
        }

    # Tier 2: KnotInfo database (2,979 knots up to 13+ crossings, minimum braid words)
    knotinfo_entry = _load_knotinfo_catalog().get(absolute_key)
    if knotinfo_entry:
        return {
            "dowker_notation_normalized": " ".join(str(token) for token in parsed_tokens),
            "crossing_count": len(parsed_tokens),
            "knot_name": knotinfo_entry["knot_name"],
            "braid_word": knotinfo_entry["braid_word"],
            "braid_index": knotinfo_entry["braid_index"],
            "root_of_unity": knotinfo_entry["root_of_unity"],
            "homfly_pt": knotinfo_entry.get("homfly_pt"),
            "is_catalog_match": True,
        }

    # Tier 3: deterministic fallback (topological correctness not guaranteed)
    return {
        "dowker_notation_normalized": " ".join(str(token) for token in parsed_tokens),
        "crossing_count": len(parsed_tokens),
        "knot_name": f"Dowker Knot ({len(parsed_tokens)} crossings)",
        "braid_word": _compile_tokens_to_braid(parsed_tokens),
        "braid_index": None,
        "root_of_unity": DEFAULT_ROOT_OF_UNITY,
        "homfly_pt": None,
        "is_catalog_match": False,
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

    # The TL generator satisfies P^2 = d*P. The braid relation requires
    # a^2 + a^{-2} = -d, which holds for a = i*exp(-i*pi/(2k)).
    # Correct formula: rho(sigma_i) = a*I + a^{-1}*P  (unitary, inverse of rho(sigma_i^{-1})).
    a_parameter = ajl_context["a_parameter"]
    a_inverse = 1 / a_parameter

    if is_inverse:
        return a_inverse * identity + a_parameter * projector

    return a_parameter * identity + a_inverse * projector


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


def evaluate_jones_multi_k(
    braid_word: str,
    roots_of_unity: tuple[int, ...] = MULTI_K_ROOTS,
) -> list[dict]:
    """Evaluate the Jones polynomial at multiple roots of unity.

    Returns a list of dicts [{k, real, imag, polynomial}] for each valid k.
    Even k values and k < 5 are skipped (degenerate path model representations).
    Individual k failures are skipped silently.
    """
    results = []
    for k in roots_of_unity:
        if k < 5 or k % 2 == 0:
            continue
        try:
            value = evaluate_jones_at_root_of_unity(braid_word, root_of_unity=k)
            results.append({
                "k": k,
                "real": round(float(value.real), 8),
                "imag": round(float(value.imag), 8),
                "polynomial": _format_jones_output(value, k),
            })
        except Exception:
            pass
    return results


def _hecke_right_multiply(
    element: dict, i: int, is_inverse: bool, q: complex, z: complex
) -> dict:
    """Right-multiply a Hecke element by T_i or T_i^{-1} (0-indexed generator).

    element: {permutation_tuple: complex_coeff}
    Rules (T_i^2 = q + z*T_i, T_i^{-1} = (T_i - z)/q):
      T_w * T_i  length+: T_{w*si}
      T_w * T_i  length-: z*T_w + q*T_{w*si}
      T_w * T_i^{-1} length+: q^{-1}*T_{w*si} - (z/q)*T_w
      T_w * T_i^{-1} length-: T_{w*si}
    """
    result: dict = {}
    for w, coeff in element.items():
        w_list = list(w)
        w_list[i], w_list[i + 1] = w_list[i + 1], w_list[i]
        w_si = tuple(w_list)
        length_increases = w[i] < w[i + 1]
        if not is_inverse:
            if length_increases:
                result[w_si] = result.get(w_si, 0) + coeff
            else:
                result[w] = result.get(w, 0) + coeff * z
                result[w_si] = result.get(w_si, 0) + coeff * q
        else:
            if length_increases:
                result[w_si] = result.get(w_si, 0) + coeff / q
                result[w] = result.get(w, 0) - coeff * z / q
            else:
                result[w_si] = result.get(w_si, 0) + coeff
    return result


def _hecke_trace_basis(w: tuple, q: complex, z: complex) -> complex:
    """Compute the Ocneanu trace tr_n(T_w) for a permutation basis element.

    Left-coset decomposition: w = D_k * u, D_k = cycle(k,...,n-1), u in S_{n-1},
    k = w[n-1].
      k == n-1: tr_n(T_w) = (1-q)/z * tr_{n-1}(T_{w[:n-1]})
      k <  n-1: tr_n(T_w) = tr_{n-1}(T_u * T_k * ... * T_{n-3})
    """
    n = len(w)
    if n == 1:
        return complex(1)
    k = w[n - 1]
    if k == n - 1:
        return (1 - q) / z * _hecke_trace_basis(w[: n - 1], q, z)
    # D_k^{-1}: v->n-1 if v==k; v->v-1 if k<v<=n-1; v->v if v<k
    u = tuple((n - 1 if v == k else v - 1 if k < v <= n - 1 else v) for v in w)
    u_restricted = u[: n - 1]
    sub: dict = {u_restricted: complex(1)}
    for idx in range(k, n - 2):
        sub = _hecke_right_multiply(sub, idx, False, q, z)
    return _hecke_trace(sub, q, z)


def _hecke_trace(element: dict, q: complex, z: complex) -> complex:
    """Compute the Ocneanu trace of a Hecke element in the permutation basis."""
    return sum(coeff * _hecke_trace_basis(w, q, z) for w, coeff in element.items())


def _build_hecke_context(strand_count: int, q_val: complex, z_param: complex) -> dict:
    """Build context dict for Hecke algebra H_n with given parameters.

    strand_count: number of braid strands (n).
    q_val, z_param: two-parameter Hecke algebra (T_i^2 = q + z*T_i).
    Permutation basis has dimension n!.
    """
    return {
        "strand_count": strand_count,
        "q": q_val,
        "z": z_param,
        "identity": tuple(range(strand_count)),
    }


def _compute_hecke_generator_matrix(
    context: dict, generator: int, is_inverse: bool
) -> dict:
    """Return the Hecke element T_{generator}^{+/-1} in the permutation basis.

    generator: 1-indexed (s1, s2, ...) matching braid_word convention.
    """
    n = context["strand_count"]
    i = generator - 1
    if i < 0 or i >= n - 1:
        raise ValueError(f"Generator s{generator} out of range for {n}-strand braid.")
    element: dict = {context["identity"]: complex(1)}
    return _hecke_right_multiply(element, i, is_inverse, context["q"], context["z"])


def _compute_hecke_braid_matrix(parsed_braid: list, context: dict) -> dict:
    """Compute the Hecke algebra element for a full braid word.

    parsed_braid: list of (generator, is_inverse) pairs (1-indexed generators).
    Returns element dict in the permutation basis.
    """
    element: dict = {context["identity"]: complex(1)}
    for generator, is_inverse in parsed_braid:
        i = generator - 1
        element = _hecke_right_multiply(element, i, is_inverse, context["q"], context["z"])
    return element


def _evaluate_homfly_string(homfly_str: str, v_val: complex, z_val: complex) -> complex:
    """Numerically evaluate a KnotInfo HOMFLY-PT string at specific (v, z) values.

    KnotInfo strings use '^' for exponentiation, e.g. '(2*v^2-v^4)+(v^2)*z^2'.
    """
    expr = homfly_str.replace("^", "**")
    return complex(eval(expr, {"__builtins__": {}, "v": v_val, "z": z_val}))  # noqa: S307


def evaluate_homfly_at_q(
    braid_word: str,
    root_of_unity: int = DEFAULT_ROOT_OF_UNITY,
) -> dict:
    """Evaluate HOMFLY-PT numerically via Hecke algebra Ocneanu trace.

    Representation: H_n(q) two-parameter permutation basis.
    Convention (KnotInfo): v^{-1}*P(L+) - v*P(L-) = z*P(L0).
    Evaluation point: v = exp(pi*i/k), z_homfly = 1.
    Hecke parameters: q_hecke = v^2 = exp(2*pi*i/k), z_param = v * z_homfly.

    Returns dict with 'real', 'imag', evaluation-point metadata.
    """
    import cmath

    parsed_braid = parse_braid_word(braid_word)
    strand_count = max(gen for gen, _ in parsed_braid) + 1

    v_val = cmath.exp(1j * cmath.pi / root_of_unity)
    q_hecke = v_val ** 2
    z_param = v_val * complex(1)  # z_homfly = 1

    context = _build_hecke_context(strand_count, q_hecke, z_param)
    element = _compute_hecke_braid_matrix(parsed_braid, context)
    homfly_val = _hecke_trace(element, q_hecke, z_param)

    return {
        "real": round(float(homfly_val.real), 8),
        "imag": round(float(homfly_val.imag), 8),
        "v_val_real": round(float(v_val.real), 8),
        "v_val_imag": round(float(v_val.imag), 8),
        "z_homfly": 1,
        "q_hecke_real": round(float(q_hecke.real), 8),
        "q_hecke_imag": round(float(q_hecke.imag), 8),
        "root_of_unity": root_of_unity,
    }


# ---------------------------------------------------------------------------
# Phase 10b: sl_N colored HOMFLY-PT via quantum group R-matrix
# ---------------------------------------------------------------------------

def _sln_quantum_dim(sl_n: int, q_val: complex) -> complex:
    """Quantum dimension [N]_q = q^{N-1} + q^{N-3} + ... + q^{-(N-1)}."""
    return complex(sum(q_val ** (sl_n - 1 - 2 * j) for j in range(sl_n)))


def _build_sln_swap(sl_n: int):
    """SWAP matrix on C^N ⊗ C^N. Maps |i,j> -> |j,i>."""
    import numpy as np
    n_sq = sl_n * sl_n
    S = np.zeros((n_sq, n_sq), dtype=complex)
    for i in range(sl_n):
        for j in range(sl_n):
            S[j * sl_n + i, i * sl_n + j] = 1.0
    return S


def _build_sln_r_matrix(sl_n: int, q_val: complex):
    """Unitary R-matrix for sl_N fundamental representation on C^N ⊗ C^N.

    R = i*sin(θ)*I + cos(θ)*SWAP  where q = exp(iθ).
    Hecke eigenvalues: q on Sym²(C^N), -q^{-1} on Λ²(C^N).
    Unitary: R†R = I when |q|=1 (roots of unity).
    Satisfies the Hecke relation (R-q)(R+q^{-1}) = 0 with z = q - q^{-1}.
    """
    import numpy as np
    cos_t = (q_val + complex(1) / q_val) / 2   # (q + q^{-1})/2 = cos(θ)
    isin_t = (q_val - complex(1) / q_val) / 2  # (q - q^{-1})/2 = i*sin(θ)
    n_sq = sl_n * sl_n
    return isin_t * np.eye(n_sq, dtype=complex) + cos_t * _build_sln_swap(sl_n)


def _build_sln_std_r_matrix(sl_n: int, q_val: complex):
    """Standard (non-unitary) quantum group R-matrix for U_q(gl_N).

    R|ij> = q|ij>              if i = j  (diagonal)
    R|ij> = |ji>               if i < j  (SWAP, no factor)
    R|ij> = (q-q^{-1})|ij>+|ji>  if i > j  (Hecke off-diagonal)

    Eigenvalues: q on Sym^2(C^N), -q^{-1} on Lambda^2(C^N).
    Satisfies the Hecke relation (R-q)(R+q^{-1}) = 0.
    Not unitary at roots of unity; use _build_sln_r_matrix for quantum circuits.
    """
    import numpy as np
    n2 = sl_n * sl_n
    R = np.zeros((n2, n2), dtype=complex)
    for i in range(sl_n):
        for j in range(sl_n):
            col = i * sl_n + j          # column = input |ij>
            if i == j:
                R[col, col] = q_val
            elif i < j:
                R[j * sl_n + i, col] = 1.0
            else:                       # i > j
                R[j * sl_n + i, col] = 1.0
                R[col, col] = q_val - 1.0 / q_val
    return R


def _embed_two_site_gate(op, site_i: int, n_sites: int, sl_n: int):
    """Embed an N^2 x N^2 gate on sites (site_i, site_i+1) into the N^n space."""
    import numpy as np
    before = np.eye(sl_n ** site_i, dtype=complex)
    after_pow = n_sites - site_i - 2
    after = np.eye(sl_n ** after_pow, dtype=complex) if after_pow > 0 else np.eye(1, dtype=complex)
    return np.kron(np.kron(before, op), after)


def _build_sln_braid_unitary(braid_word: str, sl_n: int, q_val: complex):
    """Build the N^n x N^n unitary for the braid in the sl_N fundamental representation.

    Returns (U, n_strands). U is the ordered product of R-matrices,
    one per crossing. R_inv = R† since R is unitary.
    """
    import numpy as np
    parsed = parse_braid_word(braid_word)
    n_strands = max(gen for gen, _ in parsed) + 1
    dim = sl_n ** n_strands
    U = np.eye(dim, dtype=complex)
    R = _build_sln_r_matrix(sl_n, q_val)
    R_inv = R.conj().T
    for gen, is_inv in parsed:
        mat = R_inv if is_inv else R
        full = _embed_two_site_gate(mat, gen - 1, n_strands, sl_n)
        U = full @ U
    return U, n_strands


def _sln_quantum_trace(U, sl_n: int, n_strands: int, q_val: complex) -> complex:
    """Quantum trace tr_q(U) = tr(U * K^{⊗n}) for sl_N.

    K = diag(q^{N-1}, q^{N-3}, ..., q^{-(N-1)}).
    tr_q(I) = [N]_q^n  (normalizes to the quantum dimension).
    """
    import numpy as np
    k_diag = np.array([q_val ** (sl_n - 1 - 2 * j) for j in range(sl_n)], dtype=complex)
    k_tensor = k_diag.copy()
    for _ in range(n_strands - 1):
        k_tensor = np.kron(k_tensor, k_diag)
    return complex(np.dot(np.diag(U), k_tensor))


def evaluate_homfly_sln(
    braid_word: str,
    sl_n: int = 3,
    root_of_unity: int = DEFAULT_ROOT_OF_UNITY,
) -> dict:
    """Evaluate HOMFLY-PT at the sl_N specialization via the quantum group R-matrix.

    Computes the Reshetikhin-Turaev invariant using the standard (non-unitary)
    quantum group R-matrix for U_q(sl_N), giving HOMFLY-PT evaluated at:

        v = q^N,   z = q - q^{-1},   q = exp(2*pi*i / root_of_unity)

    Reshetikhin-Turaev normalization:
        P(β̂) = conj(v^{-e} * tr_q(U_std) / [N]_q)
    where U_std is built from the standard (non-unitary) quantum group R-matrix,
    e = writhe(β), and [N]_q = q^{N-1} + ... + q^{-(N-1)}.

    For N=2 this gives the HOMFLY-PT sl_2 specialization.
    For N=3 this gives a new HOMFLY-PT slice inaccessible from Jones alone.

    Cross-check: values match _evaluate_homfly_string at (v=q^N, z=q-q^{-1}).
    Note: use build_sl3_hadamard_circuit for the unitary quantum circuit variant.
    """
    import cmath
    import numpy as np
    q_val = cmath.exp(2j * cmath.pi / root_of_unity)

    parsed = parse_braid_word(braid_word)
    n_strands = max(gen for gen, _ in parsed) + 1
    writhe = sum(-1 if inv else 1 for _, inv in parsed)

    # Build braid unitary with the standard (non-unitary) quantum group R-matrix
    R = _build_sln_std_r_matrix(sl_n, q_val)
    R_inv = np.linalg.inv(R)
    dim = sl_n ** n_strands
    U = np.eye(dim, dtype=complex)
    for gen, is_inv in parsed:
        mat = R_inv if is_inv else R
        full = _embed_two_site_gate(mat, gen - 1, n_strands, sl_n)
        U = full @ U

    v_val = q_val ** sl_n
    qd = _sln_quantum_dim(sl_n, q_val)
    raw_trace = _sln_quantum_trace(U, sl_n, n_strands, q_val)

    # Reshetikhin-Turaev normalization: P = conj(v^{-e} * tr_q(U_std) / [N]_q)
    homfly_val = complex(v_val ** (-writhe) * raw_trace / qd).conjugate()

    z_val = q_val - complex(1) / q_val
    return {
        "real": round(float(homfly_val.real), 8),
        "imag": round(float(homfly_val.imag), 8),
        "sl_n": sl_n,
        "root_of_unity": root_of_unity,
        "v_real": round(float(v_val.real), 8),
        "v_imag": round(float(v_val.imag), 8),
        "z_real": round(float(z_val.real), 8),
        "z_imag": round(float(z_val.imag), 8),
        "q_real": round(float(q_val.real), 8),
        "q_imag": round(float(q_val.imag), 8),
    }


def build_sl3_hadamard_circuit(
    braid_word: str,
    root_of_unity: int = DEFAULT_ROOT_OF_UNITY,
):
    """Build a Hadamard test circuit for the sl_3 HOMFLY-PT specialization.

    Each sl_3 qutrit (states 0,1,2) is encoded in 2 qubits:
        |0> -> |00>,  |1> -> |01>,  |2> -> |10>  (|11> unused per pair).

    The braid unitary U_braid acts on the qutrit subspace.  It is conjugated by
    K^{1/2} = diag(q, 1, q^{-1}) per qutrit, giving the K-modified unitary

        U' = K^{n/2} * U_braid * K^{n/2}

    so that the Hadamard test measures Re(<0|U'|0>) where |0> is the qutrit
    ground state.  This diagonal element contributes to the sl_3 quantum trace.

    Circuit layout:
        q0          — ancilla (Hadamard test qubit)
        q1..q_{2n}  — data qubits (2 qubits per strand, qutrit encoding)
    Total qubits: 2*n_strands + 1.

    The ancilla expectation value <Z> relates to the HOMFLY trace as:
        <Z> = Re(<0|U'|0>) = Re(K_0^n * U_{0,0}) / |K_0|^n = Re(U'_{0,0})
    """
    import cmath
    import numpy as np
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import UnitaryGate

    sl_n = 3
    q_val = cmath.exp(2j * cmath.pi / root_of_unity)

    parsed = parse_braid_word(braid_word)
    n_strands = max(gen for gen, _ in parsed) + 1

    U_qutrit, _ = _build_sln_braid_unitary(braid_word, sl_n, q_val)
    dim_qutrit = sl_n ** n_strands

    # K^{1/2} per qutrit: diag(q^{(N-1-2j)/2}) = diag(q, 1, q^{-1}) for N=3
    k_half_diag = np.array(
        [q_val ** ((sl_n - 1 - 2 * j) / 2) for j in range(sl_n)], dtype=complex
    )
    k_half_tensor = k_half_diag.copy()
    for _ in range(n_strands - 1):
        k_half_tensor = np.kron(k_half_tensor, k_half_diag)
    K_half = np.diag(k_half_tensor)

    # K-conjugated braid unitary: U' = K^{n/2} @ U @ K^{n/2}
    U_prime = K_half @ U_qutrit @ K_half

    # Qutrit digit d in {0,1,2} -> 2-qubit state |d> (binary, 2 bits)
    # Composite qutrit index -> composite qubit index (2 bits per qutrit, big-endian)
    def qutrit_to_qubit_idx(qutrit_idx: int) -> int:
        digits, q = [], qutrit_idx
        for _ in range(n_strands):
            digits.append(q % sl_n)
            q //= sl_n
        digits.reverse()
        idx = 0
        for d in digits:
            idx = idx * 4 + d
        return idx

    valid_qubit_indices = [qutrit_to_qubit_idx(i) for i in range(dim_qutrit)]

    # Embed U' into the 2^{2n} qubit space; invalid |11> states act as identity
    n_data_qubits = 2 * n_strands
    dim_qubit = 1 << n_data_qubits
    U_qubit = np.eye(dim_qubit, dtype=complex)
    for i in range(dim_qutrit):
        for j in range(dim_qutrit):
            U_qubit[valid_qubit_indices[i], valid_qubit_indices[j]] = U_prime[i, j]

    # Hadamard test circuit: ancilla=q0, data=q1..q_{n_data_qubits}
    # Data starts in |0> (qutrit ground state = qubit |00...00>)
    n_qubits = 1 + n_data_qubits
    qc = QuantumCircuit(n_qubits, 1)
    qc.h(0)
    gate_label = f"sl3_U_k{root_of_unity}"
    controlled_gate = UnitaryGate(U_qubit, label=gate_label).control(1)
    qc.append(controlled_gate, list(range(n_qubits)))
    qc.h(0)
    qc.measure(0, 0)
    return qc


def _compute_sl3_classical_reference(
    braid_word: str,
    root_of_unity: int = DEFAULT_ROOT_OF_UNITY,
) -> float:
    """Classical noiseless reference for the sl_3 Hadamard circuit.

    Returns Re(U'[0,0]) where U' = K^{n/2} @ U_braid @ K^{n/2} is the
    K-conjugated sl_3 braid unitary used in build_sl3_hadamard_circuit.
    This is the ideal value the Hadamard test ancilla expectation would
    measure without noise.
    """
    import cmath
    import numpy as np

    sl_n = 3
    q_val = cmath.exp(2j * cmath.pi / root_of_unity)
    parsed = parse_braid_word(braid_word)
    n_strands = max(gen for gen, _ in parsed) + 1
    U_qutrit, _ = _build_sln_braid_unitary(braid_word, sl_n, q_val)
    k_half_diag = np.array(
        [q_val ** ((sl_n - 1 - 2 * j) / 2) for j in range(sl_n)], dtype=complex
    )
    k_half_tensor = k_half_diag.copy()
    for _ in range(n_strands - 1):
        k_half_tensor = np.kron(k_half_tensor, k_half_diag)
    K_half = np.diag(k_half_tensor)
    U_prime = K_half @ U_qutrit @ K_half
    return float(U_prime[0, 0].real)


def _embed_r_for_pergenerator(R_9x9):
    """Embed a 9×9 qutrit R-matrix into a 16×16 qubit matrix.

    Encoding: qutrit state j → two qubits with Qiskit little-endian index j.
    For [d_low, d_high] register, qubit index = d_low + 2*d_high.
    In the 4-qubit two-qutrit space, qubit_col = i_in + 4*j_in where
    i_in, j_in ∈ {0,1,2} are left/right qutrit indices.
    """
    import numpy as np

    R_16 = np.eye(16, dtype=complex)
    for i_in in range(3):
        for j_in in range(3):
            qubit_col = i_in + 4 * j_in
            for i_out in range(3):
                for j_out in range(3):
                    qubit_row = i_out + 4 * j_out
                    R_16[qubit_row, qubit_col] = R_9x9[i_out * 3 + j_out, i_in * 3 + j_in]
    return R_16


def build_sl3_hadamard_circuit_pergenerator(
    braid_word: str,
    root_of_unity: int = DEFAULT_ROOT_OF_UNITY,
):
    """Per-generator Hadamard circuit for sl_3 representation.

    Instead of one large controlled-U for the full braid, applies one
    controlled-R (or R†) per crossing. Measures the same observable as
    build_sl3_hadamard_circuit: Re(q^{2n} U_braid[0,0]) = Re(U'[0,0])
    where U' = K^{n/2} U_braid K^{n/2}.

    The K_half_start factor K^{n/2}|0⟩ = q^n|0⟩ is a global phase on the
    ground state, implemented as a Phase gate on the ancilla qubit.
    K_half_end is applied as a per-qutrit controlled diagonal gate after
    the final R gate.

    Circuit layout: q0=ancilla, q1..q_{2n}=data (2 qubits per qutrit,
    Qiskit little-endian: qutrit j → qubits 2j+1 (low), 2j+2 (high)).
    """
    import cmath
    import math

    import numpy as np
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import UnitaryGate

    sl_n = 3
    q_val = cmath.exp(2j * cmath.pi / root_of_unity)
    parsed = parse_braid_word(braid_word)
    n_strands = max(gen for gen, _ in parsed) + 1

    R = _build_sln_r_matrix(sl_n, q_val)
    R_inv = R.conj().T
    R_emb = _embed_r_for_pergenerator(R)
    R_inv_emb = _embed_r_for_pergenerator(R_inv)

    ctrl_R = UnitaryGate(R_emb, label="R_sl3").control(1)
    ctrl_R_inv = UnitaryGate(R_inv_emb, label="R†_sl3").control(1)

    # K_half diagonal for one qutrit in qubit space: diag(q^1, q^0, q^{-1}, q^0)
    # (the j=0,1,2 qutrit states map to qubit indices 0,1,2; index 3 is unused)
    k_half_diag = np.diag([q_val, 1.0, 1.0 / q_val, 1.0])
    ctrl_k_half = UnitaryGate(k_half_diag, label="K½").control(1)

    n_data_qubits = 2 * n_strands
    n_qubits = 1 + n_data_qubits
    qc = QuantumCircuit(n_qubits, 1)

    # Hadamard on ancilla
    qc.h(0)

    # K_half_start: K_half|0⟩ = q^{(N-1)/2}|0⟩ = q^1|0⟩ for N=3.
    # The full n-strand tensor product on |0...0⟩ gives q^n global phase.
    # Implemented as Phase gate on ancilla to pick up the relative phase.
    qc.p(2 * math.pi * n_strands / root_of_unity, 0)

    # One controlled-R per crossing
    for gen, is_inv in parsed:
        gate = ctrl_R_inv if is_inv else ctrl_R
        # Generator σ_gen acts on strands gen and gen+1 (1-indexed).
        # Qubits: strand s → qubits 2s-1 (low), 2s (high).
        q_low_left = 2 * gen - 1
        q_high_left = 2 * gen
        q_low_right = 2 * gen + 1
        q_high_right = 2 * gen + 2
        qc.append(gate, [0, q_low_left, q_high_left, q_low_right, q_high_right])

    # K_half_end: per-qutrit controlled diagonal
    for j in range(n_strands):
        qc.append(ctrl_k_half, [0, 2 * j + 1, 2 * j + 2])

    # Second Hadamard and measure
    qc.h(0)
    qc.measure(0, 0)

    return qc


def _format_completed_sl3_result(
    job,
    channel_used: str | None,
    runtime_instance: str | None,
    braid_word: str | None,
    root_of_unity: int,
    backend_name_hint: str | None = None,
    zne_scale_factors: tuple = ZNE_SCALE_FACTORS,
) -> dict:
    """Format a completed IBM hardware sl_3 Hadamard circuit result.

    Expects one pub result per ZNE scale factor. Applies Richardson
    extrapolation to the Hadamard expectation values across noise levels.
    """
    result = job.result()

    raw_expectations = []
    for i in range(len(zne_scale_factors)):
        try:
            counts_i = extract_counts_from_pub_result(result[i])
            _, exp_i = _format_counts_and_expectation(counts_i)
            raw_expectations.append(exp_i)
        except Exception:
            raw_expectations.append(None)

    counts = extract_counts_from_pub_result(result[0])
    formatted_counts, expectation = _format_counts_and_expectation(counts)

    valid_pairs = [(s, e) for s, e in zip(zne_scale_factors, raw_expectations) if e is not None]
    zne_expectation = None
    if len(valid_pairs) >= 2:
        zne_expectation = _richardson_extrapolate(
            [p[0] for p in valid_pairs],
            [p[1] for p in valid_pairs],
        )

    classical_ref = None
    if braid_word:
        try:
            classical_ref = _compute_sl3_classical_reference(braid_word, root_of_unity)
        except Exception:
            pass

    zne_deviation_raw = (
        round(abs(raw_expectations[0] - classical_ref), 8)
        if raw_expectations and raw_expectations[0] is not None and classical_ref is not None
        else None
    )
    zne_deviation_corrected = (
        round(abs(zne_expectation - classical_ref), 8)
        if zne_expectation is not None and classical_ref is not None
        else None
    )

    return {
        "job_id": resolve_job_id(job),
        "backend": resolve_job_backend_name(job) or backend_name_hint or "unknown",
        "runtime_channel_used": channel_used,
        "runtime_instance_used": runtime_instance,
        "status": "COMPLETED",
        "sl_n": 3,
        "root_of_unity": root_of_unity,
        "braid_word": braid_word,
        "counts": formatted_counts,
        "hadamard_expectation": round(expectation, 8),
        "classical_reference": round(classical_ref, 8) if classical_ref is not None else None,
        "zne_noise_factors": list(zne_scale_factors),
        "zne_raw_expectations": raw_expectations,
        "zne_hadamard_expectation": round(zne_expectation, 8) if zne_expectation is not None else None,
        "zne_deviation_raw": zne_deviation_raw,
        "zne_deviation_corrected": zne_deviation_corrected,
    }


def submit_sl3_experiment(
    token: str,
    backend_name: str,
    braid_word: str,
    shots: int,
    root_of_unity: int = DEFAULT_ROOT_OF_UNITY,
    runtime_channel: str | None = None,
    runtime_instance: str | None = None,
) -> dict:
    """Build and submit the sl_3 Hadamard circuit to IBM hardware.

    Constructs build_sl3_hadamard_circuit(braid_word, root_of_unity),
    transpiles it, and submits via SamplerV2. Returns job metadata for
    polling via poll_sl3_experiment_result.
    """
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler

    circuit = build_sl3_hadamard_circuit_pergenerator(braid_word, root_of_unity)
    service, channel_used = create_runtime_service(
        QiskitRuntimeService=QiskitRuntimeService,
        token=token,
        runtime_channel=runtime_channel,
        runtime_instance=runtime_instance,
    )
    from qiskit import transpile

    backend = select_backend(service, backend_name)
    pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
    transpiled = pm.run(circuit)

    # _fold_gates inserts gate inverses (e.g. sx† = sxdg) which some backends
    # reject at submission time. Re-translate each folded circuit to native
    # basis gates at optimization_level=0 to fix unsupported inverses without
    # restructuring the ZNE noise scaling.
    _native_basis = [
        g for g in (getattr(backend, "operation_names", None) or [])
        if g not in {"sxdg", "reset", "delay", "measure", "barrier", "if_else", "switch_case"}
    ] or ["ecr", "cx", "id", "rz", "sx", "x", "cz"]

    sampler = create_sampler_for_backend(Sampler, backend)
    shots_per_level = max(1, shots // len(ZNE_SCALE_FACTORS))
    zne_circuits = [
        transpile(_fold_gates(transpiled, s), basis_gates=_native_basis, optimization_level=0)
        for s in ZNE_SCALE_FACTORS
    ]
    job = sampler.run(zne_circuits, shots=shots_per_level)

    job_id = resolve_job_id(job)
    _runtime_job_metadata_store[job_id] = {
        "experiment_type": "sl3",
        "sl_n": 3,
        "braid_word": braid_word,
        "root_of_unity": root_of_unity,
        "zne_scale_factors": ZNE_SCALE_FACTORS,
    }

    status = resolve_job_status(job)
    if status == "UNKNOWN":
        status = "SUBMITTED"

    return {
        "job_id": job_id,
        "backend": resolve_backend_name(backend),
        "runtime_channel_used": channel_used,
        "runtime_instance_used": runtime_instance,
        "status": status,
        "sl_n": 3,
        "root_of_unity": root_of_unity,
        "braid_word": braid_word,
        "circuit_qubits": transpiled.num_qubits,
        "zne_noise_factors": list(ZNE_SCALE_FACTORS),
        "shots_per_noise_level": shots_per_level,
    }


def poll_sl3_experiment_result(
    token: str,
    job_id: str,
    runtime_channel: str | None = None,
    runtime_instance: str | None = None,
) -> dict:
    """Poll an IBM hardware sl_3 Hadamard circuit job.

    Returns status while the job is in-progress. When COMPLETED, returns
    hadamard_expectation (measured Re(U'[0,0])), classical_reference
    (noiseless Re(U'[0,0])), and deviation between them.
    """
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
    braid_word = runtime_metadata.get("braid_word")
    root_of_unity = runtime_metadata.get("root_of_unity", DEFAULT_ROOT_OF_UNITY)
    zne_scale_factors = runtime_metadata.get("zne_scale_factors", ZNE_SCALE_FACTORS)

    try:
        completed_result = _format_completed_sl3_result(
            job=job,
            channel_used=channel_used,
            runtime_instance=runtime_instance,
            braid_word=braid_word,
            root_of_unity=root_of_unity,
            backend_name_hint=backend_name,
            zne_scale_factors=zne_scale_factors,
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


def _fold_gates(circuit, scale_factor: int):
    """Return a noise-amplified copy of circuit via global gate folding.

    Scale factor n replaces each unitary gate G with G (G† G)^{(n-1)/2}.
    Measurement, barrier, and reset instructions are passed through unchanged.
    """
    if scale_factor == 1:
        return circuit
    from qiskit import QuantumCircuit

    n_extra_pairs = (scale_factor - 1) // 2
    folded = QuantumCircuit(*circuit.qregs, *circuit.cregs)
    for inst in circuit.data:
        folded.append(inst)
        if inst.operation.name in ("measure", "barrier", "reset"):
            continue
        for _ in range(n_extra_pairs):
            try:
                folded.append(inst.operation.inverse(), inst.qubits, [])
                folded.append(inst.operation, inst.qubits, [])
            except Exception:
                pass  # skip gates that lack an inverse
    return folded


def _richardson_extrapolate(scale_factors: list[float], expectations: list[float]) -> float:
    """Polynomial Richardson extrapolation to the zero-noise limit.

    Fits a degree-(n-1) polynomial through n (scale, expectation) pairs
    and evaluates it at scale_factor=0.
    """
    import numpy as np

    coeffs = np.polyfit(scale_factors, expectations, deg=len(scale_factors) - 1)
    return float(np.polyval(coeffs, 0.0))


def _compute_classical_ancilla_expectation(
    braid_word: str,
    root_of_unity: int = DEFAULT_ROOT_OF_UNITY,
) -> float:
    """Compute Re(U[0,0]) from the path model — noiseless reference for ZNE cross-check.

    The Hadamard test circuit measures ⟨Z_ancilla⟩ = Re(⟨0|U|0⟩) = Re(U[0,0])
    where U is the braid representation matrix and the work register starts in |0⟩.
    """
    braid_analysis = validate_braid_problem_input(braid_word)
    ajl_context = _build_ajl_context(braid_analysis["strand_count"], root_of_unity)
    matrix = _compute_braid_representation_matrix(braid_analysis["parsed_braid"], ajl_context)
    return float(matrix[0, 0].real)


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
    zne_scale_factors: tuple = ZNE_SCALE_FACTORS,
):
    result = job.result()

    # Extract ancilla expectation at each ZNE noise level.
    raw_expectations = []
    for i in range(len(zne_scale_factors)):
        try:
            counts_i = extract_counts_from_pub_result(result[i])
            _, exp_i = _format_counts_and_expectation(counts_i)
            raw_expectations.append(exp_i)
        except Exception:
            raw_expectations.append(None)

    # Use the scale_factor=1 (first) pub result as canonical counts for display.
    pub_result = result[0]
    counts = extract_counts_from_pub_result(pub_result)
    formatted_counts, expectation = _format_counts_and_expectation(counts)

    # Richardson extrapolation to zero-noise limit.
    valid_pairs = [(s, e) for s, e in zip(zne_scale_factors, raw_expectations) if e is not None]
    zne_expectation = None
    if len(valid_pairs) >= 2:
        zne_expectation = _richardson_extrapolate(
            [p[0] for p in valid_pairs],
            [p[1] for p in valid_pairs],
        )

    # Classical noiseless reference: Re(U[0,0]) from path model.
    classical_ancilla_ref = None
    if braid_word:
        try:
            classical_ancilla_ref = _compute_classical_ancilla_expectation(braid_word, root_of_unity)
        except Exception:
            pass

    jones_value = None
    if braid_word:
        try:
            jones_value = evaluate_jones_at_root_of_unity(
                braid_word=braid_word,
                root_of_unity=root_of_unity,
                closure_method=closure_method,
            )
            jones_poly = _format_jones_output(jones_value, root_of_unity)
        except ValueError as exc:
            import sys
            print(f"[Q-Knot] Jones evaluation failed (ValueError): {exc}", file=sys.stderr)
            jones_poly = (
                "V(t) = unavailable: path model evaluation failed; "
                f"ancilla expectation={expectation:.6f}"
            )
        except Exception as exc:
            import sys
            print(f"[Q-Knot] Jones evaluation failed (unexpected): {exc!r}", file=sys.stderr)
            jones_poly = (
                "V(t) = unavailable: path model evaluation failed; "
                f"ancilla expectation={expectation:.6f}"
            )
    else:
        jones_poly = (
            "V(t) = unavailable: missing braid metadata for path model evaluation; "
            f"ancilla expectation={expectation:.6f}"
        )

    zne_deviation_raw = (
        abs(raw_expectations[0] - classical_ancilla_ref)
        if raw_expectations and raw_expectations[0] is not None and classical_ancilla_ref is not None
        else None
    )
    zne_deviation_corrected = (
        abs(zne_expectation - classical_ancilla_ref)
        if zne_expectation is not None and classical_ancilla_ref is not None
        else None
    )

    jones_multi_k = []
    if braid_word:
        try:
            jones_multi_k = evaluate_jones_multi_k(braid_word)
        except Exception:
            pass

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
        "zne_noise_factors": list(zne_scale_factors),
        "zne_raw_expectations": [round(e, 8) if e is not None else None for e in raw_expectations],
        "zne_ancilla_expectation": round(zne_expectation, 8) if zne_expectation is not None else None,
        "zne_classical_reference": round(classical_ancilla_ref, 8) if classical_ancilla_ref is not None else None,
        "zne_deviation_raw": round(zne_deviation_raw, 8) if zne_deviation_raw is not None else None,
        "zne_deviation_corrected": round(zne_deviation_corrected, 8) if zne_deviation_corrected is not None else None,
        "jones_multi_k": jones_multi_k,
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
    shots_per_level = max(1, shots // len(ZNE_SCALE_FACTORS))
    zne_circuits = [_fold_gates(transpiled_qc, s) for s in ZNE_SCALE_FACTORS]
    job = sampler.run(zne_circuits, shots=shots_per_level)

    return job, backend, channel_used, circuit_summary, ZNE_SCALE_FACTORS


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
    job, backend, channel_used, circuit_summary, zne_scale_factors = _build_and_submit_knot_job(
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
        "zne_scale_factors": zne_scale_factors,
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
            zne_scale_factors=runtime_metadata.get("zne_scale_factors", ZNE_SCALE_FACTORS),
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
    job, backend, channel_used, _, _zne = _build_and_submit_knot_job(
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
    except ValueError as exc:
        import sys
        print(f"[Q-Knot] Jones evaluation failed (ValueError): {exc}", file=sys.stderr)
        jones_poly = (
            "V(t) = unavailable: path model evaluation failed; "
            f"ancilla expectation={expectation:.6f}"
        )
    except Exception as exc:
        import sys
        print(f"[Q-Knot] Jones evaluation failed (unexpected): {exc!r}", file=sys.stderr)
        jones_poly = (
            "V(t) = unavailable: path model evaluation failed; "
            f"ancilla expectation={expectation:.6f}"
        )

    jones_multi_k = []
    try:
        jones_multi_k = evaluate_jones_multi_k(braid_word)
    except Exception:
        pass

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
        "jones_multi_k": jones_multi_k,
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
