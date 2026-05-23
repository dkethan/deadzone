"""
FastAPI server for Agent 1.
Exposes POST /predict so Agent 2 (or Streamlit) can call it over HTTP.

Run:
  uvicorn server:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from agent1 import run_agent1

app = FastAPI(title="Dead Zone Prediction API — Agent 1", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class PredictRequest(BaseModel):
    route: str
    departure_time: str


class PredictResponse(BaseModel):
    route: str
    departure_time: str
    agent1_output: str


@app.get("/health")
def health():
    return {"status": "ok", "agent": "agent1"}


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    try:
        output = run_agent1(req.route, req.departure_time, verbose=True)
        return PredictResponse(
            route=req.route,
            departure_time=req.departure_time,
            agent1_output=output,
        )
    except EnvironmentError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
