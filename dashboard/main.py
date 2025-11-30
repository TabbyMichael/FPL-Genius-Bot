from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import os
import logging
from config.database import get_db, PlayerPerformance, PlayerPrediction, TransferHistory
from config.settings import TEAM_ID
from services.health_check import HealthCheckService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="FPL Bot Dashboard", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency
def get_database():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

@app.get("/")
async def root():
    return {"message": "FPL Bot Dashboard API"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_service = HealthCheckService()
    health_status = await health_service.run_health_checks()
    return {
        "status": "healthy" if all(health_status.values()) else "unhealthy",
        "details": health_status
    }

@app.get("/team/info")
async def get_team_info(db: Session = Depends(get_database)):
    """Get team information"""
    if not TEAM_ID:
        raise HTTPException(status_code=400, detail="TEAM_ID not configured")
    
    return {
        "team_id": TEAM_ID,
        "status": "active"
    }

@app.get("/performance/history")
async def get_performance_history(limit: int = 50, db: Session = Depends(get_database)):
    """Get player performance history"""
    try:
        performances = db.query(PlayerPerformance).order_by(
            PlayerPerformance.created_at.desc()
        ).limit(limit).all()
        
        return [
            {
                "id": p.id,
                "player_id": p.player_id,
                "gameweek": p.gameweek,
                "expected_points": p.expected_points,
                "actual_points": p.actual_points,
                "opponent_difficulty": p.opponent_difficulty,
                "form": p.form,
                "points_per_game": p.points_per_game,
                "created_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in performances
        ]
    except Exception as e:
        logger.error(f"Error fetching performance history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch performance history")

@app.get("/predictions/latest")
async def get_latest_predictions(limit: int = 50, db: Session = Depends(get_database)):
    """Get latest player predictions"""
    try:
        predictions = db.query(PlayerPrediction).order_by(
            PlayerPrediction.created_at.desc()
        ).limit(limit).all()
        
        return [
            {
                "id": p.id,
                "player_id": p.player_id,
                "gameweek": p.gameweek,
                "predicted_points": p.predicted_points,
                "confidence_interval": p.confidence_interval,
                "model_version": p.model_version,
                "created_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in predictions
        ]
    except Exception as e:
        logger.error(f"Error fetching predictions: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch predictions")

@app.get("/transfers/history")
async def get_transfer_history(limit: int = 50, db: Session = Depends(get_database)):
    """Get transfer history"""
    try:
        transfers = db.query(TransferHistory).order_by(
            TransferHistory.timestamp.desc()
        ).limit(limit).all()
        
        return [
            {
                "id": t.id,
                "player_out_id": t.player_out_id,
                "player_in_id": t.player_in_id,
                "gameweek": t.gameweek,
                "transfer_gain": t.transfer_gain,
                "cost": t.cost,
                "timestamp": t.timestamp.isoformat() if t.timestamp else None
            }
            for t in transfers
        ]
    except Exception as e:
        logger.error(f"Error fetching transfer history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch transfer history")

@app.get("/analytics/summary")
async def get_analytics_summary(db: Session = Depends(get_database)):
    """Get analytics summary"""
    try:
        # Get total predictions
        total_predictions = db.query(PlayerPrediction).count()
        
        # Get total performances
        total_performances = db.query(PlayerPerformance).count()
        
        # Get total transfers
        total_transfers = db.query(TransferHistory).count()
        
        # Get latest gameweek
        latest_performance = db.query(PlayerPerformance).order_by(
            PlayerPerformance.gameweek.desc()
        ).first()
        
        latest_gameweek = latest_performance.gameweek if latest_performance else 0
        
        return {
            "total_predictions": total_predictions,
            "total_performances": total_performances,
            "total_transfers": total_transfers,
            "latest_gameweek": latest_gameweek
        }
    except Exception as e:
        logger.error(f"Error fetching analytics summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch analytics summary")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)