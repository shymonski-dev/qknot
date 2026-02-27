#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
BACKEND_VENV_DIR = BACKEND_DIR / ".venv"
BACKEND_REQUIREMENTS = BACKEND_DIR / "requirements.txt"
REQUIREMENTS_HASH_MARKER = BACKEND_VENV_DIR / ".requirements.sha256"
DIST_INDEX = ROOT_DIR / "dist" / "index.html"
SUPPORTED_PYTHON_MINORS = {10, 11, 12}


def _is_supported_python_version(version_info: tuple[int, int]) -> bool:
    major, minor = version_info
    return major == 3 and minor in SUPPORTED_PYTHON_MINORS


def _venv_python_path() -> Path:
    if os.name == "nt":
        return BACKEND_VENV_DIR / "Scripts" / "python.exe"
    return BACKEND_VENV_DIR / "bin" / "python"


def _run_or_raise(args: list[str], cwd: Path = ROOT_DIR, env: dict[str, str] | None = None) -> None:
    result = subprocess.run(args, cwd=str(cwd), env=env)
    if result.returncode != 0:
        joined = " ".join(args)
        raise RuntimeError(f"Command failed with exit code {result.returncode}: {joined}")


def _read_command_python_version(command: list[str]) -> tuple[int, int] | None:
    result = subprocess.run(
        [*command, "-c", "import sys;print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None

    version_text = result.stdout.strip()
    parts = version_text.split(".")
    if len(parts) != 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def _read_python_version(python_executable: Path) -> tuple[int, int] | None:
    result = subprocess.run(
        [
            str(python_executable),
            "-c",
            "import sys;print(f'{sys.version_info.major}.{sys.version_info.minor}')",
        ],
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    version_text = result.stdout.strip()
    parts = version_text.split(".")
    if len(parts) != 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def _resolve_supported_python_command() -> list[str]:
    candidates: list[list[str]] = []
    env_python = os.getenv("QKNOT_PYTHON", "").strip()
    if env_python:
        candidates.append(shlex.split(env_python))
    else:
        if os.name == "nt":
            candidates.extend(
                [
                    ["py", "-3.12"],
                    ["py", "-3.11"],
                    ["py", "-3.10"],
                    ["py", "-3"],
                    [sys.executable],
                    ["python"],
                ]
            )
        else:
            candidates.extend(
                [
                    [sys.executable],
                    ["python3.12"],
                    ["python3.11"],
                    ["python3.10"],
                    ["python3"],
                    ["python"],
                ]
            )

    discovered_versions: list[str] = []
    seen: set[tuple[str, ...]] = set()
    for candidate in candidates:
        key = tuple(candidate)
        if key in seen:
            continue
        seen.add(key)

        version = _read_command_python_version(candidate)
        if version is None:
            continue

        discovered_versions.append(f"{' '.join(candidate)} -> {version[0]}.{version[1]}")
        if _is_supported_python_version(version):
            return candidate

    allowed = ", ".join(sorted(f"3.{minor}" for minor in SUPPORTED_PYTHON_MINORS))
    if discovered_versions:
        raise RuntimeError(
            f"Supported Python versions are {allowed}. Found: {', '.join(discovered_versions)}."
        )
    raise RuntimeError(
        f"No Python interpreter was found. Install one of: {allowed}."
    )


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ensure_backend_runtime() -> Path:
    python_command = _resolve_supported_python_command()
    venv_python = _venv_python_path()

    if BACKEND_VENV_DIR.exists() and venv_python.exists():
        venv_version = _read_python_version(venv_python)
        if venv_version is None or not _is_supported_python_version(venv_version):
            print("Recreating backend virtual environment with supported Python...")
            shutil.rmtree(BACKEND_VENV_DIR, ignore_errors=True)

    if not BACKEND_VENV_DIR.exists():
        print("Creating backend virtual environment...")
        _run_or_raise([*python_command, "-m", "venv", str(BACKEND_VENV_DIR)])

    if not venv_python.exists():
        raise RuntimeError(f"Missing backend virtual environment Python at {venv_python}")

    requirements_hash = _file_sha256(BACKEND_REQUIREMENTS)
    installed_hash = REQUIREMENTS_HASH_MARKER.read_text().strip() if REQUIREMENTS_HASH_MARKER.exists() else ""
    if requirements_hash != installed_hash:
        print("Installing backend dependencies...")
        _run_or_raise([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"])
        _run_or_raise([str(venv_python), "-m", "pip", "install", "-r", str(BACKEND_REQUIREMENTS)])
        REQUIREMENTS_HASH_MARKER.write_text(requirements_hash, encoding="utf-8")
    else:
        print("Backend dependencies are up to date.")

    return venv_python


def _ensure_frontend_distribution() -> None:
    if DIST_INDEX.exists():
        return
    raise RuntimeError(
        "Frontend distribution is missing at dist/index.html. "
        "Run 'npm run build' once, then rerun this launcher."
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start Q-Knot standalone runtime without Node.")
    parser.add_argument("--prepare-only", action="store_true", help="Prepare runtime and exit.")
    parser.add_argument("--host", default=os.getenv("QKNOT_BACKEND_HOST", "0.0.0.0"))
    parser.add_argument("--port", default=os.getenv("QKNOT_BACKEND_PORT", "8000"))
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        venv_python = _ensure_backend_runtime()
        _ensure_frontend_distribution()
    except Exception as exc:
        print(f"Failed to prepare standalone runtime: {exc}", file=sys.stderr)
        return 1

    if args.prepare_only:
        print("Standalone runtime is prepared.")
        return 0

    print(f"Starting standalone runtime on http://localhost:{args.port}")
    runtime_env = os.environ.copy()
    runtime_env["QKNOT_SERVE_FRONTEND"] = "1"

    result = subprocess.run(
        [
            str(venv_python),
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            str(args.host),
            "--port",
            str(args.port),
        ],
        cwd=str(ROOT_DIR),
        env=runtime_env,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
