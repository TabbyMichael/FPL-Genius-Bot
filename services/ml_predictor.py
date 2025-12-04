import logging
import os
import json
from datetime import datetime
from sqlalchemy.orm import Session
from config.database import PlayerPerformance, PlayerPrediction, get_db

# Initialize variables for conditional imports
pd = None
np = None
xgb = None
train_test_split = None
mean_squared_error = None
mean_absolute_error = None
StandardScaler = None
optuna = None
shap = None
ML_LIBRARIES_AVAILABLE = False

# Conditional imports for ML libraries - using importlib to avoid linter errors
import importlib

try:
    pd = importlib.import_module('pandas')
    np = importlib.import_module('numpy')
    xgb = importlib.import_module('xgboost')
    sklearn_model_selection = importlib.import_module('sklearn.model_selection')
    train_test_split = sklearn_model_selection.train_test_split
    sklearn_metrics = importlib.import_module('sklearn.metrics')
    mean_squared_error = sklearn_metrics.mean_squared_error
    mean_absolute_error = sklearn_metrics.mean_absolute_error
    sklearn_preprocessing = importlib.import_module('sklearn.preprocessing')
    StandardScaler = sklearn_preprocessing.StandardScaler
    optuna = importlib.import_module('optuna')
    shap = importlib.import_module('shap')
    ML_LIBRARIES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"ML libraries not available: {e}")

logger = logging.getLogger(__name__)

