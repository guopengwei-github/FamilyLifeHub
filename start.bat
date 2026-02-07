@echo off
REM FamilyLifeHub Quick Start Script for Windows

echo =========================================
echo FamilyLifeHub - Quick Start
echo =========================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not installed. Please install Docker Desktop first.
    exit /b 1
)

docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo Error: Docker Compose is not installed. Please install Docker Desktop first.
    exit /b 1
)

REM Create .env file if it doesn't exist
if not exist backend\.env (
    echo Creating backend\.env file...
    copy backend\.env.example backend\.env
    echo Please update backend\.env with your API key!
)

REM Create frontend .env.local if it doesn't exist
if not exist frontend\.env.local (
    echo Creating frontend\.env.local file...
    copy frontend\.env.local.example frontend\.env.local
)

echo.
echo Starting services with Docker Compose...
docker-compose up -d

echo.
echo =========================================
echo Services started successfully!
echo =========================================
echo.
echo Frontend: http://localhost:3000
echo Backend API: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
echo To view logs: docker-compose logs -f
echo To stop: docker-compose down
echo.
pause
