# BloomingSongs

Track which birds are singing in your area using eBird and iNaturalist data.

## Features

- **Current Activity**: See which birds are most actively singing in your region
- **Trends**: Track rising and falling bird activity over time
- **Historical Data**: View 90-day trends with interactive charts
- **Multi-Source Data**: Combines data from eBird and iNaturalist

## Architecture

```
Frontend (Vercel)          Backend (Render)
    Next.js         →      FastAPI (Python)
        │                       │
        └── /api/birds/* ──────→┘
                                │
                    ┌───────────┴───────────┐
                    ↓                       ↓
               eBird API            iNaturalist API
        (breeding codes S, S7)     (audio recordings)
```

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- eBird API key ([get one here](https://ebird.org/api/keygen))

### Setup

1. **Clone and setup backend**:
   ```bash
   cd backend
   python -m venv ../venv
   source ../venv/bin/activate
   pip install -r requirements.txt
   
   # Create .env file
   echo "EBIRD_API_KEY=your_key_here" > .env
   
   # Initialize database
   python scripts/init_db.py
   
   # Fetch data from all sources
   python scripts/fetch_all_data.py
   ```

2. **Start backend**:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

3. **Setup and start frontend** (new terminal):
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. Open http://localhost:3000

## Data Fetching

You can fetch data from specific sources:

```bash
# Fetch from all sources (eBird + iNaturalist)
python scripts/fetch_all_data.py

# Fetch only from eBird
python scripts/fetch_all_data.py --source ebird

# Fetch only from iNaturalist
python scripts/fetch_all_data.py --source inaturalist

# View database statistics only
python scripts/fetch_all_data.py --stats-only
```

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for full deployment instructions.

**Quick summary**:
- Frontend deploys to **Vercel**
- Backend deploys to **Render**
- Set `BACKEND_URL` in Vercel to point to Render

## Project Structure

```
BloomingSongs/
├── backend/              # Python FastAPI backend
│   ├── app/             # API endpoints
│   ├── models/          # Database models
│   ├── scripts/         # Data fetching scripts
│   │   ├── fetch_all_data.py       # Combined fetcher
│   │   ├── fetch_singing_data.py   # eBird fetcher
│   │   └── fetch_inaturalist_data.py  # iNaturalist fetcher
│   └── requirements.txt
├── frontend/             # Next.js frontend
│   ├── pages/           # Next.js pages & API routes
│   ├── styles/          # CSS/Tailwind styles
│   └── package.json
└── DEPLOYMENT.md         # Deployment guide
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/api/birds/current` | Current bird activity by region |
| `/api/birds/trends` | Rising/falling trends |
| `/api/birds/historical` | 90-day historical data |
| `/api/birds/sources` | Data source statistics |
| `/api/health` | Health check |

### Filtering by Source

Most endpoints accept a `source` query parameter:
- `source=ebird` - Only eBird data
- `source=inaturalist` - Only iNaturalist data
- `source=all` (default) - Combined data

## Data Sources

### eBird
Data from [eBird](https://ebird.org), the world's largest biodiversity-related citizen science project. We specifically track observations with **singing/courtship breeding codes**:
- S, S1, S7: Singing Male
- C, CC: Courtship
- OS: Other Singing

### iNaturalist (via iNatSounds Dataset)
Data from the [iNatSounds Dataset](https://github.com/visipedia/inat_sounds), a curated collection of **230,000 audio recordings** from iNaturalist. We use this bulk dataset instead of the API because:
- No API rate limits (API caps calls per hour)
- Pre-curated bird vocalizations (189,662 bird recordings)
- Small metadata files (~22 MB) vs full audio (~133 GB)

The dataset includes recordings from **3,846 bird species** with location and date metadata.

## Data Sizes

| Source | Size | Notes |
|--------|------|-------|
| eBird API | ~1 MB | Real-time checklist data |
| iNatSounds metadata | ~22 MB | Annotations only, not audio |
| SQLite database | ~48 MB | All processed observations |

## License

MIT
