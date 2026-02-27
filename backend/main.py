import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

try:
    from .quantum_engine import (
        cancel_knot_experiment,
        compile_dowker_notation,
        generate_knot_circuit_artifact,
        list_accessible_backends,
        poll_knot_experiment_result,
        run_knot_experiment,
        submit_knot_experiment,
        verify_topological_mapping,
    )
except ImportError:
    from quantum_engine import (
        cancel_knot_experiment,
        compile_dowker_notation,
        generate_knot_circuit_artifact,
        list_accessible_backends,
        poll_knot_experiment_result,
        run_knot_experiment,
        submit_knot_experiment,
        verify_topological_mapping,
    )

app = FastAPI(title="Q-Knot IBM Quantum Backend")
ROOT_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT_DIR / "dist"

# Allow CORS for the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ExperimentRequest(BaseModel):
    ibm_token: str = Field(min_length=1)
    backend_name: str = Field(min_length=1)
    braid_word: str = Field(min_length=1)
    shots: int = Field(ge=1, le=100_000)
    optimization_level: int = Field(default=3, ge=0, le=3)
    closure_method: Literal["trace", "plat"] = "trace"
    runtime_channel: Literal["ibm_quantum_platform", "ibm_cloud", "ibm_quantum"] | None = None
    runtime_instance: str | None = None

    @field_validator("ibm_token", "backend_name", "braid_word")
    @classmethod
    def strip_and_validate_non_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Field cannot be blank.")
        return normalized

    @field_validator("runtime_instance", mode="before")
    @classmethod
    def normalize_optional_runtime_instance(cls, value):
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("runtime_instance must be a string when provided.")
        normalized = value.strip()
        return normalized or None


class PollJobRequest(BaseModel):
    ibm_token: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    runtime_channel: Literal["ibm_quantum_platform", "ibm_cloud", "ibm_quantum"] | None = None
    runtime_instance: str | None = None

    @field_validator("ibm_token", "job_id")
    @classmethod
    def strip_and_validate_non_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Field cannot be blank.")
        return normalized

    @field_validator("runtime_instance", mode="before")
    @classmethod
    def normalize_optional_runtime_instance(cls, value):
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("runtime_instance must be a string when provided.")
        normalized = value.strip()
        return normalized or None


class RuntimeServiceRequest(BaseModel):
    ibm_token: str = Field(min_length=1)
    runtime_channel: Literal["ibm_quantum_platform", "ibm_cloud", "ibm_quantum"] | None = None
    runtime_instance: str | None = None

    @field_validator("ibm_token")
    @classmethod
    def strip_and_validate_non_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Field cannot be blank.")
        return normalized

    @field_validator("runtime_instance", mode="before")
    @classmethod
    def normalize_optional_runtime_instance(cls, value):
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("runtime_instance must be a string when provided.")
        normalized = value.strip()
        return normalized or None


class KnotIngestionRequest(BaseModel):
    dowker_notation: str = Field(min_length=1)

    @field_validator("dowker_notation")
    @classmethod
    def strip_and_validate_non_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Field cannot be blank.")
        return normalized


class KnotVerificationRequest(BaseModel):
    braid_word: str = Field(min_length=1)

    @field_validator("braid_word")
    @classmethod
    def strip_and_validate_non_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Field cannot be blank.")
        return normalized


class CircuitGenerationRequest(BaseModel):
    braid_word: str = Field(min_length=1)
    optimization_level: int = Field(default=3, ge=0, le=3)
    closure_method: Literal["trace", "plat"] = "trace"
    target_backend: str | None = None

    @field_validator("braid_word")
    @classmethod
    def strip_and_validate_non_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Field cannot be blank.")
        return normalized

    @field_validator("target_backend", mode="before")
    @classmethod
    def normalize_optional_target_backend(cls, value):
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("target_backend must be a string when provided.")
        normalized = value.strip()
        return normalized or None


@app.post("/api/run-experiment")
async def run_experiment(req: ExperimentRequest):
    try:
        result = await run_in_threadpool(
            run_knot_experiment,
            req.ibm_token,
            req.backend_name,
            req.braid_word,
            req.shots,
            req.optimization_level,
            req.closure_method,
            req.runtime_channel,
            req.runtime_instance,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jobs/submit")
async def submit_experiment_job(req: ExperimentRequest):
    try:
        result = await run_in_threadpool(
            submit_knot_experiment,
            req.ibm_token,
            req.backend_name,
            req.braid_word,
            req.shots,
            req.optimization_level,
            req.closure_method,
            req.runtime_channel,
            req.runtime_instance,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jobs/poll")
async def poll_experiment_job(req: PollJobRequest):
    try:
        result = await run_in_threadpool(
            poll_knot_experiment_result,
            req.ibm_token,
            req.job_id,
            req.runtime_channel,
            req.runtime_instance,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jobs/cancel")
async def cancel_experiment_job(req: PollJobRequest):
    try:
        result = await run_in_threadpool(
            cancel_knot_experiment,
            req.ibm_token,
            req.job_id,
            req.runtime_channel,
            req.runtime_instance,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/backends")
async def list_backends(req: RuntimeServiceRequest):
    try:
        result = await run_in_threadpool(
            list_accessible_backends,
            req.ibm_token,
            req.runtime_channel,
            req.runtime_instance,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/knot/ingest")
async def ingest_knot(req: KnotIngestionRequest):
    try:
        result = await run_in_threadpool(
            compile_dowker_notation,
            req.dowker_notation,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/knot/verify")
async def verify_knot(req: KnotVerificationRequest):
    try:
        result = await run_in_threadpool(
            verify_topological_mapping,
            req.braid_word,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/knot/circuit/generate")
async def generate_knot_circuit(req: CircuitGenerationRequest):
    try:
        result = await run_in_threadpool(
            generate_knot_circuit_artifact,
            req.braid_word,
            req.optimization_level,
            req.closure_method,
            req.target_backend,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health():
    return {"status": "ok"}


def _env_flag_is_enabled(variable_name: str) -> bool:
    value = os.getenv(variable_name, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


if _env_flag_is_enabled("QKNOT_SERVE_FRONTEND") and DIST_DIR.exists():
    assets_dir = DIST_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="frontend-assets")

    @app.get("/", include_in_schema=False)
    async def serve_frontend_root():
        return FileResponse(DIST_DIR / "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend_path(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")

        candidate = DIST_DIR / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(DIST_DIR / "index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
