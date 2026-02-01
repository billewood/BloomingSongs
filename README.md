# BloomingSongs

Track which birds are singing in your area using eBird data.

## Features

- **Current Activity**: See which birds are most actively singing in your region
- **Trends**: Track rising and falling bird activity over time
- **Historical Data**: View 90-day trends with interactive charts

## Architecture

```
Frontend (Vercel)          Backend (Render)
    Next.js         →      FastAPI (Python)
        │                       │
        └── /api/birds/* ──────→┘
                                │
                           eBird API
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
   
   # Fetch initial data
   python scripts/fetch_singing_data.py
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
| `/api/health` | Health check |

## Data Source

Data is sourced from [eBird](https://ebird.org), the world's largest biodiversity-related citizen science project. The app specifically tracks observations with **singing/courtship breeding codes** (S, S7, C, CC, etc.).

## License

MIT
