#!/bin/bash
# Railway Startup Script
# ======================
# Starts both nginx (frontend) and gunicorn (backend)

set -e

echo "🚀 Starting Sales Insights Agent..."

# Initialize the database (creates tables if not exist)
echo "📦 Initializing database..."
python -c "from database import init_db, seed_database; init_db(); seed_database()"

# Start nginx in the background
echo "🌐 Starting nginx..."
nginx

# Start gunicorn (Flask backend) on internal port
# nginx will proxy /api/* requests to this
echo "🐍 Starting Flask backend..."
exec gunicorn \
    --bind 127.0.0.1:5001 \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    app:app
