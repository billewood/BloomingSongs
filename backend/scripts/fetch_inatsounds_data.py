#!/usr/bin/env python3
"""
Fetch bird vocalization data from iNatSounds Dataset

This script downloads and processes the iNatSounds annotation files (not the audio).
The annotations contain metadata about 230,000 sound recordings including:
- Species (scientific + common name)
- Location (lat/long)
- Date recorded
- Duration

For BloomingSongs, we only need the metadata, not the actual audio files.
This keeps the download size small (~22 MB vs 133 GB for audio).

Data source: https://github.com/visipedia/inat_sounds
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional
import json
import gzip
import tarfile
import tempfile
import urllib.request
import shutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.database import SessionLocal, BirdObservation, init_db
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# iNatSounds 2024 annotation URLs (small files, ~22MB total)
ANNOTATION_URLS = {
    "train": "https://ml-inat-competition-datasets.s3.amazonaws.com/sounds/2024/train.json.tar.gz",
    "val": "https://ml-inat-competition-datasets.s3.amazonaws.com/sounds/2024/val.json.tar.gz",
    "test": "https://ml-inat-competition-datasets.s3.amazonaws.com/sounds/2024/test.json.tar.gz",
}

# Expected file sizes (for progress reporting)
EXPECTED_SIZES = {
    "train": 14 * 1024 * 1024,  # 14 MB
    "val": 3.7 * 1024 * 1024,   # 3.7 MB
    "test": 4 * 1024 * 1024,    # 4 MB
}

# Data directory
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "inatsounds"


def format_size(size_bytes: int) -> str:
    """Format bytes as human-readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def download_file(url: str, dest_path: Path, expected_size: int = None) -> bool:
    """Download a file with progress reporting"""
    print(f"  Downloading: {url.split('/')[-1]}")
    
    try:
        # Create a request with headers
        request = urllib.request.Request(url, headers={'User-Agent': 'BloomingSongs/1.0'})
        
        with urllib.request.urlopen(request, timeout=60) as response:
            total_size = int(response.headers.get('Content-Length', expected_size or 0))
            
            # Download in chunks
            downloaded = 0
            chunk_size = 8192
            
            with open(dest_path, 'wb') as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Progress indicator
                    if total_size > 0:
                        pct = (downloaded / total_size) * 100
                        print(f"\r  Progress: {format_size(downloaded)} / {format_size(total_size)} ({pct:.1f}%)", end="")
            
            print()  # Newline after progress
            return True
            
    except Exception as e:
        print(f"\n  ✗ Error downloading: {e}")
        return False


def extract_json_from_tar_gz(tar_gz_path: Path) -> Optional[Dict]:
    """Extract and parse JSON from a tar.gz file"""
    try:
        with tarfile.open(tar_gz_path, 'r:gz') as tar:
            # Find the JSON file in the archive
            for member in tar.getmembers():
                if member.name.endswith('.json'):
                    f = tar.extractfile(member)
                    if f:
                        return json.load(f)
        return None
    except Exception as e:
        print(f"  ✗ Error extracting: {e}")
        return None


