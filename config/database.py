import os
import time
import logging
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

load_dotenv()

# Database configuration - using SQLite for easier setup
# Change to PostgreSQL connection string if desired
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fpl_bot.db")

# Create SQLAlchemy engine and session
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Simple in-memory cache for database queries
_query_cache = {}
_cache_ttl = 300  # 5 minutes

def cached_query(ttl=300):
    """Decorator to cache database query results"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Create a cache key based on function name and arguments
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            current_time = time.time()
            
            # Check if we have a cached result that hasn't expired
            if cache_key in _query_cache:
                result, timestamp = _query_cache[cache_key]
                if current_time - timestamp < ttl:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return result
                else:
                    # Remove expired cache entry
                    del _query_cache[cache_key]
            
            # Execute the function and cache the result
            result = func(*args, **kwargs)
            _query_cache[cache_key] = (result, current_time)
            logger.debug(f"Cached result for {func.__name__}")
            return result
        return wrapper
    return decorator

# Database models
class PlayerPerformance(Base):
    __tablename__ = "player_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, index=True)
    gameweek = Column(Integer)
    expected_points = Column(Float)
    actual_points = Column(Float)
    opponent_difficulty = Column(Integer)
    minutes_played = Column(Integer)
    goals_scored = Column(Integer)
    assists = Column(Integer)
    clean_sheet = Column(Boolean)
    yellow_cards = Column(Integer)
    red_cards = Column(Integer)
    saves = Column(Integer)
    bonus = Column(Integer)
    bps = Column(Integer)
    form = Column(Float)
    points_per_game = Column(Float)
    selected_by_percent = Column(Float)
    transfers_in = Column(Integer)
    transfers_out = Column(Integer)
    created_at = Column(DateTime)

class PlayerPrediction(Base):
    __tablename__ = "player_predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, index=True)
    gameweek = Column(Integer)
    predicted_points = Column(Float)
    confidence_interval = Column(Float)
    model_version = Column(String)
    created_at = Column(DateTime)

class TransferHistory(Base):
    __tablename__ = "transfer_history"
    
    id = Column(Integer, primary_key=True, index=True)
    player_out_id = Column(Integer)
    player_in_id = Column(Integer)
    gameweek = Column(Integer)
    transfer_gain = Column(Float)
    cost = Column(Integer)
    timestamp = Column(DateTime)

# Create tables
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def clear_query_cache():
    """Clear the query cache"""
    global _query_cache
    _query_cache.clear()
    logger.debug("Query cache cleared")