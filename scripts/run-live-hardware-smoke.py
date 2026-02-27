#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request


IN_PROGRESS_JOB_STATUSES = {"INITIALIZING", "QUEUED", "RUNNING", "VALIDATING", "SUBMITTED"}
FAILED_JOB_STATUSES = {"FAILED", "ERROR", "CANCELLED", "CANCELED"}


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


def main() -> int:
    try:
        ibm_token = _read_required_env("QKNOT_IBM_TOKEN")
        backend_name = _read_required_env("QKNOT_BACKEND_NAME")
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    backend_url = _read_optional_env("QKNOT_BACKEND_URL") or "http://127.0.0.1:8000"
    backend_url = backend_url.rstrip("/")
    braid_word = _read_optional_env("QKNOT_BRAID_WORD") or "s1 s2^-1 s1 s2^-1"
    shots = int(_read_optional_env("QKNOT_SHOTS") or "1024")
    optimization_level = int(_read_optional_env("QKNOT_OPTIMIZATION_LEVEL") or "2")
    closure_method = _read_optional_env("QKNOT_CLOSURE_METHOD") or "trace"
    runtime_channel = _read_optional_env("QKNOT_RUNTIME_CHANNEL")
    runtime_instance = _read_optional_env("QKNOT_RUNTIME_INSTANCE")
    poll_interval_seconds = float(_read_optional_env("QKNOT_POLL_INTERVAL_SECONDS") or "5")
    max_poll_attempts = int(_read_optional_env("QKNOT_MAX_POLL_ATTEMPTS") or "120")

    submit_payload = {
        "ibm_token": ibm_token,
        "backend_name": backend_name,
        "braid_word": braid_word,
        "shots": shots,
        "optimization_level": optimization_level,
        "closure_method": closure_method,
    }
    if runtime_channel:
        submit_payload["runtime_channel"] = runtime_channel
    if runtime_instance:
        submit_payload["runtime_instance"] = runtime_instance

    print("Submitting live hardware smoke job...")
    submit_status, submit_response = _post_json(f"{backend_url}/api/jobs/submit", submit_payload)
    if submit_status >= 400:
        print(f"Submission failed ({submit_status}): {submit_response}", file=sys.stderr)
        return 1

    job_id = submit_response.get("job_id")
    if not isinstance(job_id, str) or not job_id:
        print(f"Submission response missing job_id: {submit_response}", file=sys.stderr)
        return 1

    print(f"Submitted job_id={job_id}, status={submit_response.get('status')}")

    poll_payload = {"ibm_token": ibm_token, "job_id": job_id}
    if runtime_channel:
        poll_payload["runtime_channel"] = runtime_channel
    if runtime_instance:
        poll_payload["runtime_instance"] = runtime_instance

    for attempt in range(1, max_poll_attempts + 1):
        poll_status, poll_response = _post_json(f"{backend_url}/api/jobs/poll", poll_payload)
        if poll_status >= 400:
            print(f"Polling failed ({poll_status}): {poll_response}", file=sys.stderr)
            return 1

        status = str(poll_response.get("status", "UNKNOWN"))
        print(f"Poll attempt {attempt}: status={status}")

        if status == "COMPLETED":
            print("Live hardware smoke run completed.")
            print(json.dumps(poll_response, indent=2))
            return 0

        if status in FAILED_JOB_STATUSES:
            print(f"Live hardware smoke run failed: {poll_response}", file=sys.stderr)
            return 1

        if status not in IN_PROGRESS_JOB_STATUSES:
            print(f"Unexpected status during polling: {poll_response}", file=sys.stderr)
            return 1

        time.sleep(poll_interval_seconds)

    print(f"Timed out after {max_poll_attempts} polling attempts.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
