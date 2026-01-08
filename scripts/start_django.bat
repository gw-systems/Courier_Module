@echo off
REM Quick start script for Django Courier Module (Windows)

pushd %~dp0\..
echo.
echo ========================================
echo   Django Courier Module - Quick Start
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies if needed
python -c "import django" 2>nul
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements_django.txt
)

REM Run migrations if needed
echo.
echo Checking database migrations...
python manage.py migrate --check 2>nul
if errorlevel 1 (
    echo Running migrations...
    python manage.py migrate
)

REM Start the server
echo.
echo ========================================
echo   Server Starting on http://localhost:8001
echo ========================================
echo.
echo Available endpoints:
echo   - Dashboard: http://localhost:8001/static/dashboard.html
echo   - API Docs:  http://localhost:8001/docs/
echo   - Admin:     http://localhost:8001/django-admin/
echo   - Health:    http://localhost:8001/api/health
echo.
echo Press Ctrl+C to stop the server
echo.

python manage.py runserver 8001
