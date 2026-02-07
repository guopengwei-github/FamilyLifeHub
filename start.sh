#!/bin/bash

# FamilyLifeHub Quick Start Script

echo "========================================="
echo "FamilyLifeHub - Quick Start"
echo "========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Error: Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f backend/.env ]; then
    echo "Creating backend/.env file..."
    cp backend/.env.example backend/.env
    echo "Please update backend/.env with your API key!"
fi

# Create frontend .env.local if it doesn't exist
if [ ! -f frontend/.env.local ]; then
    echo "Creating frontend/.env.local file..."
    cp frontend/.env.local.example frontend/.env.local
fi

echo ""
echo "Starting services with Docker Compose..."
docker-compose up -d

echo ""
echo "========================================="
echo "Services started successfully!"
echo "========================================="
echo ""
echo "Frontend: http://localhost:3000"
echo "Backend API: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop: docker-compose down"
echo ""
