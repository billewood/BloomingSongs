#!/usr/bin/env python3
"""
Fetch bird singing/vocalization data from eBird API

This script fetches checklists and extracts observations with singing/courtship
breeding codes (S, S7, C, CC, etc.)
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Set
import time
import requests

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.database import SessionLocal, BirdObservation, init_db
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Configuration
EBIRD_API_KEY = os.getenv("EBIRD_API_KEY")
if not EBIRD_API_KEY:
    raise ValueError("EBIRD_API_KEY environment variable not set")

API_BASE = "https://api.ebird.org/v2"
HEADERS = {"X-eBirdApiToken": EBIRD_API_KEY}

# Breeding codes that indicate singing/vocalization
SINGING_CODES = {
    "S",    # Singing Male
    "S1",   # Singing Male (first observation)
    "S7",   # Singing Male present 7+ days
    "OS",   # Other Singing
}

COURTSHIP_CODES = {
    "C",    # Courtship display
    "CC",   # Courtship, Copulation, or Copulating
    "D",    # Display/Courtship
}

VOCALIZATION_CODES = SINGING_CODES | COURTSHIP_CODES

# Default regions to fetch
DEFAULT_REGIONS = [
    "US-CA",  # California
    "US-NY",  # New York
    "US-TX",  # Texas
    "US-FL",  # Florida
]

# How many checklists to fetch per region
MAX_CHECKLISTS_PER_REGION = 200


def get_recent_checklists(region_code: str, max_results: int = 100) -> List[Dict]:
    """Fetch recent checklists for a region"""
    url = f"{API_BASE}/product/lists/{region_code}"
    params = {"maxResults": max_results}
    
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"  ✗ Error fetching checklists: {e}")
        return []


def get_checklist_details(sub_id: str) -> Optional[Dict]:
    """Fetch full checklist details including obsAux"""
    url = f"{API_BASE}/product/checklist/view/{sub_id}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"  ✗ Error fetching checklist {sub_id}: {e}")
        return None


def extract_singing_observations(checklist: Dict, region_code: str) -> List[Dict]:
    """
    Extract observations with singing/vocalization breeding codes
    
    Returns list of observation dicts with singing data
    """
    singing_obs = []
    
    obs_date_str = checklist.get("obsDt", "")
    try:
        if "T" in obs_date_str:
            obs_date = datetime.fromisoformat(obs_date_str.replace("Z", "+00:00"))
        else:
            obs_date = datetime.strptime(obs_date_str, "%Y-%m-%d %H:%M")
    except:
        obs_date = datetime.now(timezone.utc)
    
    loc_id = checklist.get("locId", "")
    sub_id = checklist.get("subId", "")
    subnational1 = checklist.get("subnational1Code", region_code)
    
    for obs in checklist.get("obs", []):
        species_code = obs.get("speciesCode", "")
        how_many = obs.get("howManyStr", "1")
        obs_id = obs.get("obsId", "")
        
        # Check obsAux for breeding codes
        breeding_code = None
        is_singing = False
        is_courtship = False
        
        for aux in obs.get("obsAux", []):
            if aux.get("fieldName") == "breeding_code":
                breeding_code = aux.get("auxCode", "")
                if breeding_code in SINGING_CODES:
                    is_singing = True
                elif breeding_code in COURTSHIP_CODES:
                    is_courtship = True
        
        # Only include observations with vocalization codes
        if is_singing or is_courtship:
            singing_obs.append({
                "species_code": species_code,
                "observation_date": obs_date,
                "location_id": loc_id,
                "checklist_id": sub_id,
                "obs_id": obs_id,
                "region_code": subnational1,
                "how_many": how_many,
                "breeding_code": breeding_code,
                "is_singing": is_singing,
                "is_courtship": is_courtship,
            })
    
    return singing_obs


def fetch_region_singing_data(region_code: str, max_checklists: int = MAX_CHECKLISTS_PER_REGION) -> List[Dict]:
    """
    Fetch all singing observations for a region
    
    This fetches checklists and extracts observations with singing/courtship codes
    """
    print(f"\nFetching singing data for {region_code}...")
    
    # Get recent checklists
    checklists = get_recent_checklists(region_code, max_checklists)
    print(f"  Found {len(checklists)} recent checklists")
    
    all_singing_obs = []
    checklists_with_singing = 0
    
    for i, cl_summary in enumerate(checklists):
        sub_id = cl_summary.get("subId")
        
        # Get full checklist details
        checklist = get_checklist_details(sub_id)
        if not checklist:
            continue
        
        # Extract singing observations
        singing_obs = extract_singing_observations(checklist, region_code)
        
        if singing_obs:
            all_singing_obs.extend(singing_obs)
            checklists_with_singing += 1
        
        # Progress indicator every 50 checklists
        if (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/{len(checklists)} checklists, found {len(all_singing_obs)} singing observations")
        
        # Rate limiting
        time.sleep(0.1)  # 100ms between requests
    
    print(f"  ✓ Found {len(all_singing_obs)} singing observations in {checklists_with_singing} checklists")
    return all_singing_obs


def save_singing_observations(observations: List[Dict], db_session) -> tuple:
    """Save singing observations to database"""
    from ebird.api.requests.taxonomy import get_taxonomy
    
    # Get taxonomy for species names (cached)
    try:
        taxonomy = {t["speciesCode"]: t for t in get_taxonomy(EBIRD_API_KEY)}
    except:
        taxonomy = {}
    
    saved = 0
    updated = 0
    
    for obs in observations:
        species_code = obs["species_code"]
        species_info = taxonomy.get(species_code, {})
        
        # Check for existing observation
        existing = db_session.query(BirdObservation).filter(
            BirdObservation.species_code == species_code,
            BirdObservation.location_id == obs["location_id"],
            BirdObservation.observation_date == obs["observation_date"]
        ).first()
        
        if existing:
            # Update existing record with singing data
            if obs["is_singing"] or obs["is_courtship"]:
                existing.is_vocal = 1
                updated += 1
            continue
        
        # Create new observation
        new_obs = BirdObservation(
            species_code=species_code,
            common_name=species_info.get("comName", species_code),
            scientific_name=species_info.get("sciName", ""),
            observation_date=obs["observation_date"],
            location_id=obs["location_id"],
            region_code=obs["region_code"],
            observation_count=obs["how_many"],
            is_vocal=1 if obs["is_singing"] else 0,
            has_media=1 if obs["breeding_code"] else 0,
            approved=1,
            source="ebird_singing",
            fetched_at=datetime.now(timezone.utc)
        )
        
        db_session.add(new_obs)
        saved += 1
    
    db_session.commit()
    return saved, updated


def main():
    """Main function"""
    print("=" * 60)
    print("BloomingSongs - Singing Data Fetch")
    print(f"Started at: {datetime.now()}")
    print("=" * 60)
    
    # Initialize database
    init_db()
    db = SessionLocal()
    
    try:
        total_singing = 0
        
        for region_code in DEFAULT_REGIONS:
            # Fetch singing data
            singing_obs = fetch_region_singing_data(region_code)
            
            if singing_obs:
                saved, updated = save_singing_observations(singing_obs, db)
                total_singing += len(singing_obs)
                print(f"  Saved {saved} new, updated {updated} existing observations")
            
            # Rate limiting between regions
            time.sleep(1)
        
        print("\n" + "=" * 60)
        print(f"✓ Complete! Found {total_singing} total singing observations")
        print(f"Finished at: {datetime.now()}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
