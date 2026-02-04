"""
FastAPI application for BloomingSongs API
"""

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, distinct
from datetime import datetime, timedelta
from typing import List, Optional, Literal
import sys
from pathlib import Path

# Add models to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.database import get_db, BirdObservation, BirdTrend, DailySummary
from app.schemas import (
    BirdObservationResponse,
    BirdTrendResponse,
    CurrentBirdsResponse,
    HistoricalDataResponse,
    SourceBreakdown,
    DataSourceStats
)

app = FastAPI(
    title="BloomingSongs API",
    description="API for bird singing activity and trends from eBird and iNaturalist",
    version="1.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_source_breakdown(db: Session, base_query=None) -> SourceBreakdown:
    """Get count of observations by source"""
    if base_query is None:
        ebird = db.query(func.count(BirdObservation.id)).filter(
            BirdObservation.source.like('%ebird%')
        ).scalar() or 0
        # iNaturalist includes both API data and iNatSounds dataset
        inat = db.query(func.count(BirdObservation.id)).filter(
            BirdObservation.source.in_(['inaturalist', 'inatsounds'])
        ).scalar() or 0
    else:
        # For subqueries, this is trickier - just return totals
        ebird = 0
        inat = 0
    
    total = ebird + inat
    return SourceBreakdown(ebird=ebird, inaturalist=inat, total=total)


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "name": "BloomingSongs API",
        "version": "1.0.0",
        "description": "API for bird singing activity and trends"
    }


@app.get("/api/birds/current", response_model=CurrentBirdsResponse)
def get_current_birds(
    lat: Optional[float] = Query(None, description="Latitude"),
    lon: Optional[float] = Query(None, description="Longitude"),
    region_code: Optional[str] = Query(None, description="Region code (e.g., US-CA)"),
    days: int = Query(7, description="Number of days to look back"),
    limit: int = Query(50, description="Maximum number of results"),
    source: Optional[str] = Query(None, description="Filter by source: 'ebird', 'inaturalist', or 'all'"),
    db: Session = Depends(get_db)
):
    """
    Get current singing birds for a location or region
    
    Returns birds observed in the specified time period, sorted by observation frequency.
    Data is combined from eBird (breeding codes) and iNaturalist (audio recordings).
    """
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Build base filter for source breakdown
    base_filters = [
        BirdObservation.observation_date >= start_date,
        BirdObservation.observation_date <= end_date
    ]
    
    if region_code:
        base_filters.append(BirdObservation.region_code == region_code)
    
    # Get source breakdown
    ebird_count = db.query(func.count(BirdObservation.id)).filter(
        *base_filters,
        BirdObservation.source.like('%ebird%')
    ).scalar() or 0
    
    inat_count = db.query(func.count(BirdObservation.id)).filter(
        *base_filters,
        BirdObservation.source.in_(['inaturalist', 'inatsounds'])
    ).scalar() or 0
    
    sources = SourceBreakdown(
        ebird=ebird_count,
        inaturalist=inat_count,
        total=ebird_count + inat_count
    )
    
    # Build query
    query = db.query(
        BirdObservation.species_code,
        BirdObservation.common_name,
        BirdObservation.scientific_name,
        func.count(BirdObservation.id).label('observation_count')
    ).filter(
        BirdObservation.observation_date >= start_date,
        BirdObservation.observation_date <= end_date
    )
    
    # Apply source filter
    if source == 'ebird':
        query = query.filter(BirdObservation.source.like('%ebird%'))
    elif source == 'inaturalist':
        query = query.filter(BirdObservation.source.in_(['inaturalist', 'inatsounds']))
    # else 'all' or None - include all sources
    
    # Apply location filters
    if lat and lon:
        # Simple bounding box (could be improved with proper distance calculation)
        query = query.filter(
            BirdObservation.latitude.between(lat - 0.5, lat + 0.5),
            BirdObservation.longitude.between(lon - 0.5, lon + 0.5)
        )
    elif region_code:
        query = query.filter(BirdObservation.region_code == region_code)
    
    # Group by species and order by count
    query = query.group_by(
        BirdObservation.species_code,
        BirdObservation.common_name,
        BirdObservation.scientific_name
    ).order_by(desc('observation_count')).limit(limit)
    
    results = query.all()
    
    birds = [
        {
            "species_code": r.species_code,
            "common_name": r.common_name,
            "scientific_name": r.scientific_name,
            "observation_count": r.observation_count
        }
        for r in results
    ]
    
    return {
        "birds": birds,
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
        "total_species": len(birds),
        "sources": sources
    }


