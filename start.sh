#!/bin/bash
# YUNA-System Startup Script
# Runs both the API server and Telegram bot

echo "🚀 Starting YUNA-System..."

# Start API server in background
echo "📡 Starting API server on port 8000..."
uvicorn yuna.api.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# Wait a moment for API to start
sleep 2

# Check if API started successfully
if kill -0 $API_PID 2>/dev/null; then
    echo "✅ API server running (PID: $API_PID)"
else
    echo "❌ API server failed to start"
fi

# Start Telegram bot (foreground)
echo "🤖 Starting Telegram bot..."
python main.py

# If bot exits, also stop the API
echo "Stopping API server..."
kill $API_PID 2>/dev/null
