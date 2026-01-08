#!/bin/bash
# Quick start script for Django Courier Module

cd "$(dirname "$0")/.."
echo "🚀 Starting Django Courier Module..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Creating one..."
    python -m venv venv
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate || source venv/Scripts/activate

# Install dependencies if needed
if ! python -c "import django" 2>/dev/null; then
    echo "📥 Installing dependencies..."
    pip install -r requirements_django.txt
fi

# Check if migrations are needed
echo "🔍 Checking database migrations..."
python manage.py migrate --check 2>/dev/null
if [ $? -ne 0 ]; then
    echo "🔄 Running migrations..."
    python manage.py migrate
fi

# Start the server
echo ""
echo "✅ Starting Django development server on http://localhost:8001"
echo ""
echo "📍 Available endpoints:"
echo "   - Dashboard: http://localhost:8001/static/dashboard.html"
echo "   - API Docs:  http://localhost:8001/docs/"
echo "   - Admin:     http://localhost:8001/django-admin/"
echo "   - Health:    http://localhost:8001/api/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python manage.py runserver 8001
