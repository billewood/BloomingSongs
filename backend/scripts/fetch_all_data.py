#!/usr/bin/env python3
"""
Combined data fetch script for BloomingSongs

This script fetches singing/vocalization data from multiple sources:
1. eBird - Using breeding codes (S, S7, C, etc.) from checklists
2. iNatSounds - Using the iNaturalist Sounds Dataset (bulk download, no API limits)

Run daily/weekly to keep data current.

Note: We use iNatSounds dataset instead of iNaturalist API because:
- No API rate limits (API caps calls per hour)
- Curated dataset of 230,000+ audio recordings
- Only need metadata files (~22 MB), not audio (~133 GB)
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import argparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.database import SessionLocal, BirdObservation, init_db


def get_database_stats(db_session) -> dict:
    """Get current database statistics"""
    from sqlalchemy import func
    
    total = db_session.query(func.count(BirdObservation.id)).scalar() or 0
    ebird_count = db_session.query(func.count(BirdObservation.id)).filter(
        BirdObservation.source.like('%ebird%')
    ).scalar() or 0
    # iNaturalist includes both API data and iNatSounds dataset
    inat_count = db_session.query(func.count(BirdObservation.id)).filter(
        BirdObservation.source.in_(['inaturalist', 'inatsounds'])
    ).scalar() or 0
    vocal_count = db_session.query(func.count(BirdObservation.id)).filter(
        BirdObservation.is_vocal == 1
    ).scalar() or 0
    
    return {
        'total': total,
        'ebird': ebird_count,
        'inaturalist': inat_count,
        'vocal': vocal_count,
    }


def run_ebird_fetch():
    """Run eBird data fetch"""
    print("\n" + "=" * 60)
    print("FETCHING FROM eBIRD")
    print("=" * 60)
    
    try:
        # Import and run eBird fetcher
        from scripts.fetch_singing_data import main as ebird_main
        ebird_main()
        return True
    except Exception as e:
        print(f"✗ eBird fetch failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_inatsounds_fetch():
    """Run iNatSounds dataset fetch (bulk download, no API limits)"""
    print("\n" + "=" * 60)
    print("FETCHING FROM iNATSOUNDS DATASET")
    print("=" * 60)
    
    try:
        # Import and run iNatSounds fetcher
        from scripts.fetch_inatsounds_data import main as inatsounds_main
        inatsounds_main()
        return True
    except Exception as e:
        print(f"✗ iNatSounds fetch failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Fetch bird singing data from multiple sources'
    )
    parser.add_argument(
        '--source',
        choices=['all', 'ebird', 'inaturalist', 'inatsounds'],
        default='all',
        help='Which data source(s) to fetch from (default: all). "inaturalist" and "inatsounds" are equivalent.'
    )
    parser.add_argument(
        '--stats-only',
        action='store_true',
        help='Only show database statistics, do not fetch new data'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("BloomingSongs - Combined Data Fetch")
    print(f"Started at: {datetime.now()}")
    print("=" * 60)
    
    # Initialize database
    init_db()
    db = SessionLocal()
    
    try:
        # Show initial stats
        print("\n📊 Database Statistics (Before):")
        stats_before = get_database_stats(db)
        print(f"   Total observations: {stats_before['total']:,}")
        print(f"   From eBird: {stats_before['ebird']:,}")
        print(f"   From iNaturalist: {stats_before['inaturalist']:,}")
        print(f"   Vocal/Singing: {stats_before['vocal']:,}")
        
        if args.stats_only:
            return
        
        # Run fetchers based on source argument
        ebird_success = True
        inat_success = True
        
        if args.source in ['all', 'ebird']:
            ebird_success = run_ebird_fetch()
        
        if args.source in ['all', 'inaturalist', 'inatsounds']:
            inat_success = run_inatsounds_fetch()
        
        # Refresh session to see new data
        db.expire_all()
        
        # Show final stats
        print("\n" + "=" * 60)
        print("📊 Database Statistics (After):")
        stats_after = get_database_stats(db)
        print(f"   Total observations: {stats_after['total']:,}")
        print(f"   From eBird: {stats_after['ebird']:,}")
        print(f"   From iNaturalist: {stats_after['inaturalist']:,}")
        print(f"   Vocal/Singing: {stats_after['vocal']:,}")
        
        # Show what was added
        print("\n📈 New Data Added:")
        print(f"   Total: +{stats_after['total'] - stats_before['total']:,}")
        print(f"   eBird: +{stats_after['ebird'] - stats_before['ebird']:,}")
        print(f"   iNaturalist: +{stats_after['inaturalist'] - stats_before['inaturalist']:,}")
        
        print("\n" + "=" * 60)
        if ebird_success and inat_success:
            print("✓ All fetches completed successfully!")
        else:
            print("⚠ Some fetches had issues (see errors above)")
        print(f"Finished at: {datetime.now()}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
