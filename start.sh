#!/bin/bash

# Minutemen Compass - Startup Script
# Starts both backend and frontend servers

echo "🚀 Starting Minutemen Compass..."

# Check if .env exists
if [ ! -f "backend/.env" ]; then
    echo "⚠️  Warning: backend/.env not found!"
    echo "Please create backend/.env with your OPENAI_API_KEY"
    echo "See backend/ENV_SETUP.md for instructions"
    exit 1
fi

# Start backend in background
echo "📡 Starting backend server..."
cd backend
python -m uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Start frontend
echo "🎨 Starting frontend server..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Servers started!"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all servers"

# Wait for user interrupt
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait

