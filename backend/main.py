from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, field_validator
from fastapi.middleware.cors import CORSMiddleware

try:
    from .quantum_engine import (
        cancel_knot_experiment,
        list_accessible_backends,
        poll_knot_experiment_result,
        run_knot_experiment,
        submit_knot_experiment,
    )
except ImportError:
    from quantum_engine import (
        cancel_knot_experiment,
        list_accessible_backends,
        poll_knot_experiment_result,
        run_knot_experiment,
        submit_knot_experiment,
    )

app = FastAPI(title="Q-Knot IBM Quantum Backend")

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


@app.get("/api/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
