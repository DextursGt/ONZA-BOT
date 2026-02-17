#!/bin/bash
# Start ONZA-BOT Dashboard

cd "$(dirname "$0")"

echo "Starting ONZA-BOT Dashboard..."

# Activate virtual environment if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start dashboard with uvicorn
python3 -m uvicorn dashboard.app:app --host 0.0.0.0 --port 8000 --reload
