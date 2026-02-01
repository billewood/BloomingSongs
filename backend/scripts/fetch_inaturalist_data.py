#!/usr/bin/env python3
"""
Fetch bird vocalization data from iNaturalist API

This script fetches bird observations that have audio recordings attached,
which strongly indicates the bird was singing/vocalizing.

iNaturalist provides:
- sounds=True filter for observations with audio
- taxon_id filtering for birds (Aves = 3)
- place_id for geographic filtering
- quality_grade for research-grade verified observations
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.database import SessionLocal, BirdObservation, init_db
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Try to import pyinaturalist
try:
    from pyinaturalist import get_observations
except ImportError:
    print("Error: pyinaturalist not installed. Run: pip install pyinaturalist")
    sys.exit(1)

# Aves (Birds) taxon ID in iNaturalist
AVES_TAXON_ID = 3

# iNaturalist place IDs for regions
# These can be found at: https://www.inaturalist.org/places
REGION_PLACE_IDS = {
    "US-CA": 14,      # California
    "US-NY": 48,      # New York  
    "US-TX": 18,      # Texas
    "US-FL": 21,      # Florida
    "US-WA": 39,      # Washington
    "US-OR": 37,      # Oregon
    "US-AZ": 3,       # Arizona
    "US-CO": 6,       # Colorado
}

# Mapping of iNaturalist place IDs back to region codes
PLACE_ID_TO_REGION = {v: k for k, v in REGION_PLACE_IDS.items()}

# Default regions to fetch (using place IDs)
DEFAULT_PLACE_IDS = [
    14,   # California
    48,   # New York
    18,   # Texas
    21,   # Florida
]

# Maximum observations per region
MAX_OBSERVATIONS_PER_REGION = 500


def fetch_bird_audio_observations(
    place_id: int,
    max_results: int = MAX_OBSERVATIONS_PER_REGION,
    days_back: int = 30
) -> List[Dict]:
    """
    Fetch bird observations with audio recordings from iNaturalist
    
    Args:
        place_id: iNaturalist place ID
        max_results: Maximum number of observations to fetch
        days_back: How many days back to search
        
    Returns:
        List of observation dicts
    """
    d1 = datetime.now() - timedelta(days=days_back)
    
    try:
        # Query iNaturalist for bird observations with sounds
        response = get_observations(
            taxon_id=AVES_TAXON_ID,  # Birds
            place_id=place_id,
            sounds=True,  # Must have audio recordings
            quality_grade='research',  # Only verified observations
            d1=d1.strftime('%Y-%m-%d'),
            per_page=min(max_results, 200),  # API max is 200 per page
            order_by='observed_on',
            order='desc'
        )
        
        observations = response.get('results', [])
        
        # If we need more than 200, paginate
        if max_results > 200:
            total_fetched = len(observations)
            page = 2
            
            while total_fetched < max_results and total_fetched < response.get('total_results', 0):
                time.sleep(0.5)  # Rate limiting
                
                page_response = get_observations(
                    taxon_id=AVES_TAXON_ID,
                    place_id=place_id,
                    sounds=True,
                    quality_grade='research',
                    d1=d1.strftime('%Y-%m-%d'),
                    per_page=min(200, max_results - total_fetched),
                    page=page,
                    order_by='observed_on',
                    order='desc'
                )
                
                page_results = page_response.get('results', [])
                if not page_results:
                    break
                    
                observations.extend(page_results)
                total_fetched += len(page_results)
                page += 1
        
        return observations
        
    except Exception as e:
        print(f"  ✗ Error fetching iNaturalist data: {e}")
        return []


def process_inaturalist_observation(obs: Dict, region_code: str) -> Optional[Dict]:
    """
    Process a single iNaturalist observation into our format
    
    Args:
        obs: Raw observation from iNaturalist API
        region_code: Region code (e.g., US-CA)
        
    Returns:
        Processed observation dict or None if invalid
    """
    try:
        taxon = obs.get('taxon', {})
        if not taxon:
            return None
            
        # Get species info
        species_code = taxon.get('name', '').replace(' ', '_')[:50]  # Use scientific name as code
        common_name = taxon.get('preferred_common_name', taxon.get('name', ''))
        scientific_name = taxon.get('name', '')
        
        # Get observation date
        obs_date_str = obs.get('observed_on_details', {}).get('date') or obs.get('observed_on', '')
        try:
            if obs_date_str:
                obs_date = datetime.strptime(obs_date_str[:10], '%Y-%m-%d')
                obs_date = obs_date.replace(tzinfo=timezone.utc)
            else:
                obs_date = datetime.now(timezone.utc)
        except:
            obs_date = datetime.now(timezone.utc)
        
        # Get location info - can be a list [lat, lon] or a string "lat,lon"
        location = obs.get('location')
        latitude = None
        longitude = None
        
        if location:
            if isinstance(location, list) and len(location) >= 2:
                # Location is a list: [lat, lon]
                latitude = float(location[0]) if location[0] else None
                longitude = float(location[1]) if location[1] else None
            elif isinstance(location, str):
                # Location is a string: "lat,lon"
                parts = location.split(',')
                latitude = float(parts[0].strip()) if len(parts) > 0 else None
                longitude = float(parts[1].strip()) if len(parts) > 1 else None
        
        # Fallback to geojson if available
        if latitude is None or longitude is None:
            geojson = obs.get('geojson', {})
            if geojson and 'coordinates' in geojson:
                coords = geojson['coordinates']
                if coords and len(coords) >= 2:
                    longitude = float(coords[0])  # GeoJSON is [lon, lat]
                    latitude = float(coords[1])
        
        location_name = obs.get('place_guess', '')
        
        # Count sounds - more sounds typically means more singing
        sounds = obs.get('sounds', [])
        num_sounds = len(sounds)
        
        # Get observation ID for deduplication
        inat_id = str(obs.get('id', ''))
        
        return {
            'species_code': f"inat_{species_code}",  # Prefix to distinguish from eBird codes
            'common_name': common_name[:200] if common_name else species_code,
            'scientific_name': scientific_name[:200] if scientific_name else '',
            'observation_date': obs_date,
            'latitude': latitude,
            'longitude': longitude,
            'location_id': f"inat_{inat_id}",  # Use observation ID as location ID
            'location_name': location_name[:500] if location_name else '',
            'region_code': region_code,
            'observation_count': str(num_sounds) if num_sounds > 1 else '1',
            'has_media': 1,  # Always has media (sounds)
            'is_vocal': 1,  # Always vocal (has audio)
            'source': 'inaturalist',
            'inat_id': inat_id,
            'quality_grade': obs.get('quality_grade', ''),
        }
        
    except Exception as e:
        print(f"  ✗ Error processing observation: {e}")
        return None


def save_inaturalist_observations(observations: List[Dict], db_session) -> tuple:
    """
    Save iNaturalist observations to database
    
    Returns:
        Tuple of (saved_count, skipped_count)
    """
    saved = 0
    skipped = 0
    
    for obs in observations:
        if not obs:
            continue
            
        # Check for existing observation (by iNaturalist ID)
        existing = db_session.query(BirdObservation).filter(
            BirdObservation.location_id == obs['location_id'],
            BirdObservation.source == 'inaturalist'
        ).first()
        
        if existing:
            skipped += 1
            continue
        
        # Create new observation
        new_obs = BirdObservation(
            species_code=obs['species_code'],
            common_name=obs['common_name'],
            scientific_name=obs['scientific_name'],
            observation_date=obs['observation_date'],
            latitude=obs['latitude'],
            longitude=obs['longitude'],
            location_id=obs['location_id'],
            location_name=obs['location_name'],
            region_code=obs['region_code'],
            observation_count=obs['observation_count'],
            has_media=obs['has_media'],
            is_vocal=obs['is_vocal'],
            approved=1,  # Research grade = approved
            source=obs['source'],
            fetched_at=datetime.now(timezone.utc)
        )
        
        db_session.add(new_obs)
        saved += 1
    
    db_session.commit()
    return saved, skipped


def fetch_region_data(place_id: int, region_code: str) -> List[Dict]:
    """
    Fetch and process all bird audio observations for a region
    
    Args:
        place_id: iNaturalist place ID
        region_code: Region code (e.g., US-CA)
        
    Returns:
        List of processed observations
    """
    print(f"\nFetching iNaturalist data for {region_code} (place_id: {place_id})...")
    
    # Fetch raw observations
    raw_observations = fetch_bird_audio_observations(place_id)
    print(f"  Found {len(raw_observations)} bird observations with audio")
    
    # Process observations
    processed = []
    for obs in raw_observations:
        processed_obs = process_inaturalist_observation(obs, region_code)
        if processed_obs:
            processed.append(processed_obs)
    
    print(f"  ✓ Processed {len(processed)} valid observations")
    return processed


def main():
    """Main function"""
    print("=" * 60)
    print("BloomingSongs - iNaturalist Data Fetch")
    print(f"Started at: {datetime.now()}")
    print("=" * 60)
    print("\nFetching bird observations with audio recordings...")
    print("(Audio recordings indicate singing/vocalizing birds)")
    
    # Initialize database
    init_db()
    db = SessionLocal()
    
    try:
        total_observations = 0
        total_saved = 0
        
        for place_id in DEFAULT_PLACE_IDS:
            region_code = PLACE_ID_TO_REGION.get(place_id, f"place_{place_id}")
            
            # Fetch data for region
            observations = fetch_region_data(place_id, region_code)
            
            if observations:
                saved, skipped = save_inaturalist_observations(observations, db)
                total_observations += len(observations)
                total_saved += saved
                print(f"  Saved {saved} new, skipped {skipped} existing observations")
            
            # Rate limiting between regions
            time.sleep(1)
        
        print("\n" + "=" * 60)
        print(f"✓ Complete!")
        print(f"  Total observations found: {total_observations}")
        print(f"  New observations saved: {total_saved}")
        print(f"Finished at: {datetime.now()}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
