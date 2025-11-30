#!/bin/bash

# Startup script to initialize DB, run bot, start API, and launch React dashboard

echo "=== FPL Bot System Startup ==="

# Initialize database
echo "1. Initializing database..."
python init_db.py
if [ $? -ne 0 ]; then
    echo "Error: Database initialization failed"
    exit 1
fi

# Start the FastAPI dashboard in the background
echo "2. Starting FastAPI dashboard..."
python -m uvicorn dashboard.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# Give the API a moment to start
sleep 5

# Start the React dashboard in the background
echo "3. Starting React dashboard..."
cd dashboard/react
npm install
npm start &
REACT_PID=$!

# Run the bot
echo "4. Running FPL bot..."
cd ../..
python bot.py

# Wait for background processes
wait $API_PID
wait $REACT_PID

echo "=== FPL Bot System Shutdown ==="