@app.get("/api/birds/trends", response_model=List[BirdTrendResponse])
def get_bird_trends(
    region_code: Optional[str] = Query(None, description="Region code"),
    days: int = Query(7, description="Days in each comparison period"),
    limit: int = Query(50, description="Maximum number of results"),
    min_observations: int = Query(5, description="Minimum observations to include"),
    db: Session = Depends(get_db)
):
    """
    Get trend data showing which birds are rising, falling, or stable
    
    Compares current period with previous period of same length
    """
    # Calculate date ranges
    now = datetime.utcnow()
    current_end = now
    current_start = now - timedelta(days=days)
    previous_end = current_start
    previous_start = previous_end - timedelta(days=days)
    
    # Get current period counts
    current_query = db.query(
        BirdObservation.species_code,
        BirdObservation.common_name,
        func.count(BirdObservation.id).label('count')
    ).filter(
        BirdObservation.observation_date >= current_start,
        BirdObservation.observation_date < current_end
    )
    
    if region_code:
        current_query = current_query.filter(BirdObservation.region_code == region_code)
    
    current_counts = {
        r.species_code: {
            "common_name": r.common_name,
            "count": r.count
        }
        for r in current_query.group_by(
            BirdObservation.species_code,
            BirdObservation.common_name
        ).all()
    }
    
    # Get previous period counts
    previous_query = db.query(
        BirdObservation.species_code,
        func.count(BirdObservation.id).label('count')
    ).filter(
        BirdObservation.observation_date >= previous_start,
        BirdObservation.observation_date < previous_end
    )
    
    if region_code:
        previous_query = previous_query.filter(BirdObservation.region_code == region_code)
    
    previous_counts = {
        r.species_code: r.count
        for r in previous_query.group_by(BirdObservation.species_code).all()
    }
    
    # Calculate trends
    trends = []
    for species_code, data in current_counts.items():
        current_count = data["count"]
        previous_count = previous_counts.get(species_code, 0)
        
        # Skip if below minimum observations
        if current_count < min_observations and previous_count < min_observations:
            continue
        
        # Calculate percentage change
        if previous_count > 0:
            change_percent = ((current_count - previous_count) / previous_count) * 100
        elif current_count > 0:
            change_percent = 100.0  # New species
        else:
            change_percent = 0.0
        
        # Determine trend direction
        if change_percent > 10:
            trend_direction = "rising"
        elif change_percent < -10:
            trend_direction = "falling"
        else:
            trend_direction = "stable"
        
        trends.append({
            "species_code": species_code,
            "common_name": data["common_name"],
            "current_count": current_count,
            "previous_count": previous_count,
            "change_percent": round(change_percent, 2),
            "trend_direction": trend_direction,
            "period_start": current_start.isoformat(),
            "period_end": current_end.isoformat()
        })
    
    # Sort by absolute change percentage
    trends.sort(key=lambda x: abs(x["change_percent"]), reverse=True)
    
    return trends[:limit]


