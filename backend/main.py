from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from quantum_engine import run_knot_experiment

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
    ibm_token: str
    backend_name: str
    braid_word: str
    shots: int
    optimization_level: int = 3

@app.post("/api/run-experiment")
async def run_experiment(req: ExperimentRequest):
    try:
        result = run_knot_experiment(
            token=req.ibm_token,
            backend_name=req.backend_name,
            braid_word=req.braid_word,
            shots=req.shots,
            optimization_level=req.optimization_level
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
