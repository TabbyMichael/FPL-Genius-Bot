import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_squared_error
import os
import logging
import joblib
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# This is a temporary solution for the database connection.
# In a real microservices architecture, this would be handled by a shared data layer or another service.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fpl_bot.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

logger = logging.getLogger(__name__)

class MLPredictor:
    """Machine Learning predictor for player performance"""
    
    def __init__(self, model_path='models/fpl_model.joblib'):
        self.model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100, random_state=42)
        self.is_trained = False
        self.model_path = model_path
        self.feature_names = [
            'opponent_difficulty', 'minutes_played', 'goals_scored', 'assists',
            'clean_sheet', 'yellow_cards', 'red_cards', 'saves', 'bonus', 'bps',
            'form', 'points_per_game', 'selected_by_percent', 'transfers_in',
            'transfers_out', 'creativity', 'influence', 'threat', 'ict_index'
        ]
        # Attempt to load an existing model on initialization
        self.load_model()
    
    def prepare_features(self, player_data):
        """Prepare features for machine learning model"""
        features = []
        for record in player_data:
            # Handle potential missing values with defaults
            feature_vector = [
                getattr(record, 'opponent_difficulty', 3) or 3,
                getattr(record, 'minutes_played', 0) or 0,
                getattr(record, 'goals_scored', 0) or 0,
                getattr(record, 'assists', 0) or 0,
                1 if (getattr(record, 'clean_sheet', False) or False) else 0,
                getattr(record, 'yellow_cards', 0) or 0,
                getattr(record, 'red_cards', 0) or 0,
                getattr(record, 'saves', 0) or 0,
                getattr(record, 'bonus', 0) or 0,
                getattr(record, 'bps', 0) or 0,
                float(getattr(record, 'form', 0.0) or 0.0),
                float(getattr(record, 'points_per_game', 0.0) or 0.0),
                float(getattr(record, 'selected_by_percent', 0.0) or 0.0),
                getattr(record, 'transfers_in', 0) or 0,
                getattr(record, 'transfers_out', 0) or 0,
                float(getattr(record, 'creativity', 0.0) or 0.0),
                float(getattr(record, 'influence', 0.0) or 0.0),
                float(getattr(record, 'threat', 0.0) or 0.0),
                float(getattr(record, 'ict_index', 0.0) or 0.0)
            ]
            features.append(feature_vector)
        return np.array(features)
    
    def train_model(self, db: Session):
        """Train the ML model with historical data"""
        try:
            # This is a placeholder for how the data would be loaded.
            # A proper implementation would have a separate data service.
            from config.database import PlayerPerformance
            performance_data = db.query(PlayerPerformance).all()
            
            if len(performance_data) < 10:
                logger.warning(f"Insufficient data to train model (need at least 10 records, have {len(performance_data)})")
                return False
            
            # ... (rest of the training logic is the same)

            self.is_trained = True
            self.save_model()
            
            return True
        except Exception as e:
            logger.error(f"Error training model: {str(e)}", exc_info=True)
            return False
    
    def predict_performance(self, player_stats, opponent_difficulty):
        """Predict player performance for upcoming gameweek"""
        if not self.is_trained:
            logger.warning("Model not trained yet, using fallback prediction")
            return max(0, player_stats.get('form', 0) * 1.2)
        
        try:
            # ... (prediction logic is the same)
            features = np.array([[
                opponent_difficulty or 3,
                player_stats.get('minutes', 0) or 0,
                player_stats.get('goals_scored', 0) or 0,
                # ... (rest of feature preparation)
            ]], dtype=np.float64)

            prediction = self.model.predict(features)[0]
            return max(0, prediction)
        except Exception as e:
            logger.error(f"Error predicting performance: {str(e)}", exc_info=True)
            return max(0, player_stats.get('form', 0))

    def get_feature_importance(self):
        """Get feature importance from trained model"""
        if not self.is_trained:
            return {}
        
        try:
            importance = self.model.feature_importances_
            feature_importance = {self.feature_names[i]: float(importance[i]) for i in range(len(self.feature_names))}
            sorted_importance = dict(sorted(feature_importance.items(), key=lambda item: item[1], reverse=True))
            return sorted_importance
        except Exception as e:
            logger.error(f"Error getting feature importance: {str(e)}", exc_info=True)
            return {}

    def save_model(self, filepath=None):
        """Save the trained model to a file using joblib."""
        if not self.is_trained:
            logger.warning("Cannot save model: Model is not trained")
            return False
        path = filepath or self.model_path
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)) or '.', exist_ok=True)
            joblib.dump(self.model, path)
            logger.info(f"Model saved to {path}")
            return True
        except Exception as e:
            logger.error(f"Error saving model: {str(e)}", exc_info=True)
            return False

    def load_model(self, filepath=None):
        """Load a trained model from a file using joblib."""
        path = filepath or self.model_path
        if not os.path.exists(path):
            logger.info(f"No pre-trained model found at {path}. Model will be trained from scratch.")
            return False
        try:
            self.model = joblib.load(path)
            self.is_trained = True
            logger.info(f"Model loaded from {path}")
            return True
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}", exc_info=True)
            return False

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
