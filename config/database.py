import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Database configuration - using SQLite for easier setup
# Change to PostgreSQL connection string if desired
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fpl_bot.db")

# Create SQLAlchemy engine and session
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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