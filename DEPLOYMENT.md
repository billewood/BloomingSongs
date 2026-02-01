# Deployment Strategy

## Production Setup (Planned)

**Frontend**: Vercel (bloomingsongs.com or similar)  
**Backend**: Render (bloomingsongs-api.onrender.com)  
**Data**: SQLite (bundled) or PostgreSQL (Render)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         User                                 │
│                          │                                   │
│                          ▼                                   │
│              bloomingsongs.com (Vercel)                      │
│                    Next.js Frontend                          │
│                          │                                   │
│                          ▼                                   │
│              /api/birds/* (Next.js API Route)                │
│                          │                                   │
│                          ▼                                   │
│     bloomingsongs-api.onrender.com (Render)                  │
│                 Python FastAPI Backend                       │
│              /api/birds/* endpoints                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Environment Variables

### Vercel (Frontend)
```bash
BACKEND_URL=https://bloomingsongs-api.onrender.com
```

### Render (Backend)
```bash
EBIRD_API_KEY=your_ebird_api_key
PORT=10000
```

---

## Deployment Workflow

### Making Changes

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature
   ```

2. **Make changes, commit, and push**:
   ```bash
   git add .
   git commit -m "Description of changes"
   git push -u origin feature/your-feature
   ```

3. **Create a Pull Request** on GitHub:
   - Go to your repository
   - Click "Compare & pull request"
   - Set base to `main`
   - Vercel automatically creates a preview deployment

4. **Test the preview** (Vercel comments with preview URL on the PR)

5. **Merge to main** when ready:
   - Click "Merge pull request" on GitHub
   - Vercel automatically redeploys the frontend
   - Render automatically redeploys the backend (if backend files changed)

---

## Initial Setup

### 1. GitHub Repository

Create a new repository and push the code:
```bash
cd /Users/williamwood/Code/BloomingSongs
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/bloomingsongs.git
git push -u origin main
```

### 2. Render (Backend)

1. Go to https://dashboard.render.com
2. Click "New" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name**: bloomingsongs-api
   - **Region**: Oregon (US West)
   - **Branch**: main
   - **Root Directory**: backend
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables:
   - `EBIRD_API_KEY`: Your eBird API key
6. Click "Create Web Service"

### 3. Vercel (Frontend)

1. Go to https://vercel.com/new
2. Import your GitHub repository
3. Configure:
   - **Framework Preset**: Next.js
   - **Root Directory**: frontend
4. Add environment variables:
   - `BACKEND_URL`: https://bloomingsongs-api.onrender.com
5. Click "Deploy"

### 4. Custom Domain (Optional)

**Vercel**:
1. Go to Project Settings → Domains
2. Add your domain (e.g., bloomingsongs.com)
3. Follow DNS configuration instructions

**Porkbun (or other registrar)**:
1. Add DNS records as instructed by Vercel
2. Usually an A record and CNAME record

---

## Service Details

### Vercel (Frontend)
- **Dashboard**: https://vercel.com/dashboard
- **Auto-deploys**: On push to `main` branch
- **Preview deploys**: On pull requests
- **Framework**: Next.js 14

### Render (Backend)
- **Dashboard**: https://dashboard.render.com
- **Health check**: /api/health
- **Auto-deploys**: On push to `main` branch (backend directory)
- **Framework**: FastAPI + Uvicorn

---

## Local Development

### Start Backend
```bash
cd backend
source ../venv/bin/activate  # or create venv first
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Start Frontend
```bash
cd frontend
npm install
npm run dev
```

The frontend runs on http://localhost:3000 and proxies API calls to http://localhost:8000.

---

## Data Management

### Daily Data Fetch

The eBird data needs to be refreshed daily. Options:

1. **Render Cron Job** (Paid plan):
   - Set up a cron job to run `python scripts/fetch_singing_data.py`

2. **GitHub Actions** (Free):
   - Create a workflow that runs daily and calls the backend

3. **External Scheduler**:
   - Use a service like cron-job.org to hit an endpoint

### Database

**Development**: SQLite (file-based, bundled with the app)
**Production Options**:
- SQLite (simple, but data resets on redeploy)
- PostgreSQL (Render offers free tier, persistent)

To migrate to PostgreSQL, update `DATABASE_URL` environment variable.

---

## Monitoring

### Health Checks
- Frontend: `https://your-domain.com/api/health`
- Backend: `https://bloomingsongs-api.onrender.com/api/health`

### Logs
- **Vercel**: Project → Deployments → Functions tab
- **Render**: Dashboard → Service → Logs tab

---

## Troubleshooting

### Backend Not Responding
1. Check Render dashboard for deployment status
2. Check logs for errors
3. Verify environment variables are set
4. Check if the service is sleeping (free tier sleeps after inactivity)

### Frontend API Errors
1. Check browser console for errors
2. Verify BACKEND_URL is set correctly in Vercel
3. Test backend directly: `curl https://bloomingsongs-api.onrender.com/api/health`

### CORS Issues
The backend is configured to allow all origins. If you have issues:
1. Check the CORS configuration in `backend/app/main.py`
2. Add your specific domain to `allow_origins`
