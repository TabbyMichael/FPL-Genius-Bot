from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import os
import logging

# Conditional import for FPLAPI to avoid linter errors
import importlib

try:
    fpl_api_module = importlib.import_module('services.fpl_api_service')
    FPLAPI = fpl_api_module.FPLAPI
except ImportError as e:
    logging.error(f"Failed to import FPLAPI: {e}")
    FPLAPI = None

from config.database import get_db, PlayerPerformance, PlayerPrediction, TransferHistory
from config.settings import TEAM_ID
from services.health_check import HealthCheckService
from services.ml_predictor import MLPredictor

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

# Cache for player data
_player_cache = {}

# Global ML predictor instance
ml_predictor = MLPredictor()

# Initialize ML model status
def initialize_ml_model():
    """Initialize ML model status"""
    global ml_predictor
    try:
        # Try to check if model file exists or is trained
        # For now, we'll just set it as not trained until the bot runs
        logger.info("ML Predictor initialized")
    except Exception as e:
        logger.error(f"Error initializing ML predictor: {str(e)}")

# Initialize on startup
initialize_ml_model()

# Dependency
def get_database():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

async def get_player_name(player_id: int) -> str:
    """Get player name from FPL API or cache"""
    global _player_cache
    
    # Check cache first
    if player_id in _player_cache:
        return _player_cache[player_id]
    
    try:
        # Create FPL API instance (without auth for public data)
        if FPLAPI is not None:
            async with FPLAPI() as api:
                player_info = await api.get_player_info(player_id)
                if player_info and isinstance(player_info, dict):
                    # Safely extract the web_name
                    player_name = player_info.get('web_name')
                    if player_name:
                        _player_cache[player_id] = player_name
                        return player_name
        
        # Fallback if player info is not available or FPLAPI is None
        return f'Player {player_id}'
    except Exception as e:
        logger.error(f"Error fetching player name for ID {player_id}: {str(e)}")
        return f'Player {player_id}'

@app.get("/")
async def root():
    return {"message": "FPL Bot Dashboard API"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_service = HealthCheckService()
    health_status = await health_service.run_health_checks(ml_predictor)
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
    """Get player performance history with player names"""
    try:
        performances = db.query(PlayerPerformance).order_by(
            PlayerPerformance.created_at.desc()
        ).limit(limit).all()
        
        # Get player names for all unique player IDs
        player_ids = []
        for p in performances:
            player_id = p.player_id if p.player_id is not None else 0
            if player_id not in player_ids:
                player_ids.append(player_id)
        
        player_names = {}
        for player_id in player_ids:
            player_names[player_id] = await get_player_name(player_id)
        
        result = []
        for p in performances:
            player_id = p.player_id if p.player_id is not None else 0
            result.append({
                "id": p.id if p.id is not None else 0,
                "player_id": player_id,
                "player_name": player_names.get(player_id, f'Player {player_id}'),
                "gameweek": p.gameweek if p.gameweek is not None else 0,
                "expected_points": p.expected_points if p.expected_points is not None else 0.0,
                "actual_points": p.actual_points if p.actual_points is not None else 0.0,
                "opponent_difficulty": p.opponent_difficulty if p.opponent_difficulty is not None else 3,
                "form": p.form if p.form is not None else 0.0,
                "points_per_game": p.points_per_game if p.points_per_game is not None else 0.0,
                "created_at": p.created_at.isoformat() if p.created_at is not None else None
            })
        
        return result
    except Exception as e:
        logger.error(f"Error fetching performance history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch performance history")

@app.get("/predictions/latest")
async def get_latest_predictions(limit: int = 50, db: Session = Depends(get_database)):
    """Get latest player predictions with player names"""
    try:
        predictions = db.query(PlayerPrediction).order_by(
            PlayerPrediction.created_at.desc()
        ).limit(limit).all()
        
        # Get player names for all unique player IDs
        player_ids = []
        for p in predictions:
            player_id = p.player_id if p.player_id is not None else 0
            if player_id not in player_ids:
                player_ids.append(player_id)
        
        player_names = {}
        for player_id in player_ids:
            player_names[player_id] = await get_player_name(player_id)
        
        result = []
        for p in predictions:
            player_id = p.player_id if p.player_id is not None else 0
            result.append({
                "id": p.id if p.id is not None else 0,
                "player_id": player_id,
                "player_name": player_names.get(player_id, f'Player {player_id}'),
                "gameweek": p.gameweek if p.gameweek is not None else 0,
                "predicted_points": p.predicted_points if p.predicted_points is not None else 0.0,
                "confidence_interval": p.confidence_interval if p.confidence_interval is not None else 0.0,
                "model_version": getattr(p, 'model_version', ''),
                "created_at": p.created_at.isoformat() if p.created_at is not None else None
            })
        
        return result
    except Exception as e:
        logger.error(f"Error fetching predictions: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch predictions")

@app.get("/transfers/history")
async def get_transfer_history(limit: int = 50, db: Session = Depends(get_database)):
    """Get transfer history with player names"""
    try:
        transfers = db.query(TransferHistory).order_by(
            TransferHistory.timestamp.desc()
        ).limit(limit).all()
        
        # Get player names for all unique player IDs
        player_ids = []
        for t in transfers:
            player_out_id = t.player_out_id if t.player_out_id is not None else 0
            player_in_id = t.player_in_id if t.player_in_id is not None else 0
            if player_out_id not in player_ids:
                player_ids.append(player_out_id)
            if player_in_id not in player_ids:
                player_ids.append(player_in_id)
        
        player_names = {}
        for player_id in player_ids:
            player_names[player_id] = await get_player_name(player_id)
        
        result = []
        for t in transfers:
            player_out_id = t.player_out_id if t.player_out_id is not None else 0
            player_in_id = t.player_in_id if t.player_in_id is not None else 0
            result.append({
                "id": t.id if t.id is not None else 0,
                "player_out_id": player_out_id,
                "player_out_name": player_names.get(player_out_id, f'Player {player_out_id}'),
                "player_in_id": player_in_id,
                "player_in_name": player_names.get(player_in_id, f'Player {player_in_id}'),
                "gameweek": t.gameweek if t.gameweek is not None else 0,
                "transfer_gain": t.transfer_gain if t.transfer_gain is not None else 0.0,
                "cost": t.cost if t.cost is not None else 0,
                "timestamp": t.timestamp.isoformat() if t.timestamp is not None else None
            })
        
        return result
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