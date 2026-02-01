# BloomingSongs Setup Guide

## Prerequisites

- Python 3.10 or higher
- Node.js 16+ and npm (for frontend)
- eBird API key (free at https://ebird.org/api/keygen)

## Step-by-Step Setup

### 1. Clone/Navigate to Project

```bash
cd /Users/williamwood/Code/BloomingSongs
```

### 2. Set Up Python Backend

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure eBird API Key

Create a `.env` file in the `backend` directory:

```bash
cd backend
cp .env.example .env
```

Edit `.env` and add your eBird API key:

```
EBIRD_API_KEY=your_actual_api_key_here
```

Get your API key at: https://ebird.org/api/keygen

### 4. Initialize Database

```bash
cd backend
python scripts/init_db.py
```

This creates the SQLite database at `data/bloomingsongs.db`

### 5. Fetch Initial Data

```bash
cd backend
python scripts/fetch_ebird_data.py
```

This will fetch bird observations for default regions (CA, NY, TX, FL) from the last 7 days.

**Note**: The first run may take a few minutes as it fetches data from eBird's API. Subsequent runs will be faster as they only fetch new data.

### 6. Calculate Trends (Optional)

After fetching data, you can calculate trends:

```bash
python scripts/calculate_trends.py
```

### 7. Start Backend Server

```bash
cd backend
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

You can test it by visiting:
- http://localhost:8000/api/health
- http://localhost:8000/api/birds/current?region_code=US-CA

### 8. Set Up Frontend

In a new terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Daily Data Updates

To keep data current, set up a daily cron job or scheduled task:

```bash
# Edit crontab
crontab -e

# Add this line to run daily at 2 AM
0 2 * * * cd /Users/williamwood/Code/BloomingSongs/backend && /path/to/venv/bin/python scripts/fetch_ebird_data.py >> logs/fetch.log 2>&1
```

Or use a system scheduler like `launchd` on macOS.

## Troubleshooting

### API Key Issues

- Make sure your `.env` file is in the `backend` directory
- Verify your API key is correct at https://ebird.org/api/keygen
- Check that the key doesn't have extra spaces or quotes

### Database Issues

- If you get database errors, try deleting `data/bloomingsongs.db` and running `init_db.py` again
- Make sure the `data` directory exists and is writable

### API Rate Limits

- eBird API has rate limits (typically 10,000 requests per day)
- If you hit limits, reduce the number of regions or increase delays between requests
- The script includes 1-second delays between region fetches

### Frontend Connection Issues

- Make sure the backend is running on port 8000
- Check that the Vite proxy is configured correctly in `vite.config.js`
- Check browser console for CORS errors

## Project Structure

```
BloomingSongs/
├── backend/
│   ├── app/              # FastAPI application
│   │   ├── main.py       # API endpoints
│   │   └── schemas.py    # Request/response models
│   ├── models/           # Database models
│   │   └── database.py   # SQLAlchemy models
│   ├── scripts/          # Utility scripts
│   │   ├── init_db.py    # Initialize database
│   │   ├── fetch_ebird_data.py  # Daily data fetch
│   │   └── calculate_trends.py  # Trend calculations
│   └── .env              # Environment variables (create this)
├── frontend/             # React frontend
│   ├── src/
│   │   ├── App.jsx       # Main app component
│   │   └── main.jsx      # Entry point
│   └── package.json
├── data/                 # Database and data files
└── requirements.txt      # Python dependencies
```

## Next Steps

1. Customize regions: Edit `DEFAULT_REGIONS` in `fetch_ebird_data.py`
2. Add location-based queries: Use latitude/longitude in API calls
3. Enhance trend analysis: Modify `calculate_trends.py` for more sophisticated analysis
4. Add more visualizations: Extend the frontend with additional charts
5. Deploy: Consider deploying to a cloud service for 24/7 availability
