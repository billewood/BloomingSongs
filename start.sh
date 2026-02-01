#!/bin/bash
# Quick start script for BloomingSongs

echo "🐦 Starting BloomingSongs..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Check if dependencies are installed
if [ ! -f "venv/bin/uvicorn" ]; then
    echo "Installing Python dependencies..."
    pip install -r requirements.txt
fi

# Check if .env exists
if [ ! -f "backend/.env" ]; then
    echo ""
    echo "⚠️  WARNING: backend/.env file not found!"
    echo "Please create backend/.env with your EBIRD_API_KEY"
    echo "Get your key at: https://ebird.org/api/keygen"
    echo ""
    exit 1
fi

# Initialize database if it doesn't exist
if [ ! -f "data/bloomingsongs.db" ]; then
    echo "Initializing database..."
    cd backend
    python scripts/init_db.py
    cd ..
fi

# Start backend server
echo "Starting backend server on http://localhost:8000"
cd backend
uvicorn app.main:app --reload &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to start
sleep 2

# Start frontend (if Node.js is available)
if command -v npm &> /dev/null; then
    if [ ! -d "frontend/node_modules" ]; then
        echo "Installing frontend dependencies..."
        cd frontend
        npm install
        cd ..
    fi
    
    echo "Starting frontend on http://localhost:3000"
    cd frontend
    npm run dev &
    FRONTEND_PID=$!
    cd ..
    
    echo ""
    echo "✓ BloomingSongs is running!"
    echo "  Backend: http://localhost:8000"
    echo "  Frontend: http://localhost:3000"
    echo ""
    echo "Press Ctrl+C to stop both servers"
    
    # Wait for user interrupt
    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
    wait
else
    echo ""
    echo "✓ Backend is running on http://localhost:8000"
    echo "  (Frontend requires Node.js - install it to run the full app)"
    echo ""
    echo "Press Ctrl+C to stop the server"
    wait $BACKEND_PID
fi
