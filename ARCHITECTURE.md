# BloomingSongs Architecture

## Overview

BloomingSongs is a full-stack application that tracks bird singing activity using eBird data. It consists of:

1. **Backend**: FastAPI-based REST API
2. **Frontend**: React web application
3. **Data Layer**: SQLite database with daily data updates
4. **Data Fetching**: Automated scripts for eBird API integration

## System Architecture

```
┌─────────────┐
│   eBird     │
│    API      │
└──────┬──────┘
       │
       │ Daily Fetch
       ▼
┌─────────────────┐
│  Data Fetcher   │
│  (Python Script)│
└──────┬──────────┘
       │
       │ Store Observations
       ▼
┌─────────────────┐
│   SQLite DB     │
│  (Observations) │
└──────┬──────────┘
       │
       │ Query
       ▼
┌─────────────────┐      ┌──────────────┐
│  FastAPI Backend│◄────►│ React Frontend│
│  (REST API)     │      │  (Web UI)     │
└─────────────────┘      └──────────────┘
```

## Components

### Backend (`backend/`)

#### API Layer (`app/main.py`)
- **GET /api/birds/current**: Current bird activity for a region
- **GET /api/birds/trends**: Trend analysis (rising/falling birds)
- **GET /api/birds/historical**: Historical data over time
- **GET /api/birds/top**: Top singing birds

#### Data Models (`models/database.py`)
- **BirdObservation**: Individual observations from eBird
- **BirdTrend**: Calculated trend data comparing periods
- **DailySummary**: Aggregated daily statistics

#### Scripts (`scripts/`)
- **init_db.py**: Initialize database schema
- **fetch_ebird_data.py**: Daily data fetch from eBird API
- **calculate_trends.py**: Calculate trend metrics

### Frontend (`frontend/`)

#### Components
- **App.jsx**: Main application component with tabs
  - Current Activity tab
  - Trends tab
  - Historical tab

#### Features
- Region selection (CA, NY, TX, FL)
- Time period selection (3, 7, 14, 30 days)
- Interactive charts (Recharts)
- Real-time data updates

### Data Flow

1. **Data Collection**:
   - Daily script fetches observations from eBird API
   - Stores in SQLite database
   - Avoids duplicates using composite keys

2. **Trend Calculation**:
   - Compares current period vs previous period
   - Calculates percentage change
   - Categorizes as "rising", "falling", or "stable"

3. **API Serving**:
   - FastAPI queries database
   - Returns JSON responses
   - Supports filtering by region, date range

4. **Frontend Display**:
   - React fetches from API
   - Displays lists and charts
   - Updates based on user selections

## Database Schema

### bird_observations
- Stores individual eBird observations
- Indexed by date, species, location
- Includes metadata (coordinates, location names, etc.)

### bird_trends
- Aggregated trend calculations
- Compares two time periods
- Includes change percentages and directions

### daily_summaries
- Daily aggregated statistics
- Top species per day
- Used for quick lookups

## Data Sources

### eBird API
- Primary data source
- Provides observation records
- Includes location, species, date/time
- Rate limited (10,000 requests/day)

### Future Sources
- Could integrate:
  - Merlin Sound ID data
  - Xeno-canto recordings
  - Local birding databases

## Key Design Decisions

1. **SQLite**: Lightweight, file-based database suitable for single-server deployment
2. **Daily Updates**: Balance between data freshness and API rate limits
3. **Inferred Vocalization**: Since eBird doesn't explicitly mark "singing", we infer from:
   - Observations with media (often audio)
   - High observation frequency
   - Breeding season timing

4. **Trend Calculation**: Simple but effective comparison of two periods
   - Can be enhanced with statistical methods
   - Could add seasonality adjustments

## Scalability Considerations

### Current Limitations
- Single SQLite database (not ideal for high concurrency)
- No caching layer
- Synchronous API calls

### Future Improvements
- Migrate to PostgreSQL for production
- Add Redis caching for frequently accessed data
- Implement background job queue for data fetching
- Add API response caching
- Consider CDN for frontend assets

## Security

- API key stored in environment variables
- CORS configured (should be restricted in production)
- Input validation via Pydantic schemas
- SQL injection protection via SQLAlchemy ORM

## Deployment Options

1. **Local Development**: Run both backend and frontend locally
2. **Single Server**: Deploy both on same server (e.g., DigitalOcean, AWS EC2)
3. **Separated**: Backend on server, frontend on CDN (Vercel, Netlify)
4. **Containerized**: Docker containers for easy deployment

## Monitoring & Maintenance

### Daily Tasks
- Run `fetch_ebird_data.py` to update observations
- Optional: Run `calculate_trends.py` to update trends

### Monitoring
- Check API health endpoint: `/api/health`
- Monitor database size
- Track API rate limit usage
- Review error logs

### Maintenance
- Periodic database cleanup (remove old observations if needed)
- Update dependencies regularly
- Monitor eBird API changes