def download_annotations() -> Dict[str, Dict]:
    """Download all annotation files and return parsed data"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    all_data = {}
    
    for split, url in ANNOTATION_URLS.items():
        tar_path = DATA_DIR / f"{split}.json.tar.gz"
        
        # Check if already downloaded
        if tar_path.exists():
            print(f"  {split}: Using cached file ({format_size(tar_path.stat().st_size)})")
        else:
            print(f"\n  Downloading {split} annotations...")
            if not download_file(url, tar_path, EXPECTED_SIZES.get(split)):
                continue
        
        # Extract and parse JSON
        print(f"  Extracting {split} annotations...")
        data = extract_json_from_tar_gz(tar_path)
        
        if data:
            all_data[split] = data
            print(f"  ✓ {split}: {len(data.get('audio', []))} recordings, {len(data.get('categories', []))} species")
        else:
            print(f"  ✗ Failed to parse {split} data")
    
    return all_data


def build_category_lookup(categories: List[Dict]) -> Dict[int, Dict]:
    """Build a lookup dict from category ID to category info"""
    return {cat['id']: cat for cat in categories}


def build_annotation_lookup(annotations: List[Dict]) -> Dict[int, int]:
    """Build a lookup from audio_id to category_id"""
    return {ann['audio_id']: ann['category_id'] for ann in annotations}


def filter_bird_observations(data: Dict, split_name: str) -> List[Dict]:
    """Filter observations to just birds (Aves) and format for our database"""
    
    categories = build_category_lookup(data.get('categories', []))
    annotations = build_annotation_lookup(data.get('annotations', []))
    audio_records = data.get('audio', [])
    
    bird_observations = []
    
    for audio in audio_records:
        audio_id = audio['id']
        category_id = annotations.get(audio_id)
        
        if category_id is None:
            continue
            
        category = categories.get(category_id)
        if category is None:
            continue
        
        # Filter for birds only (Aves)
        if category.get('class') != 'Aves' and category.get('supercategory') != 'Aves':
            continue
        
        # Parse date
        date_str = audio.get('date', '')
        try:
            if date_str:
                obs_date = datetime.strptime(date_str[:10], '%Y-%m-%d')
                obs_date = obs_date.replace(tzinfo=timezone.utc)
            else:
                obs_date = None
        except:
            obs_date = None
        
        # Skip if no date (can't use for time-based analysis)
        if obs_date is None:
            continue
        
        # Get location
        latitude = audio.get('latitude')
        longitude = audio.get('longitude')
        
        # Determine region code from lat/long
        region_code = get_region_from_coords(latitude, longitude)
        
        bird_observations.append({
            'species_code': f"inat_{category.get('name', '').replace(' ', '_')[:50]}",
            'common_name': category.get('common_name', category.get('name', ''))[:200],
            'scientific_name': category.get('name', '')[:200],
            'observation_date': obs_date,
            'latitude': latitude,
            'longitude': longitude,
            'location_id': f"inatsounds_{audio_id}",
            'location_name': '',
            'region_code': region_code,
            'observation_count': '1',
            'has_media': 1,  # Has audio
            'is_vocal': 1,   # It's a sound recording!
            'source': 'inatsounds',
            'duration': audio.get('duration'),
        })
    
    return bird_observations


def get_region_from_coords(lat: Optional[float], lon: Optional[float]) -> str:
    """
    Determine US region code from coordinates.
    Returns empty string if not in a supported US state.
    """
    if lat is None or lon is None:
        return ''
    
    # Simple bounding boxes for US states we support
    # Format: (min_lat, max_lat, min_lon, max_lon)
    regions = {
        'US-CA': (32.5, 42.0, -124.5, -114.0),   # California
        'US-NY': (40.5, 45.0, -79.8, -71.8),     # New York
        'US-TX': (25.8, 36.5, -106.7, -93.5),    # Texas
        'US-FL': (24.5, 31.0, -87.6, -80.0),     # Florida
        'US-WA': (45.5, 49.0, -124.8, -116.9),   # Washington
        'US-OR': (42.0, 46.3, -124.6, -116.5),   # Oregon
        'US-AZ': (31.3, 37.0, -114.8, -109.0),   # Arizona
        'US-CO': (37.0, 41.0, -109.1, -102.0),   # Colorado
    }
    
    for region_code, (min_lat, max_lat, min_lon, max_lon) in regions.items():
        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            return region_code
    
    return ''


def save_observations(observations: List[Dict], db_session) -> tuple:
    """Save observations to database"""
    saved = 0
    skipped = 0
    
    for obs in observations:
        # Check for existing observation
        existing = db_session.query(BirdObservation).filter(
            BirdObservation.location_id == obs['location_id'],
            BirdObservation.source == 'inatsounds'
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
            approved=1,
            source=obs['source'],
            fetched_at=datetime.now(timezone.utc)
        )
        
        db_session.add(new_obs)
        saved += 1
        
        # Commit in batches
        if saved % 1000 == 0:
            db_session.commit()
            print(f"    Saved {saved} observations...")
    
    db_session.commit()
    return saved, skipped


def main():
    """Main function"""
    print("=" * 60)
    print("BloomingSongs - iNatSounds Data Fetch")
    print(f"Started at: {datetime.now()}")
    print("=" * 60)
    print("\nThis downloads annotation metadata only (~22 MB)")
    print("NOT the audio files (which are ~133 GB)")
    print()
    
    # Check disk space
    import shutil
    total, used, free = shutil.disk_usage("/")
    print(f"💾 Available disk space: {format_size(free)}")
    
    if free < 100 * 1024 * 1024:  # Less than 100 MB free
        print("⚠️  Warning: Low disk space!")
    
    # Download annotations
    print("\n📥 Downloading annotation files...")
    all_data = download_annotations()
    
    if not all_data:
        print("✗ No data downloaded")
        return
    
    # Initialize database
    print("\n🗄️  Initializing database...")
    init_db()
    db = SessionLocal()
    
    try:
        total_birds = 0
        total_saved = 0
        total_us_birds = 0
        
        for split_name, data in all_data.items():
            print(f"\n📊 Processing {split_name} data...")
            
            # Filter for birds
            bird_obs = filter_bird_observations(data, split_name)
            total_birds += len(bird_obs)
            
            # Count US observations
            us_birds = [b for b in bird_obs if b['region_code']]
            total_us_birds += len(us_birds)
            
            print(f"  Found {len(bird_obs)} bird recordings")
            print(f"  {len(us_birds)} in supported US regions")
            
            # Save US observations to database
            if us_birds:
                saved, skipped = save_observations(us_birds, db)
                total_saved += saved
                print(f"  Saved {saved} new, skipped {skipped} existing")
        
        print("\n" + "=" * 60)
        print("✓ Complete!")
        print(f"  Total bird recordings in dataset: {total_birds:,}")
        print(f"  Bird recordings in US regions: {total_us_birds:,}")
        print(f"  New observations saved: {total_saved:,}")
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
