# FamilyLifeHub

A private, self-hosted family life data hub for tracking and analyzing health and work metrics. Designed to help identify unhealthy patterns in daily routines through data quantification.

## Features

- **Health Metrics Tracking**: Sleep hours, resting heart rate, stress levels (HRV), and exercise minutes
- **Work Metrics Tracking**: Screen time, focus scores, and activity categorization
- **Visual Analytics**: Interactive dashboard with trend charts showing correlations between work and sleep
- **Privacy-First**: Fully self-hosted with no external data sharing
- **API-First Design**: RESTful API with token authentication for future integrations

## Tech Stack

### Backend
- **FastAPI**: Modern Python web framework
- **SQLAlchemy**: ORM for database operations
- **SQLite**: Lightweight database for data storage
- **Pydantic**: Data validation and serialization

### Frontend
- **Next.js 14**: React framework with App Router
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Utility-first styling
- **Recharts**: Data visualization
- **Shadcn/ui**: Component library

### Deployment
- **Docker Compose**: Containerized deployment

## Project Structure

```
family_life_hub/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API endpoints
│   │   ├── core/            # Configuration and security
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   └── services/        # Business logic
│   ├── main.py              # Application entry point
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile
├── frontend/
│   ├── app/                 # Next.js pages
│   ├── components/          # React components
│   ├── lib/                 # Utilities and API client
│   ├── types/               # TypeScript definitions
│   └── Dockerfile
└── docker-compose.yml       # Docker orchestration
```

## Getting Started

### Prerequisites
- Docker and Docker Compose
- (Optional) Python 3.11+ and Node.js 20+ for local development

### Quick Start with Docker

1. Clone the repository:
```bash
git clone <repository-url>
cd family_life_hub
```

2. Create environment file:
```bash
cp backend/.env.example backend/.env
```

3. Update the API key in `backend/.env`:
```
API_KEY=your-secure-api-key-here
```

4. Start the services:
```bash
docker-compose up -d
```

5. Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Local Development

#### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your settings
python main.py
```

#### Frontend Setup

```bash
cd frontend
npm install
cp .env.local.example .env.local
# Edit .env.local with your settings
npm run dev
```

## API Usage

### Authentication

All write endpoints require an API key in the `X-API-Key` header:

```bash
curl -X POST http://localhost:8000/api/v1/ingest/health \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "date": "2024-01-31",
    "sleep_hours": 7.5,
    "exercise_minutes": 30
  }'
```

### Key Endpoints

- `POST /api/v1/users` - Create a new user
- `GET /api/v1/users` - List all users
- `POST /api/v1/ingest/health` - Submit health metrics
- `POST /api/v1/ingest/work` - Submit work metrics (for desktop client)
- `GET /api/v1/dashboard/overview` - Get today's overview
- `GET /api/v1/dashboard/trends?days=30` - Get trend data

## Initial Setup

1. Create family members:
```bash
curl -X POST http://localhost:8000/api/v1/users \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "avatar": null}'
```

2. Submit health data (manually or via Garmin integration):
```bash
curl -X POST http://localhost:8000/api/v1/ingest/health \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "date": "2024-01-31",
    "sleep_hours": 7.5,
    "resting_heart_rate": 65,
    "stress_level": 45,
    "exercise_minutes": 30
  }'
```

## Future Enhancements

- [ ] Desktop client (C++) for automatic work metrics collection
- [ ] Garmin Connect integration
- [ ] Mobile app for quick data entry
- [ ] Advanced analytics and insights
- [ ] Notification system for unhealthy patterns
- [ ] Data export functionality

## License

This project is open source and available under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
