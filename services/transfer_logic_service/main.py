from fastapi import FastAPI, Depends, HTTPException
from typing import List, Dict, Any
from sqlalchemy.orm import Session
import os

from .engine import TransferEngine, get_db

app = FastAPI(
    title="Transfer Logic Service",
    description="A microservice for FPL transfer recommendations.",
    version="1.0.0"
)

# Configuration for other services (to be passed to TransferEngine)
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://fpl-ml-service:8002")
FPL_API_SERVICE_URL = os.getenv("FPL_API_SERVICE_URL", "http://fpl-api-service:8001")


@app.post("/identify-targets")
async def identify_transfer_targets(
    current_squad: List[Dict[str, Any]],
    available_players: List[Dict[str, Any]],
    budget: float,
    db: Session = Depends(get_db)
):
    """
    Identify potential transfer targets given the current squad, available players, and budget.
    """
    engine = TransferEngine(db, ML_SERVICE_URL, FPL_API_SERVICE_URL)
    targets = await engine.identify_transfer_targets(current_squad, available_players, budget)
    return targets

@app.post("/record-transfer")
async def record_transfer(transfer_data: Dict[str, Any], db: Session = Depends(get_db)):
    """
    Record a completed transfer in the database.
    """
    engine = TransferEngine(db, ML_SERVICE_URL, FPL_API_SERVICE_URL) # ML and FPL service URLs not directly used here
    engine.record_transfer(transfer_data)
    return {"message": "Transfer recorded successfully."}
