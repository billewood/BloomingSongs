#!/usr/bin/env python3
"""
Script to calculate and store bird trend data
Run this after fetching new observations
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy import func, desc

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.database import SessionLocal, BirdObservation, BirdTrend, init_db
from typing import Optional


def calculate_trends(region_code: Optional[str] = None, days: int = 7):
    """
    Calculate trends comparing current period with previous period
    
    Args:
        region_code: Optional region code to filter by
        days: Number of days in each comparison period
    """
    db = SessionLocal()
    
    try:
        # Calculate date ranges
        now = datetime.utcnow()
        current_end = now
        current_start = now - timedelta(days=days)
        previous_end = current_start
        previous_start = previous_end - timedelta(days=days)
        
        print(f"Calculating trends:")
        print(f"  Current period: {current_start.date()} to {current_end.date()}")
        print(f"  Previous period: {previous_start.date()} to {previous_end.date()}")
        
        # Get current period counts
        current_query = db.query(
            BirdObservation.species_code,
            BirdObservation.common_name,
            func.count(BirdObservation.id).label('count')
        ).filter(
            BirdObservation.observation_date >= current_start,
            BirdObservation.observation_date < current_end,
            BirdObservation.approved == 1
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
            BirdObservation.observation_date < previous_end,
            BirdObservation.approved == 1
        )
        
        if region_code:
            previous_query = previous_query.filter(BirdObservation.region_code == region_code)
        
        previous_counts = {
            r.species_code: r.count
            for r in previous_query.group_by(BirdObservation.species_code).all()
        }
        
        # Calculate and store trends
        trends_created = 0
        for species_code, data in current_counts.items():
            current_count = data["count"]
            previous_count = previous_counts.get(species_code, 0)
            
            # Calculate percentage change
            if previous_count > 0:
                change_percent = ((current_count - previous_count) / previous_count) * 100
            elif current_count > 0:
                change_percent = 100.0
            else:
                change_percent = 0.0
            
            # Determine trend direction
            if change_percent > 10:
                trend_direction = "rising"
            elif change_percent < -10:
                trend_direction = "falling"
            else:
                trend_direction = "stable"
            
            # Create or update trend record
            trend = BirdTrend(
                species_code=species_code,
                common_name=data["common_name"],
                region_code=region_code or "",
                date=now,
                period_start=current_start,
                period_end=current_end,
                current_count=current_count,
                previous_count=previous_count,
                change_percent=change_percent,
                trend_direction=trend_direction,
                calculated_at=now
            )
            
            db.add(trend)
            trends_created += 1
        
        db.commit()
        print(f"✓ Created {trends_created} trend records")
        
    except Exception as e:
        print(f"✗ Error calculating trends: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    calculate_trends()
