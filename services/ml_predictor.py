import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from sqlalchemy.orm import Session
from config.database import PlayerPerformance, PlayerPrediction, get_db
import logging

logger = logging.getLogger(__name__)

class MLPredictor:
    """Machine Learning predictor for player performance"""
    
    def __init__(self):
        self.model = RandomForestRegressor(
            n_estimators=100, 
            random_state=42,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2
        )
        self.is_trained = False
        self.feature_names = [
            'opponent_difficulty',
            'minutes_played',
            'goals_scored',
            'assists',
            'clean_sheet',
            'yellow_cards',
            'red_cards',
            'saves',
            'bonus',
            'bps',  # Bonus points system
            'form',
            'points_per_game',
            'selected_by_percent',
            'transfers_in',
            'transfers_out'
        ]
    
    def prepare_features(self, player_data):
        """Prepare features for machine learning model"""
        features = []
        for record in player_data:
            # Handle potential missing values
            feature_vector = [
                getattr(record, 'opponent_difficulty', 3),
                getattr(record, 'minutes_played', 0),
                getattr(record, 'goals_scored', 0),
                getattr(record, 'assists', 0),
                1 if getattr(record, 'clean_sheet', False) else 0,
                getattr(record, 'yellow_cards', 0),
                getattr(record, 'red_cards', 0),
                getattr(record, 'saves', 0),
                getattr(record, 'bonus', 0),
                getattr(record, 'bps', 0),
                getattr(record, 'form', 0),
                getattr(record, 'points_per_game', 0),
                getattr(record, 'selected_by_percent', 0),
                getattr(record, 'transfers_in', 0),
                getattr(record, 'transfers_out', 0)
            ]
            features.append(feature_vector)
        return np.array(features)
    
    def train_model(self, db: Session):
        """Train the ML model with historical data"""
        try:
            # Fetch historical performance data
            performance_data = db.query(PlayerPerformance).all()
            
            if len(performance_data) < 20:  # Need minimum data to train
                logger.warning("Insufficient data to train model (need at least 20 records)")
                return False
            
            # Prepare features and target
            X = self.prepare_features(performance_data)
            y = np.array([getattr(record, 'actual_points', 0) for record in performance_data])
            
            # Remove any rows with NaN values
            mask = ~np.isnan(X).any(axis=1) & ~np.isnan(y)
            X = X[mask]
            y = y[mask]
            
            if len(X) < 20:
                logger.warning("Insufficient valid data to train model after cleaning")
                return False
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Train model
            self.model.fit(X_train, y_train)
            self.is_trained = True
            
            # Evaluate model
            y_pred = self.model.predict(X_test)
            mse = mean_squared_error(y_test, y_pred)
            logger.info(f"Model trained. MSE: {mse:.2f}, Samples: {len(X)}")
            
            return True
        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            return False
    
    def predict_performance(self, player_stats, opponent_difficulty):
        """Predict player performance for upcoming gameweek"""
        if not self.is_trained:
            logger.warning("Model not trained yet, using fallback prediction")
            # Simple fallback prediction
            return player_stats.get('form', 0) * 1.2
        
        try:
            # Prepare feature vector with default values for missing features
            features = np.array([[
                opponent_difficulty,
                player_stats.get('minutes', 0),
                player_stats.get('goals_scored', 0),
                player_stats.get('assists', 0),
                1 if player_stats.get('clean_sheets', 0) > 0 else 0,
                player_stats.get('yellow_cards', 0),
                player_stats.get('red_cards', 0),
                player_stats.get('saves', 0),
                player_stats.get('bonus', 0),
                player_stats.get('bps', 0),
                player_stats.get('form', 0),
                player_stats.get('points_per_game', 0),
                player_stats.get('selected_by_percent', 0),
                player_stats.get('transfers_in', 0),
                player_stats.get('transfers_out', 0)
            ]])
            
            # Make prediction
            prediction = self.model.predict(features)[0]
            return max(0, prediction)  # Ensure non-negative prediction
        except Exception as e:
            logger.error(f"Error predicting performance: {str(e)}")
            return player_stats.get('form', 0)  # Fallback to form rating
    
    def get_feature_importance(self):
        """Get feature importance from trained model"""
        if not self.is_trained:
            return {}
        
        try:
            importance = self.model.feature_importances_
            feature_importance = {}
            for i, feature in enumerate(self.feature_names):
                feature_importance[feature] = importance[i]
            
            # Sort by importance
            sorted_importance = dict(sorted(feature_importance.items(), key=lambda item: item[1], reverse=True))
            return sorted_importance
        except Exception as e:
            logger.error(f"Error getting feature importance: {str(e)}")
            return {}