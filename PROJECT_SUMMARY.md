# BloomingSongs Project Summary

## What Was Created

A complete full-stack application for tracking bird singing activity using eBird data.

## Project Structure

```
BloomingSongs/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── main.py            # API endpoints (current, trends, historical)
│   │   └── schemas.py         # Pydantic request/response models
│   ├── models/
│   │   └── database.py        # SQLAlchemy database models
│   ├── scripts/
│   │   ├── init_db.py         # Database initialization
│   │   ├── fetch_ebird_data.py # Daily eBird data fetcher
│   │   └── calculate_trends.py # Trend calculation script
│   └── .env.example           # Environment variable template
│
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── App.jsx            # Main React component
│   │   ├── main.jsx           # React entry point
│   │   └── index.css          # Styling
│   ├── index.html             # HTML template
│   ├── package.json           # Node.js dependencies
│   └── vite.config.js         # Vite configuration
│
├── data/                       # Database storage (created on init)
│
├── README.md                   # Project overview
├── SETUP.md                    # Detailed setup instructions
├── ARCHITECTURE.md             # System architecture documentation
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git ignore rules
└── start.sh                    # Quick start script
```

## Key Features Implemented

### 1. Data Fetching (`backend/scripts/fetch_ebird_data.py`)
- Fetches bird observations from eBird API
- Supports multiple regions (CA, NY, TX, FL)
- Stores observations in SQLite database
- Avoids duplicates
- Handles API rate limiting

### 2. Database Models (`backend/models/database.py`)
- **BirdObservation**: Individual observations with metadata
- **BirdTrend**: Calculated trend comparisons
- **DailySummary**: Aggregated daily statistics
- Proper indexing for performance

### 3. API Endpoints (`backend/app/main.py`)
- `GET /api/birds/current` - Current singing birds
- `GET /api/birds/trends` - Rising/falling trends
- `GET /api/birds/historical` - Historical data over time
- `GET /api/birds/top` - Top singing birds
- `GET /api/health` - Health check

### 4. Frontend (`frontend/src/App.jsx`)
- Three main views:
  - **Current Activity**: Shows most active birds
  - **Trends**: Shows rising/falling birds with percentages
  - **Historical**: Interactive line chart of trends over time
- Region selection (CA, NY, TX, FL)
- Time period selection (3, 7, 14, 30 days)
- Beautiful, modern UI with gradient background

### 5. Trend Analysis
- Compares current period vs previous period
- Calculates percentage change
- Categorizes as "rising", "falling", or "stable"
- Can be run manually or scheduled

## How It Works

1. **Daily Data Fetch**:
   - Script runs daily (via cron or manual)
   - Fetches observations from eBird API for configured regions
   - Stores in database, avoiding duplicates

2. **Trend Calculation** (optional):
   - Compares current period with previous period
   - Calculates which birds are rising/falling
   - Stores trend data for quick access

3. **API Serving**:
   - FastAPI serves REST endpoints
   - Queries database based on user parameters
   - Returns JSON data

4. **Frontend Display**:
   - React app fetches from API
   - Displays data in lists and charts
   - Updates based on user selections

## Next Steps to Get Started

1. **Get eBird API Key**:
   - Visit https://ebird.org/api/keygen
   - Create account if needed
   - Generate API key

2. **Configure Environment**:
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env and add your EBIRD_API_KEY
   ```

3. **Initialize Database**:
   ```bash
   cd backend
   python scripts/init_db.py
   ```

4. **Fetch Initial Data**:
   ```bash
   python scripts/fetch_ebird_data.py
   ```

5. **Start Backend**:
   ```bash
   uvicorn app.main:app --reload
   ```

6. **Start Frontend** (in new terminal):
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

7. **View Application**:
   - Open http://localhost:3000 in browser

## Customization Options

### Add More Regions
Edit `DEFAULT_REGIONS` in `backend/scripts/fetch_ebird_data.py`:
```python
DEFAULT_REGIONS = [
    "US-CA",  # California
    "US-NY",  # New York
    "US-TX",  # Texas
    "US-FL",  # Florida
    "US-WA",  # Add Washington
    # ... add more
]
```

### Change Time Periods
Modify the `days` parameter in API calls or frontend controls.

### Enhance Trend Analysis
Modify `calculate_trends.py` to:
- Use statistical methods (moving averages, seasonality)
- Compare multiple periods
- Add confidence intervals

### Add Location-Based Queries
Use latitude/longitude parameters in API calls:
```python
GET /api/birds/current?lat=37.7749&lon=-122.4194&days=7
```

## Technical Stack

- **Backend**: Python 3.10+, FastAPI, SQLAlchemy, SQLite
- **Frontend**: React 18, Vite, Recharts
- **Data Source**: eBird API 2.0
- **Database**: SQLite (can migrate to PostgreSQL for production)

## Notes

- eBird API has rate limits (typically 10,000 requests/day)
- The app infers "singing" from observation frequency and media presence
- SQLite is fine for development; consider PostgreSQL for production
- Daily data fetch can be scheduled via cron or system scheduler

## Support

For issues or questions:
1. Check SETUP.md for troubleshooting
2. Review ARCHITECTURE.md for system details
3. Check eBird API documentation for data source questions
