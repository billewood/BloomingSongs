"""
Pydantic schemas for API request/response models
"""

from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime


class SourceBreakdown(BaseModel):
    """Breakdown of observations by data source"""
    ebird: int = 0
    inaturalist: int = 0
    total: int = 0


class BirdObservationResponse(BaseModel):
    """Response model for a single bird observation"""
    species_code: str
    common_name: str
    scientific_name: str
    observation_count: int
    sources: Optional[SourceBreakdown] = None


class CurrentBirdsResponse(BaseModel):
    """Response model for current birds endpoint"""
    birds: List[BirdObservationResponse]
    period_start: str
    period_end: str
    total_species: int
    sources: SourceBreakdown


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


class HistoricalDataEntry(BaseModel):
    """A single entry in historical data"""
    species_code: str
    common_name: str
    count: int


class HistoricalDataResponse(BaseModel):
    """Response model for historical data"""
    data: Dict[str, List[HistoricalDataEntry]]  # Date -> list of observations
    period_start: str
    period_end: str
    total_days: int
    sources: SourceBreakdown


class DataSourceStats(BaseModel):
    """Response model for data source statistics"""
    total_observations: int
    ebird_observations: int
    inaturalist_observations: int
    vocal_observations: int
    unique_species: int
    regions: List[str]
    last_updated: Optional[str] = None