class MLPredictor:
    """Machine Learning predictor for player performance with enhanced feature engineering and explainability"""
    
    def __init__(self):
        self.model = None
        self.is_trained = False
        self.scaler = StandardScaler() if ML_LIBRARIES_AVAILABLE and StandardScaler is not None else None
        self.feature_names = []
        self.study = None
        self.evaluation_metrics = {}
        self.explainer = None
        
    def engineer_features(self, player_data):
        """Engineer advanced features for better prediction accuracy"""
        if not ML_LIBRARIES_AVAILABLE or pd is None or np is None:
            logger.warning("ML libraries not available, returning empty arrays")
            # Return empty arrays with proper shape when ML libraries aren't available
            empty_array = []
            return empty_array, empty_array
            
        features_list = []
        targets = []
        
        # Convert SQLAlchemy objects to dictionaries for easier manipulation
        for record in player_data:
            features_list.append({
                'opponent_difficulty': getattr(record, 'opponent_difficulty', 3) or 3,
                'minutes_played': getattr(record, 'minutes_played', 0) or 0,
                'goals_scored': getattr(record, 'goals_scored', 0) or 0,
                'assists': getattr(record, 'assists', 0) or 0,
                'clean_sheet': 1 if (getattr(record, 'clean_sheet', False) or False) else 0,
                'yellow_cards': getattr(record, 'yellow_cards', 0) or 0,
                'red_cards': getattr(record, 'red_cards', 0) or 0,
                'saves': getattr(record, 'saves', 0) or 0,
                'bonus': getattr(record, 'bonus', 0) or 0,
                'bps': getattr(record, 'bps', 0) or 0,
                'form': float(getattr(record, 'form', 0.0) or 0.0),
                'points_per_game': float(getattr(record, 'points_per_game', 0.0) or 0.0),
                'selected_by_percent': float(getattr(record, 'selected_by_percent', 0.0) or 0.0),
                'transfers_in': getattr(record, 'transfers_in', 0) or 0,
                'transfers_out': getattr(record, 'transfers_out', 0) or 0,
                'creativity': float(getattr(record, 'creativity', 0.0) or 0.0),
                'influence': float(getattr(record, 'influence', 0.0) or 0.0),
                'threat': float(getattr(record, 'threat', 0.0) or 0.0),
                'ict_index': float(getattr(record, 'ict_index', 0.0) or 0.0),
                'actual_points': float(getattr(record, 'actual_points', 0) or 0)
            })
            targets.append(float(getattr(record, 'actual_points', 0) or 0))
        
        if not features_list:
            empty_array = []
            return empty_array, empty_array
        
        # Create DataFrame
        df = pd.DataFrame(features_list)
        
        # Derived features
        # Recent form windows (using form as proxy for recent performance)
        df['form_3gw'] = df['form'].rolling(window=3, min_periods=1).mean()
        df['form_5gw'] = df['form'].rolling(window=5, min_periods=1).mean()
        
        # Ownership momentum
        df['ownership_momentum'] = df['selected_by_percent'].diff().fillna(0)
        
        # Transfers delta
        df['transfers_delta'] = df['transfers_in'] - df['transfers_out']
        
        # Expected minutes (based on recent playing time)
        df['expected_minutes'] = df['minutes_played'].rolling(window=5, min_periods=1).mean()
        
        # Points per minute ratio
        if np is not None:
            df['points_per_minute'] = np.where(df['minutes_played'] > 0, 
                                             df['actual_points'] / df['minutes_played'], 0)
        else:
            df['points_per_minute'] = [0] * len(df)
        
        # Goal involvement rate
        df['goal_involvement'] = df['goals_scored'] + df['assists']
        
        # Defensive contribution (for defensive positions)
        df['defensive_contribution'] = df['clean_sheet'] + df['saves']/3  # Normalize saves
        
        # Discipline score (inverse of cards)
        df['discipline_score'] = 10 - (df['yellow_cards'] + df['red_cards']*2)
        
        # ICT composite score
        df['ict_composite'] = (df['influence'] + df['creativity'] + df['threat']) / 3
        
        # Value features
        # Normalize some features to prevent dominance
        features_to_normalize = ['bps', 'influence', 'creativity', 'threat', 'ict_index', 'ict_composite']
        for col in features_to_normalize:
            if col in df.columns:
                col_min = df[col].min()
                col_max = df[col].max()
                if col_max != col_min:  # Avoid division by zero
                    df[f'{col}_normalized'] = (df[col] - col_min) / (col_max - col_min + 1e-8)
                else:
                    df[f'{col}_normalized'] = 0
        
        # Drop any rows with NaN values that might have been introduced
        df = df.dropna()
        
        # Set feature names
        self.feature_names = [col for col in df.columns if col != 'actual_points']
        
        # Separate features and target
        if 'actual_points' in df.columns:
            y = df['actual_points'].values
            X = df.drop(['actual_points'], axis=1).values
            return X, y
        else:
            return df.values, np.array(targets) if np is not None else list(df.values)
    
    def objective(self, trial):
        """Objective function for Optuna hyperparameter tuning"""
        if not ML_LIBRARIES_AVAILABLE or xgb is None or train_test_split is None or mean_squared_error is None:
            return float('inf')
            
        # Suggest hyperparameters
        params = {
            'n_estimators': trial.suggest_int('n_estimators', 100, 500),
            'max_depth': trial.suggest_int('max_depth', 3, 10),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
            'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
            'gamma': trial.suggest_float('gamma', 0, 5),
            'reg_alpha': trial.suggest_float('reg_alpha', 0, 5),
            'reg_lambda': trial.suggest_float('reg_lambda', 0, 5)
        }
        
        # Create model with suggested parameters
        if xgb is not None:
            model = xgb.XGBRegressor(**params, random_state=42, objective='reg:squarederror')
        else:
            return float('inf')
        
        # Perform cross-validation
        X_scaled = self.scaler.transform(self.X_train) if hasattr(self, 'X_train') and self.scaler is not None else self.X_train
        scores = []
        
        # Use a simple train-test split for speed during optimization
        if train_test_split is not None:
            X_train, X_val, y_train, y_val = train_test_split(
                X_scaled, self.y_train, test_size=0.2, random_state=42
            )
        else:
            return float('inf')
        
        model.fit(X_train, y_train)
        y_pred = model.predict(X_val)
        if mean_squared_error is not None:
            mse = mean_squared_error(y_val, y_pred)
        else:
            # Fallback calculation
            mse = sum((y1 - y2) ** 2 for y1, y2 in zip(y_val, y_pred)) / len(y_val) if y_val and y_pred else float('inf')
        
        return mse
    
    def train_model(self, db: Session):
        """Train the ML model with enhanced feature engineering and Optuna tuning"""
        if not ML_LIBRARIES_AVAILABLE or pd is None or np is None or xgb is None or train_test_split is None or mean_squared_error is None or mean_absolute_error is None:
            logger.warning("ML libraries not available, skipping model training")
            return False
            
        try:
            # Default parameters in case Optuna is not available
            default_params = {
                'n_estimators': 100,
                'max_depth': 6,
                'learning_rate': 0.1,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'min_child_weight': 1,
                'gamma': 0,
                'reg_alpha': 0,
                'reg_lambda': 1
            }
            
            # Fetch historical performance data
            performance_data = db.query(PlayerPerformance).all()
            
            if len(performance_data) < 10:
                logger.warning(f"Insufficient data to train model (need at least 10 records, have {len(performance_data)})")
                return False
            
            # Engineer features
            X, y = self.engineer_features(performance_data)
            
            # Check if we have valid data after feature engineering
            if len(X) == 0 or (hasattr(X, '__len__') and len(X) < 5):
                logger.warning(f"Insufficient valid data to train model after feature engineering (need at least 5 records)")
                return False
            
            # Remove any rows with NaN or infinite values (only if we have data and numpy is available)
            if len(X) > 0 and np is not None:
                # Convert to numpy arrays if they aren't already
                if not isinstance(X, np.ndarray):
                    X = np.array(X)
                if not isinstance(y, np.ndarray):
                    y = np.array(y)
                    
                mask = ~np.isnan(X).any(axis=1) & ~np.isnan(y) & np.isfinite(X).all(axis=1) & np.isfinite(y)
                X = X[mask]
                y = y[mask]
            
            if len(X) < 5:
                logger.warning(f"Insufficient valid data to train model after cleaning (need at least 5 records, have {len(X)})")
                return False
            
            # Split data
            if train_test_split is not None:
                self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
                    X, y, test_size=0.2, random_state=42
                )
            else:
                # Manual split as fallback
                split_idx = int(len(X) * 0.8)
                self.X_train, self.X_test = X[:split_idx], X[split_idx:]
                self.y_train, self.y_test = y[:split_idx], y[split_idx:]
            
            # Scale features (only if scaler is available)
            if self.scaler is not None:
                self.X_train = self.scaler.fit_transform(self.X_train)
                self.X_test = self.scaler.transform(self.X_test)
            
            # Hyperparameter tuning with Optuna
            logger.info("Starting Optuna hyperparameter tuning...")
            if optuna is not None:
                self.study = optuna.create_study(direction='minimize')
                self.study.optimize(self.objective, n_trials=20)  # Reduced for faster execution
                best_params = self.study.best_params
            else:
                logger.warning("Optuna not available, using default parameters")
                best_params = default_params
            
            logger.info(f"Parameters: {best_params}")
            
            # Train final model with best parameters or defaults
            if xgb is not None:
                self.model = xgb.XGBRegressor(**best_params, random_state=42, objective='reg:squarederror')
                self.model.fit(self.X_train, self.y_train)
                self.is_trained = True
            else:
                logger.error("XGBoost not available, cannot train model")
                return False
            
            # Evaluate model
            if self.model is not None:
                y_pred = self.model.predict(self.X_test)
            else:
                logger.error("Model is not available for prediction")
                return False
                
            if mean_squared_error is not None and mean_absolute_error is not None:
                mse = mean_squared_error(self.y_test, y_pred)
                mae = mean_absolute_error(self.y_test, y_pred)
            else:
                # Fallback calculations
                mse = sum((y1 - y2) ** 2 for y1, y2 in zip(self.y_test, y_pred)) / len(self.y_test) if self.y_test and y_pred else 0
                mae = sum(abs(y1 - y2) for y1, y2 in zip(self.y_test, y_pred)) / len(self.y_test) if self.y_test and y_pred else 0
            
            if np is not None:
                rmse = np.sqrt(mse)
            else:
                rmse = mse**0.5
                
            self.evaluation_metrics = {
                'mse': mse,
                'mae': mae,
                'rmse': rmse,
                'best_params': best_params
            }
            
            logger.info(f"Model trained. MSE: {mse:.2f}, MAE: {mae:.2f}, RMSE: {rmse:.2f}")
            
            # Create SHAP explainer
            logger.info("Creating SHAP explainer...")
            if shap is not None:
                self.explainer = shap.TreeExplainer(self.model)
            else:
                self.explainer = None
                logger.warning("SHAP not available, skipping explainability")
            
            # Save model artifacts
            self._save_artifacts()
            
            return True
        except Exception as e:
            logger.error(f"Error training model: {str(e)}", exc_info=True)
            return False
    
    def _save_artifacts(self):
        """Save model artifacts for explainability and reproducibility"""
        if not ML_LIBRARIES_AVAILABLE:
            return
            
        try:
            # Create ml_runs directory if it doesn't exist
            os.makedirs('ml_runs', exist_ok=True)
            
            # Save run metadata
            run_metadata = {
                'timestamp': datetime.now().isoformat(),
                'evaluation_metrics': self.evaluation_metrics,
                'feature_names': self.feature_names if hasattr(self, 'feature_names') else [],
                'model_params': self.model.get_params() if self.model is not None else {}
            }
            
            # Save metadata
            with open(f'ml_runs/run_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
                json.dump(run_metadata, f, indent=2)
            
            # Save feature importance
            importance = self.get_feature_importance()
            with open(f'ml_runs/feature_importance_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
                json.dump(importance, f, indent=2)
            
            logger.info("Model artifacts saved successfully")
        except Exception as e:
            logger.error(f"Error saving model artifacts: {str(e)}")
    
    def predict_performance(self, player_stats, opponent_difficulty):
        """Predict player performance for upcoming gameweek"""
        if not self.is_trained or not ML_LIBRARIES_AVAILABLE or pd is None:
            logger.warning("Model not trained yet or ML libraries not available, using fallback prediction")
            # Simple fallback prediction
            return max(0, player_stats.get('form', 0) * 1.2)
        
        try:
            # Create a DataFrame with the same structure as training data
            player_data = [{
                'opponent_difficulty': opponent_difficulty or 3,
                'minutes_played': player_stats.get('minutes', 0) or 0,
                'goals_scored': player_stats.get('goals_scored', 0) or 0,
                'assists': player_stats.get('assists', 0) or 0,
                'clean_sheet': 1 if (player_stats.get('clean_sheets', 0) or 0) > 0 else 0,
                'yellow_cards': player_stats.get('yellow_cards', 0) or 0,
                'red_cards': player_stats.get('red_cards', 0) or 0,
                'saves': player_stats.get('saves', 0) or 0,
                'bonus': player_stats.get('bonus', 0) or 0,
                'bps': player_stats.get('bps', 0) or 0,
                'form': float(player_stats.get('form', 0.0) or 0.0),
                'points_per_game': float(player_stats.get('points_per_game', 0.0) or 0.0),
                'selected_by_percent': float(player_stats.get('selected_by_percent', 0.0) or 0.0),
                'transfers_in': player_stats.get('transfers_in', 0) or 0,
                'transfers_out': player_stats.get('transfers_out', 0) or 0,
                'creativity': float(player_stats.get('creativity', 0.0) or 0.0),
                'influence': float(player_stats.get('influence', 0.0) or 0.0),
                'threat': float(player_stats.get('threat', 0.0) or 0.0),
                'ict_index': float(player_stats.get('ict_index', 0.0) or 0.0),
                'actual_points': 0  # Not used for prediction
            }]
            
            # Apply same feature engineering
            df = pd.DataFrame(player_data)
            
            # Recent form windows
            df['form_3gw'] = df['form']  # Simplified for single prediction
            df['form_5gw'] = df['form']
            
            # Ownership momentum (simplified)
            df['ownership_momentum'] = 0
            
            # Transfers delta
            df['transfers_delta'] = df['transfers_in'] - df['transfers_out']
            
            # Expected minutes (simplified)
            df['expected_minutes'] = df['minutes_played']
            
            # Points per minute ratio
            if np is not None:
                df['points_per_minute'] = np.where(df['minutes_played'] > 0, 
                                                 df['actual_points'] / df['minutes_played'], 0)
            else:
                df['points_per_minute'] = [0] * len(df)
            
            # Goal involvement rate
            df['goal_involvement'] = df['goals_scored'] + df['assists']
            
            # Defensive contribution
            df['defensive_contribution'] = df['clean_sheet'] + df['saves']/3
            
            # Discipline score
            df['discipline_score'] = 10 - (df['yellow_cards'] + df['red_cards']*2)
            
            # ICT composite score
            df['ict_composite'] = (df['influence'] + df['creativity'] + df['threat']) / 3
            
            # Normalize features
            features_to_normalize = ['bps', 'influence', 'creativity', 'threat', 'ict_index', 'ict_composite']
            for col in features_to_normalize:
                if col in df.columns:
                    # Use a small constant for normalization to avoid division by zero
                    df[f'{col}_normalized'] = (df[col] - 0) / (1 + 1e-8)
            
            # Select only the features used in training
            if hasattr(self, 'feature_names') and self.feature_names:
                X_pred = df[self.feature_names].values
            else:
                # Fallback if feature_names is not available
                X_pred = df.values
            
            # Scale features (only if scaler is available)
            if self.scaler is not None:
                X_pred_scaled = self.scaler.transform(X_pred)
            else:
                X_pred_scaled = X_pred
            
            # Make prediction
            if self.model is not None:
                prediction = self.model.predict(X_pred_scaled)[0]
                return max(0, prediction)  # Ensure non-negative prediction
            else:
                logger.error("Model is not available for prediction")
                return max(0, player_stats.get('form', 0))  # Fallback to form rating
        except Exception as e:
            logger.error(f"Error predicting performance: {str(e)}", exc_info=True)
            return max(0, player_stats.get('form', 0))  # Fallback to form rating
    
    def get_shap_values(self, X_sample=None):
        """Get SHAP values for explainability"""
        if not self.is_trained or self.explainer is None or not ML_LIBRARIES_AVAILABLE or shap is None:
            return None
        
        try:
            # If no sample provided, use a subset of test data
            if X_sample is None and hasattr(self, 'X_test') and self.X_test is not None:
                # Use a sample of test data
                sample_size = min(100, len(self.X_test))
                X_sample = self.X_test[:sample_size]
            
            # Calculate SHAP values
            if X_sample is not None:
                shap_values = self.explainer.shap_values(X_sample)
                return shap_values
            else:
                return None
        except Exception as e:
            logger.error(f"Error calculating SHAP values: {str(e)}", exc_info=True)
            return None
    
    def get_feature_importance(self):
        """Get enhanced feature importance from trained model"""
        if not self.is_trained or not ML_LIBRARIES_AVAILABLE:
            return {}
        
        try:
            # Check if model exists and has feature_importances_ attribute
            if self.model is None or not hasattr(self.model, 'feature_importances_'):
                return {}
            
            importance = self.model.feature_importances_
            feature_importance = {}
            if hasattr(self, 'feature_names') and self.feature_names:
                for i, feature in enumerate(self.feature_names):
                    # Handle case where importance might be NaN
                    if i < len(importance):
                        imp_value = importance[i]
                        if np is not None and np.isnan(imp_value):
                            imp_value = 0.0
                        feature_importance[feature] = imp_value
            else:
                # Fallback if feature_names is not available
                for i, imp_value in enumerate(importance):
                    if np is not None and np.isnan(imp_value):
                        imp_value = 0.0
                    feature_importance[f'feature_{i}'] = imp_value
            
            # Sort by importance
            sorted_importance = dict(sorted(feature_importance.items(), key=lambda item: item[1], reverse=True))
            return sorted_importance
        except Exception as e:
            logger.error(f"Error getting feature importance: {str(e)}", exc_info=True)
            return {}