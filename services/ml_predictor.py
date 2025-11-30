import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_squared_error
from sqlalchemy.orm import Session
from config.database import PlayerPerformance, PlayerPrediction, get_db
import logging

logger = logging.getLogger(__name__)

class MLPredictor:
    """Machine Learning predictor for player performance"""
    
    def __init__(self):
        self.model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100, random_state=42)
        self.is_trained = False
        self.feature_names = [
            'opponent_difficulty', 'minutes_played', 'goals_scored', 'assists',
            'clean_sheet', 'yellow_cards', 'red_cards', 'saves', 'bonus', 'bps',
            'form', 'points_per_game', 'selected_by_percent', 'transfers_in',
            'transfers_out', 'creativity', 'influence', 'threat', 'ict_index'
        ]
    
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
            # Fetch historical performance data
            performance_data = db.query(PlayerPerformance).all()
            
            if len(performance_data) < 10:  # Reduced minimum for better testing
                logger.warning(f"Insufficient data to train model (need at least 10 records, have {len(performance_data)})")
                return False
            
            # Prepare features and target
            X = self.prepare_features(performance_data)
            y = np.array([getattr(record, 'actual_points', 0) or 0 for record in performance_data])
            
            # Remove any rows with NaN or infinite values
            mask = ~np.isnan(X).any(axis=1) & ~np.isnan(y) & np.isfinite(X).all(axis=1) & np.isfinite(y)
            X = X[mask]
            y = y[mask]
            
            if len(X) < 5:  # Reduced minimum for better testing
                logger.warning(f"Insufficient valid data to train model after cleaning (need at least 5 records, have {len(X)})")
                return False
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Hyperparameter tuning
            param_grid = {
                'n_estimators': [100, 200],
                'max_depth': [3, 5, 7],
                'learning_rate': [0.05, 0.1],
                'colsample_bytree': [0.7, 1.0]
            }
            grid_search = GridSearchCV(estimator=self.model, param_grid=param_grid, cv=3, n_jobs=-1, scoring='neg_mean_squared_error')
            grid_search.fit(X_train, y_train)

            self.model = grid_search.best_estimator_
            self.is_trained = True
            
            # Evaluate model
            y_pred = self.model.predict(X_test)
            mse = mean_squared_error(y_test, y_pred)
            logger.info(f"Model trained with best params: {grid_search.best_params_}. MSE: {mse:.2f}, Samples: {len(X)}")
            
            return True
        except Exception as e:
            logger.error(f"Error training model: {str(e)}", exc_info=True)
            return False
    
    def predict_performance(self, player_stats, opponent_difficulty):
        """Predict player performance for upcoming gameweek"""
        if not self.is_trained:
            logger.warning("Model not trained yet, using fallback prediction")
            # Simple fallback prediction
            return max(0, player_stats.get('form', 0) * 1.2)
        
        try:
            # Data validation and cleaning
            numeric_features = [
                'minutes', 'goals_scored', 'assists', 'clean_sheets',
                'yellow_cards', 'red_cards', 'saves', 'bonus', 'bps',
                'form', 'points_per_game', 'selected_by_percent',
                'transfers_in', 'transfers_out'
            ]
            for feature in numeric_features:
                try:
                    player_stats[feature] = pd.to_numeric(player_stats.get(feature, 0), errors='coerce')
                    if pd.isna(player_stats[feature]):
                        player_stats[feature] = 0
                except (ValueError, TypeError):
                    player_stats[feature] = 0

            # Prepare feature vector with default values for missing features
            features = np.array([[
                opponent_difficulty or 3,
                player_stats.get('minutes', 0) or 0,
                player_stats.get('goals_scored', 0) or 0,
                player_stats.get('assists', 0) or 0,
                1 if (player_stats.get('clean_sheets', 0) or 0) > 0 else 0,
                player_stats.get('yellow_cards', 0) or 0,
                player_stats.get('red_cards', 0) or 0,
                player_stats.get('saves', 0) or 0,
                player_stats.get('bonus', 0) or 0,
                player_stats.get('bps', 0) or 0,
                player_stats.get('form', 0.0) or 0.0,
                player_stats.get('points_per_game', 0.0) or 0.0,
                player_stats.get('selected_by_percent', 0.0) or 0.0,
                player_stats.get('transfers_in', 0) or 0,
                player_stats.get('transfers_out', 0) or 0,
                player_stats.get('creativity', 0.0) or 0.0,
                player_stats.get('influence', 0.0) or 0.0,
                player_stats.get('threat', 0.0) or 0.0,
                player_stats.get('ict_index', 0.0) or 0.0
            ]], dtype=np.float64)  # Ensure dtype is float
            
            # Validate features
            if np.isnan(features).any() or not np.isfinite(features).all():
                logger.warning("Invalid features detected, using fallback prediction")
                return max(0, player_stats.get('form', 0))
            
            # Make prediction
            prediction = self.model.predict(features)[0]
            return max(0, prediction)  # Ensure non-negative prediction
        except Exception as e:
            logger.error(f"Error predicting performance: {str(e)}", exc_info=True)
            return max(0, player_stats.get('form', 0))  # Fallback to form rating
    
    def get_feature_importance(self):
        """Get feature importance from trained model"""
        if not self.is_trained:
            return {}
        
        try:
            importance = self.model.feature_importances_
            feature_importance = {}
            for i, feature in enumerate(self.feature_names):
                # Handle case where importance might be NaN
                imp_value = importance[i] if not np.isnan(importance[i]) else 0.0
                feature_importance[feature] = imp_value
            
            # Sort by importance
            sorted_importance = dict(sorted(feature_importance.items(), key=lambda item: item[1], reverse=True))
            return sorted_importance
        except Exception as e:
            logger.error(f"Error getting feature importance: {str(e)}", exc_info=True)
            return {}