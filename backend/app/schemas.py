"""
Pydantic schemas for API request/response models
"""

from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime


class BirdObservationResponse(BaseModel):
    """Response model for a single bird observation"""
    species_code: str
    common_name: str
    scientific_name: str
    observation_count: int


class CurrentBirdsResponse(BaseModel):
    """Response model for current birds endpoint"""
    birds: List[BirdObservationResponse]
    period_start: str
    period_end: str
    total_species: int


class BirdTrendResponse(BaseModel):
    """Response model for bird trend data"""
    species_code: str
    common_name: str
    current_count: int
    previous_count: int
    change_percent: float
    trend_direction: str  # "rising", "falling", "stable"
    period_start: str
    period_end: str


class HistoricalDataResponse(BaseModel):
    """Response model for historical data"""
    data: Dict[str, List[BirdObservationResponse]]  # Date -> list of observations
    period_start: str
    period_end: str
    total_days: int
