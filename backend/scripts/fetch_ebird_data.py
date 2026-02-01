#!/usr/bin/env python3
"""
Daily script to fetch bird observation data from eBird API
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ebird.api.requests.observations import get_observations, get_nearby_observations
from models.database import SessionLocal, BirdObservation, init_db
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Configuration
EBIRD_API_KEY = os.getenv("EBIRD_API_KEY")
if not EBIRD_API_KEY:
    raise ValueError("EBIRD_API_KEY environment variable not set. Get your key at https://ebird.org/api/keygen")

# Default regions to fetch (can be configured)
DEFAULT_REGIONS = [
    "US-CA",  # California
    "US-NY",  # New York
    "US-TX",  # Texas
    "US-FL",  # Florida
]

# Number of days back to fetch (default: last 7 days)
DAYS_BACK = 7


def fetch_region_observations(region_code: str, days_back: int = DAYS_BACK) -> List[Dict]:
    """
    Fetch observations for a region from eBird API
    
    Args:
        region_code: eBird region code (e.g., "US-CA")
        days_back: Number of days back to fetch observations
        
    Returns:
        List of observation dictionaries
    """
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        print(f"Fetching observations for {region_code} from {start_date.date()} to {end_date.date()}...")
        
        # Fetch observations using ebird-api library
        # Note: The API may have rate limits, so we'll add delays between requests
        observations = get_observations(
            EBIRD_API_KEY,
            region_code,
            back=days_back
        )
        
        print(f"  ✓ Fetched {len(observations)} observations")
        return observations
        
    except Exception as e:
        print(f"  ✗ Error fetching observations for {region_code}: {e}")
        return []


def fetch_location_observations(lat: float, lon: float, dist: int = 25, days_back: int = DAYS_BACK) -> List[Dict]:
    """
    Fetch observations near a specific location
    
    Args:
        lat: Latitude
        lon: Longitude
        dist: Distance in kilometers
        days_back: Number of days back to fetch
        
    Returns:
        List of observation dictionaries
    """
    try:
        observations = get_nearby_observations(
            EBIRD_API_KEY,
            lat,
            lon,
            dist=dist,
            back=days_back
        )
        return observations
    except Exception as e:
        print(f"  ✗ Error fetching nearby observations: {e}")
        return []


def process_observation(obs_data: Dict, region_code: Optional[str] = None) -> Optional[BirdObservation]:
    """
    Convert eBird API observation data to database model
    
    Args:
        obs_data: Dictionary from eBird API
        
    Returns:
        BirdObservation object or None if invalid
    """
    try:
        # Parse observation date
        obs_date_str = obs_data.get('obsDt', '')
        if 'T' in obs_date_str:
            obs_date = datetime.fromisoformat(obs_date_str.replace('Z', '+00:00'))
        else:
            obs_date = datetime.strptime(obs_date_str, '%Y-%m-%d %H:%M')
        
        # Extract location data
        loc_data = obs_data.get('loc', {})
        if isinstance(loc_data, str):
            location_name = loc_data
            location_id = None
        else:
            location_name = loc_data.get('name', '')
            location_id = loc_data.get('id', '')
        
        # Extract region code from location name or use provided region_code
        # eBird API sometimes includes region in locName like "City, State US-CA"
        extracted_region = obs_data.get('subnational2Code') or obs_data.get('subnational1Code') or ''
        if not extracted_region and location_name and 'US-' in location_name:
            # Try to extract from location name
            parts = location_name.split('US-')
            if len(parts) > 1:
                extracted_region = 'US-' + parts[1].split()[0] if parts[1] else ''
        
        # Use provided region_code if available, otherwise use extracted
        final_region_code = region_code or extracted_region
        
        # Create observation object
        observation = BirdObservation(
            species_code=obs_data.get('speciesCode', ''),
            common_name=obs_data.get('comName', ''),
            scientific_name=obs_data.get('sciName', ''),
            observation_date=obs_date,
            latitude=obs_data.get('lat', None),
            longitude=obs_data.get('lng', None),
            location_id=location_id or obs_data.get('locId', ''),
            location_name=location_name or obs_data.get('locName', ''),
            region_code=final_region_code,
            county_code=obs_data.get('subnational2Code', ''),
            observation_count=obs_data.get('howMany', ''),
            has_media=1 if obs_data.get('hasMedia', False) else 0,
            approved=1 if obs_data.get('obsValid', True) else 0,  # obsValid indicates valid observation
            is_vocal=1 if obs_data.get('hasMedia', False) else 0,  # Infer vocalization from media
            source='ebird',
            fetched_at=datetime.utcnow()
        )
        
        return observation
        
    except Exception as e:
        print(f"  ✗ Error processing observation: {e}")
        return None


def save_observations(observations: List[BirdObservation], db_session):
    """
    Save observations to database, avoiding duplicates
    
    Args:
        observations: List of BirdObservation objects
        db_session: Database session
    """
    saved_count = 0
    skipped_count = 0
    
    for obs in observations:
        try:
            # Check if observation already exists
            # Use combination of species_code, location_id, and observation_date as unique key
            existing = db_session.query(BirdObservation).filter(
                BirdObservation.species_code == obs.species_code,
                BirdObservation.location_id == obs.location_id,
                BirdObservation.observation_date == obs.observation_date
            ).first()
            
            if not existing:
                db_session.add(obs)
                saved_count += 1
            else:
                skipped_count += 1
                
        except Exception as e:
            print(f"  ✗ Error saving observation: {e}")
            continue
    
    db_session.commit()
    print(f"  ✓ Saved {saved_count} new observations, skipped {skipped_count} duplicates")


def main():
    """Main function to fetch and store eBird data"""
    print("=" * 60)
    print("BloomingSongs - eBird Data Fetch")
    print(f"Started at: {datetime.now()}")
    print("=" * 60)
    
    # Initialize database
    init_db()
    
    # Create database session
    db = SessionLocal()
    
    try:
        total_observations = 0
        
        # Fetch data for each default region
        for region_code in DEFAULT_REGIONS:
            print(f"\nProcessing region: {region_code}")
            
            # Fetch observations
            obs_data_list = fetch_region_observations(region_code, DAYS_BACK)
            
            if not obs_data_list:
                print(f"  No observations found for {region_code}")
                continue
            
            # Process observations
            observations = []
            for obs_data in obs_data_list:
                obs = process_observation(obs_data, region_code=region_code)
                if obs:
                    observations.append(obs)
            
            # Save to database
            if observations:
                save_observations(observations, db)
                total_observations += len(observations)
            
            # Rate limiting: wait between API calls
            time.sleep(1)
        
        print("\n" + "=" * 60)
        print(f"✓ Data fetch complete!")
        print(f"  Total observations processed: {total_observations}")
        print(f"Finished at: {datetime.now()}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
