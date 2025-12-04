from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
import logging

from .predictor import MLPredictor, get_db

app = FastAPI(
    title="ML Prediction Service",
    description="A microservice for training and using the FPL ML model.",
    version="1.0.0"
)

# A single, shared MLPredictor instance
ml_predictor = MLPredictor()

class PlayerStats(BaseModel):
    # Define the structure of the player stats for prediction
    # This should match the features used in the model
    form: float = 0.0
    # ... add other relevant player stats here
    
@app.post("/train")
async def train_model(db: Session = Depends(get_db)):
    """
    Trigger the model training process.
    """
    success = ml_predictor.train_model(db)
    if not success:
        raise HTTPException(status_code=500, detail="Model training failed.")
    return {"message": "Model training completed successfully."}

@app.post("/predict")
async def predict_performance(stats: PlayerStats, opponent_difficulty: int):
    """
    Predict performance for a player given their stats.
    """
    if not ml_predictor.is_trained:
        raise HTTPException(status_code=404, detail="Model not trained yet.")
    
    # The stats need to be converted to a dictionary
    player_stats_dict = stats.dict()
    
    prediction = ml_predictor.predict_performance(player_stats_dict, opponent_difficulty)
    return {"predicted_points": prediction}

@app.get("/feature-importance")
async def get_feature_importance():
    """
    Get the feature importance of the trained model.
    """
    if not ml_predictor.is_trained:
        raise HTTPException(status_code=404, detail="Model not trained yet.")
    
    importance = ml_predictor.get_feature_importance()
    return importance