@app.get("/api/birds/historical", response_model=HistoricalDataResponse)
def get_historical_data(
    species_code: Optional[str] = Query(None, description="Species code to filter"),
    region_code: Optional[str] = Query(None, description="Region code"),
    days: int = Query(90, description="Number of days to look back"),
    source: Optional[str] = Query(None, description="Filter by source: 'ebird', 'inaturalist', or 'all'"),
    db: Session = Depends(get_db)
):
    """
    Get historical data over time for trend visualization.
    Data is combined from eBird and iNaturalist sources.
    """
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Build base filter for source breakdown
    base_filters = [
        BirdObservation.observation_date >= start_date,
        BirdObservation.observation_date <= end_date
    ]
    
    if region_code:
        base_filters.append(BirdObservation.region_code == region_code)
    if species_code:
        base_filters.append(BirdObservation.species_code == species_code)
    
    # Get source breakdown
    ebird_count = db.query(func.count(BirdObservation.id)).filter(
        *base_filters,
        BirdObservation.source.like('%ebird%')
    ).scalar() or 0
    
    inat_count = db.query(func.count(BirdObservation.id)).filter(
        *base_filters,
        BirdObservation.source.in_(['inaturalist', 'inatsounds'])
    ).scalar() or 0
    
    sources = SourceBreakdown(
        ebird=ebird_count,
        inaturalist=inat_count,
        total=ebird_count + inat_count
    )
    
    # Build query
    query = db.query(
        func.date(BirdObservation.observation_date).label('date'),
        BirdObservation.species_code,
        BirdObservation.common_name,
        func.count(BirdObservation.id).label('count')
    ).filter(
        BirdObservation.observation_date >= start_date,
        BirdObservation.observation_date <= end_date
    )
    
    # Apply source filter
    if source == 'ebird':
        query = query.filter(BirdObservation.source.like('%ebird%'))
    elif source == 'inaturalist':
        query = query.filter(BirdObservation.source.in_(['inaturalist', 'inatsounds']))
    
    if species_code:
        query = query.filter(BirdObservation.species_code == species_code)
    if region_code:
        query = query.filter(BirdObservation.region_code == region_code)
    
    # Group by date and species
    results = query.group_by(
        func.date(BirdObservation.observation_date),
        BirdObservation.species_code,
        BirdObservation.common_name
    ).order_by('date').all()
    
    # Organize data by date
    daily_data = {}
    for r in results:
        date_str = r.date.isoformat() if isinstance(r.date, datetime) else str(r.date)
        if date_str not in daily_data:
            daily_data[date_str] = []
        
        daily_data[date_str].append({
            "species_code": r.species_code,
            "common_name": r.common_name,
            "count": r.count
        })
    
    return {
        "data": daily_data,
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
        "total_days": days,
        "sources": sources
    }


@app.get("/api/birds/top", response_model=List[BirdObservationResponse])
def get_top_birds(
    region_code: Optional[str] = Query(None, description="Region code"),
    days: int = Query(7, description="Number of days to look back"),
    limit: int = Query(20, description="Maximum number of results"),
    db: Session = Depends(get_db)
):
    """
    Get top singing birds by observation count
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    query = db.query(
        BirdObservation.species_code,
        BirdObservation.common_name,
        BirdObservation.scientific_name,
        func.count(BirdObservation.id).label('observation_count')
    ).filter(
        BirdObservation.observation_date >= start_date,
        BirdObservation.observation_date <= end_date
    )
    
    if region_code:
        query = query.filter(BirdObservation.region_code == region_code)
    
    results = query.group_by(
        BirdObservation.species_code,
        BirdObservation.common_name,
        BirdObservation.scientific_name
    ).order_by(desc('observation_count')).limit(limit).all()
    
    return [
        {
            "species_code": r.species_code,
            "common_name": r.common_name,
            "scientific_name": r.scientific_name,
            "observation_count": r.observation_count
        }
        for r in results
    ]


@app.get("/api/birds/sources", response_model=DataSourceStats)
def get_data_sources(
    db: Session = Depends(get_db)
):
    """
    Get statistics about data sources
    
    Returns counts of observations from each source (eBird, iNaturalist)
    """
    total = db.query(func.count(BirdObservation.id)).scalar() or 0
    ebird = db.query(func.count(BirdObservation.id)).filter(
        BirdObservation.source.like('%ebird%')
    ).scalar() or 0
    # iNaturalist includes both API data and iNatSounds dataset
    inat = db.query(func.count(BirdObservation.id)).filter(
        BirdObservation.source.in_(['inaturalist', 'inatsounds'])
    ).scalar() or 0
    vocal = db.query(func.count(BirdObservation.id)).filter(
        BirdObservation.is_vocal == 1
    ).scalar() or 0
    
    unique_species = db.query(
        func.count(distinct(BirdObservation.species_code))
    ).scalar() or 0
    
    regions = [r[0] for r in db.query(
        distinct(BirdObservation.region_code)
    ).filter(BirdObservation.region_code.isnot(None)).all()]
    
    # Get last update time
    last_obs = db.query(func.max(BirdObservation.fetched_at)).scalar()
    last_updated = last_obs.isoformat() if last_obs else None
    
    return {
        "total_observations": total,
        "ebird_observations": ebird,
        "inaturalist_observations": inat,
        "vocal_observations": vocal,
        "unique_species": unique_species,
        "regions": regions,
        "last_updated": last_updated
    }


@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
