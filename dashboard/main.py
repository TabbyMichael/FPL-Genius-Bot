from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import os
import logging
from config.database import get_db, PlayerPerformance, PlayerPrediction, TransferHistory
from config.settings import TEAM_ID
from services.health_check import HealthCheckService
from services.fpl_api import FPLAPI
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
        async with FPLAPI() as api:
            player_info = await api.get_player_info(player_id)
            if player_info:
                player_name = player_info.get('web_name', f'Player {player_id}')
                _player_cache[player_id] = player_name
                return player_name
            else:
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
            player_id = int(p.player_id) if hasattr(p, 'player_id') else 0
            if player_id not in player_ids:
                player_ids.append(player_id)
        
        player_names = {}
        for player_id in player_ids:
            player_names[player_id] = await get_player_name(player_id)
        
        result = []
        for p in performances:
            result.append({
                "id": int(p.id) if hasattr(p, 'id') else 0,
                "player_id": int(p.player_id) if hasattr(p, 'player_id') else 0,
                "player_name": player_names.get(int(p.player_id) if hasattr(p, 'player_id') else 0, f'Player {p.player_id if hasattr(p, "player_id") else 0}'),
                "gameweek": int(p.gameweek) if hasattr(p, 'gameweek') and p.gameweek is not None else 0,
                "expected_points": float(p.expected_points) if hasattr(p, 'expected_points') and p.expected_points is not None else 0.0,
                "actual_points": float(p.actual_points) if hasattr(p, 'actual_points') and p.actual_points is not None else 0.0,
                "opponent_difficulty": int(p.opponent_difficulty) if hasattr(p, 'opponent_difficulty') and p.opponent_difficulty is not None else 3,
                "form": float(p.form) if hasattr(p, 'form') and p.form is not None else 0.0,
                "points_per_game": float(p.points_per_game) if hasattr(p, 'points_per_game') and p.points_per_game is not None else 0.0,
                "created_at": p.created_at.isoformat() if hasattr(p, 'created_at') and p.created_at is not None else None
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
            player_id = int(p.player_id) if hasattr(p, 'player_id') else 0
            if player_id not in player_ids:
                player_ids.append(player_id)
        
        player_names = {}
        for player_id in player_ids:
            player_names[player_id] = await get_player_name(player_id)
        
        result = []
        for p in predictions:
            result.append({
                "id": int(p.id) if hasattr(p, 'id') else 0,
                "player_id": int(p.player_id) if hasattr(p, 'player_id') else 0,
                "player_name": player_names.get(int(p.player_id) if hasattr(p, 'player_id') else 0, f'Player {p.player_id if hasattr(p, "player_id") else 0}'),
                "gameweek": int(p.gameweek) if hasattr(p, 'gameweek') and p.gameweek is not None else 0,
                "predicted_points": float(p.predicted_points) if hasattr(p, 'predicted_points') and p.predicted_points is not None else 0.0,
                "confidence_interval": float(p.confidence_interval) if hasattr(p, 'confidence_interval') and p.confidence_interval is not None else 0.0,
                "model_version": getattr(p, 'model_version', ''),
                "created_at": p.created_at.isoformat() if hasattr(p, 'created_at') and p.created_at is not None else None
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
            player_out_id = int(t.player_out_id) if hasattr(t, 'player_out_id') else 0
            player_in_id = int(t.player_in_id) if hasattr(t, 'player_in_id') else 0
            if player_out_id not in player_ids:
                player_ids.append(player_out_id)
            if player_in_id not in player_ids:
                player_ids.append(player_in_id)
        
        player_names = {}
        for player_id in player_ids:
            player_names[player_id] = await get_player_name(player_id)
        
        result = []
        for t in transfers:
            result.append({
                "id": int(t.id) if hasattr(t, 'id') else 0,
                "player_out_id": int(t.player_out_id) if hasattr(t, 'player_out_id') else 0,
                "player_out_name": player_names.get(int(t.player_out_id) if hasattr(t, 'player_out_id') else 0, f'Player {t.player_out_id if hasattr(t, "player_out_id") else 0}'),
                "player_in_id": int(t.player_in_id) if hasattr(t, 'player_in_id') else 0,
                "player_in_name": player_names.get(int(t.player_in_id) if hasattr(t, 'player_in_id') else 0, f'Player {t.player_in_id if hasattr(t, "player_in_id") else 0}'),
                "gameweek": int(t.gameweek) if hasattr(t, 'gameweek') and t.gameweek is not None else 0,
                "transfer_gain": float(t.transfer_gain) if hasattr(t, 'transfer_gain') and t.transfer_gain is not None else 0.0,
                "cost": int(t.cost) if hasattr(t, 'cost') and t.cost is not None else 0,
                "timestamp": t.timestamp.isoformat() if hasattr(t, 'timestamp') and t.timestamp is not None else None
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