#!/usr/bin/env python3
"""
Initialize the BloomingSongs database
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.database import init_db

if __name__ == "__main__":
    print("Initializing BloomingSongs database...")
    init_db()
    print("✓ Database initialized successfully!")
