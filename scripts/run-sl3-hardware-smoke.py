#!/usr/bin/env python3
"""Live hardware smoke test for the sl_3 Hadamard circuit.

Submits build_sl3_hadamard_circuit_pergenerator to IBM hardware via the
/api/knot/sl3/submit and /api/knot/sl3/poll routes, then prints the
result including hadamard_expectation and classical_reference.

Use QKNOT_BRAID_WORDS (comma-separated) to run multiple knots in sequence.
If QKNOT_BRAID_WORDS is not set, falls back to QKNOT_BRAID_WORD (single
braid). If neither is set, runs trefoil, figure-eight, and cinquefoil.

Required environment variables:
    QKNOT_BACKEND_NAME   IBM backend to target (e.g. ibm_torino)

Optional environment variables:
    QKNOT_BACKEND_URL          Backend API base URL (default: http://127.0.0.1:8000)
    QKNOT_BRAID_WORDS          Comma-separated braid words (overrides QKNOT_BRAID_WORD)
    QKNOT_BRAID_WORD           Single braid word (default: see QKNOT_BRAID_WORDS)
    QKNOT_SHOTS                Number of shots total (default: 1536)
    QKNOT_ROOT_OF_UNITY        Root of unity k (default: 5)
    QKNOT_RUNTIME_CHANNEL      IBM runtime channel (e.g. ibm_cloud)
    QKNOT_RUNTIME_INSTANCE     IBM runtime instance CRN
    QKNOT_POLL_INTERVAL_SECONDS  Seconds between poll requests (default: 5)
    QKNOT_MAX_POLL_ATTEMPTS    Maximum poll attempts before timeout (default: 120)
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request


IN_PROGRESS_JOB_STATUSES = {"INITIALIZING", "QUEUED", "RUNNING", "VALIDATING", "SUBMITTED"}
FAILED_JOB_STATUSES = {"FAILED", "ERROR", "CANCELLED", "CANCELED"}

DEFAULT_BRAID_WORDS = [
    "s1 s2 s1 s2",       # trefoil (3_1)
    "s1 s2^-1 s1 s2^-1", # figure-eight (4_1)
    "s1 s1 s1 s1 s1 s2", # cinquefoil (5_1)
]


def _read_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Environment variable {name} is required.")
    return value


def _read_optional_env(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


def _post_json(url: str, payload: dict) -> tuple[int, dict]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            status_code = response.status
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        status_code = exc.code
        body = exc.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error while calling {url}: {exc.reason}") from exc

    try:
        payload_json = json.loads(body) if body else {}
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON response from {url}: {body}") from exc
    return status_code, payload_json


def _run_single_knot(
    backend_url: str,
    backend_name: str,
    braid_word: str,
    shots: int,
    root_of_unity: int,
    runtime_channel: str | None,
    runtime_instance: str | None,
    poll_interval_seconds: float,
    max_poll_attempts: int,
) -> int:
    """Submit and poll one sl_3 job. Returns 0 on success, 1 on failure."""
    submit_payload: dict = {
        "backend_name": backend_name,
        "braid_word": braid_word,
        "shots": shots,
        "root_of_unity": root_of_unity,
    }
    if runtime_channel:
        submit_payload["runtime_channel"] = runtime_channel
    if runtime_instance:
        submit_payload["runtime_instance"] = runtime_instance

    print(f"\nSubmitting sl_3 Hadamard circuit smoke job...")
    print(f"  braid_word    : {braid_word}")
    print(f"  backend       : {backend_name}")
    print(f"  shots         : {shots}")
    print(f"  root_of_unity : {root_of_unity}")

    try:
        submit_status, submit_response = _post_json(
            f"{backend_url}/api/knot/sl3/submit", submit_payload
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if submit_status >= 400:
        print(f"Submission failed ({submit_status}): {submit_response}", file=sys.stderr)
        return 1

    job_id = submit_response.get("job_id")
    if not isinstance(job_id, str) or not job_id:
        print(f"Submission response missing job_id: {submit_response}", file=sys.stderr)
        return 1

    print(
        f"Submitted job_id={job_id}, status={submit_response.get('status')}, "
        f"circuit_qubits={submit_response.get('circuit_qubits')}"
    )

    poll_payload: dict = {"job_id": job_id}
    if runtime_channel:
        poll_payload["runtime_channel"] = runtime_channel
    if runtime_instance:
        poll_payload["runtime_instance"] = runtime_instance

    for attempt in range(1, max_poll_attempts + 1):
        try:
            poll_status, poll_response = _post_json(
                f"{backend_url}/api/knot/sl3/poll", poll_payload
            )
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        if poll_status >= 400:
            print(f"Polling failed ({poll_status}): {poll_response}", file=sys.stderr)
            return 1

        status = str(poll_response.get("status", "UNKNOWN"))
        print(f"Poll attempt {attempt}: status={status}")

        if status == "COMPLETED":
            print("\nsl_3 Hadamard circuit smoke run completed.")
            print(f"  hadamard_expectation     : {poll_response.get('hadamard_expectation')}")
            print(f"  classical_reference      : {poll_response.get('classical_reference')}")
            print(f"  zne_hadamard_expectation : {poll_response.get('zne_hadamard_expectation')}")
            print(f"  zne_deviation_raw        : {poll_response.get('zne_deviation_raw')}")
            print(f"  zne_deviation_corrected  : {poll_response.get('zne_deviation_corrected')}")
            print(f"  sl_n                     : {poll_response.get('sl_n')}")
            print(f"  root_of_unity            : {poll_response.get('root_of_unity')}")
            print("\nFull response payload:")
            print(json.dumps(poll_response, indent=2))
            return 0

        if status in FAILED_JOB_STATUSES:
            print(f"sl_3 smoke run failed: {poll_response}", file=sys.stderr)
            return 1

        if status not in IN_PROGRESS_JOB_STATUSES:
            print(f"Unexpected status during polling: {poll_response}", file=sys.stderr)
            return 1

        time.sleep(poll_interval_seconds)

    print(f"Timed out after {max_poll_attempts} polling attempts.", file=sys.stderr)
    return 1


def main() -> int:
    try:
        backend_name = _read_required_env("QKNOT_BACKEND_NAME")
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    if not _read_optional_env("IBM_QUANTUM_TOKEN") and not _read_optional_env("QKNOT_IBM_TOKEN"):
        print(
            "Warning: IBM_QUANTUM_TOKEN is not set in this shell. "
            "Ensure the backend runtime process has IBM credentials configured.",
            file=sys.stderr,
        )

    backend_url = _read_optional_env("QKNOT_BACKEND_URL") or "http://127.0.0.1:8000"
    backend_url = backend_url.rstrip("/")
    shots = int(_read_optional_env("QKNOT_SHOTS") or "1536")
    root_of_unity = int(_read_optional_env("QKNOT_ROOT_OF_UNITY") or "5")
    runtime_channel = _read_optional_env("QKNOT_RUNTIME_CHANNEL")
    runtime_instance = _read_optional_env("QKNOT_RUNTIME_INSTANCE")
    poll_interval_seconds = float(_read_optional_env("QKNOT_POLL_INTERVAL_SECONDS") or "5")
    max_poll_attempts = int(_read_optional_env("QKNOT_MAX_POLL_ATTEMPTS") or "120")

    # Resolve braid word list: QKNOT_BRAID_WORDS > QKNOT_BRAID_WORD > defaults
    braid_words_raw = _read_optional_env("QKNOT_BRAID_WORDS")
    if braid_words_raw:
        braid_words = [w.strip() for w in braid_words_raw.split(",") if w.strip()]
    else:
        single = _read_optional_env("QKNOT_BRAID_WORD")
        braid_words = [single] if single else DEFAULT_BRAID_WORDS

    print(f"sl_3 hardware smoke: {len(braid_words)} knot(s) on {backend_name}")

    overall_exit = 0
    for braid_word in braid_words:
        exit_code = _run_single_knot(
            backend_url=backend_url,
            backend_name=backend_name,
            braid_word=braid_word,
            shots=shots,
            root_of_unity=root_of_unity,
            runtime_channel=runtime_channel,
            runtime_instance=runtime_instance,
            poll_interval_seconds=poll_interval_seconds,
            max_poll_attempts=max_poll_attempts,
        )
        if exit_code != 0:
            overall_exit = exit_code

    return overall_exit


if __name__ == "__main__":
    raise SystemExit(main())
