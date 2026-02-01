"""
Database models and connection setup for BloomingSongs
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Index, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from pathlib import Path

# Database path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATABASE_PATH = BASE_DIR / "data" / "bloomingsongs.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Ensure data directory exists
os.makedirs(BASE_DIR / "data", exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class BirdObservation(Base):
    """Store individual bird observations from eBird"""
    __tablename__ = "bird_observations"
    
    id = Column(Integer, primary_key=True, index=True)
    # eBird data fields
    species_code = Column(String(50), index=True)  # eBird species code
    common_name = Column(String(200), index=True)
    scientific_name = Column(String(200))
    observation_date = Column(DateTime, index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    location_id = Column(String(100), index=True)  # eBird location ID
    location_name = Column(String(500))
    region_code = Column(String(10), index=True)  # e.g., US-CA
    county_code = Column(String(10), index=True)
    
    # Observation metadata
    observation_count = Column(String(50))  # e.g., "X", "1", "2-5"
    has_media = Column(Integer, default=0)  # 1 if observation has media
    approved = Column(Integer, default=1)  # 1 if approved, 0 if not reviewed
    
    # Singing/vocalization indicators
    # Note: eBird doesn't have explicit "singing" field, but we can infer from:
    # - Observations with media (often audio)
    # - Recent observations during breeding season
    # - High observation frequency
    is_vocal = Column(Integer, default=0)  # 1 if likely vocalizing (inferred)
    
    # Data source
    source = Column(String(50), default="ebird")
    fetched_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_date_species', 'observation_date', 'species_code'),
        Index('idx_location_date', 'location_id', 'observation_date'),
        Index('idx_region_date', 'region_code', 'observation_date'),
    )


class BirdTrend(Base):
    """Aggregated trend data for bird species"""
    __tablename__ = "bird_trends"
    
    id = Column(Integer, primary_key=True, index=True)
    species_code = Column(String(50), index=True)
    common_name = Column(String(200), index=True)
    region_code = Column(String(10), index=True)
    
    # Time period
    date = Column(DateTime, index=True)  # Date for this trend calculation
    period_start = Column(DateTime)  # Start of comparison period
    period_end = Column(DateTime)    # End of comparison period
    
    # Observation counts
    current_count = Column(Integer)  # Observations in current period
    previous_count = Column(Integer)  # Observations in previous period
    
    # Trend metrics
    change_percent = Column(Float)  # Percentage change
    trend_direction = Column(String(20))  # "rising", "falling", "stable"
    
    # Ranking
    current_rank = Column(Integer)  # Rank by observation count in current period
    previous_rank = Column(Integer)  # Rank in previous period
    
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_species_date', 'species_code', 'date'),
        Index('idx_region_date', 'region_code', 'date'),
    )


class DailySummary(Base):
    """Daily summary statistics for regions"""
    __tablename__ = "daily_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    region_code = Column(String(10), index=True)
    
    total_observations = Column(Integer)
    unique_species = Column(Integer)
    top_species_json = Column(Text)  # JSON array of top species
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_date_region', 'date', 'region_code'),
    )


def init_db():
    """Initialize the database by creating all tables"""
    Base.metadata.create_all(bind=engine, checkfirst=True)


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
