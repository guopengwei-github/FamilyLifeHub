# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FamilyLifeHub is a self-hosted family life data hub for tracking and analyzing health and work metrics. The system uses a FastAPI backend with SQLite and a Next.js 14 frontend with TypeScript and Tailwind CSS.

## Development Commands

### Docker (Recommended)
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild containers
docker-compose build --no-cache
```

### Backend (Local Development)
```bash
cd backend

# Setup virtual environment (first time)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run backend server
python main.py  # Runs on http://localhost:8000

# Access API documentation
# http://localhost:8000/docs (Swagger UI)
```

### Frontend (Local Development)
```bash
cd frontend

# Install dependencies (first time)
npm install

# Run development server
npm run dev  # Runs on http://localhost:3000

# Build for production
npm run build

# Run production build
npm start

# Lint code
npm run lint
```

## Architecture

### Backend Structure

The backend follows a layered architecture pattern:

- **`main.py`**: Application entry point, FastAPI app initialization, CORS configuration, and router registration
- **`app/core/`**: Core infrastructure
  - `config.py`: Environment configuration using Pydantic settings
  - `database.py`: SQLAlchemy engine, session management, and `get_db()` dependency
  - `security.py`: API key authentication via `X-API-Key` header
- **`app/models/`**: SQLAlchemy ORM models (User, HealthMetric, WorkMetric)
- **`app/schemas/`**: Pydantic schemas for request validation and response serialization
- **`app/api/v1/`**: API endpoint routers
  - `users.py`: User management (create, list, get by ID)
  - `ingest.py`: Data ingestion endpoints (health and work metrics)
  - `dashboard.py`: Dashboard data endpoints (overview, trends)
- **`app/services/`**: Business logic layer
  - `dashboard.py`: Data aggregation and calculations for dashboard

### Frontend Structure

The frontend uses Next.js 14 App Router:

- **`app/`**: Next.js pages and layouts
  - `page.tsx`: Main dashboard page
  - `layout.tsx`: Root layout with global styles
  - `globals.css`: Global CSS and Tailwind directives
- **`components/`**: React components
  - `overview-panel.tsx`: Today's metrics display
  - `trend-chart.tsx`: Recharts-based trend visualization
  - `ui/`: Shadcn/ui components (card, etc.)
- **`lib/`**: Utilities and API client
  - `api.ts`: API client with typed fetch wrappers
  - `utils.ts`: Utility functions (cn for className merging)
- **`types/`**: TypeScript type definitions
  - `api.ts`: API response types matching backend schemas

### Data Flow

1. **Data Ingestion**: External sources (Garmin, desktop client) → POST to `/api/v1/ingest/*` → SQLAlchemy models → SQLite
2. **Dashboard Display**: Frontend → GET `/api/v1/dashboard/*` → Service layer aggregates data → Pydantic schemas → Frontend components
3. **Authentication**: Write endpoints require `X-API-Key` header validated by `verify_api_key()` dependency

### Database Models

- **User**: Family members (id, name, avatar, created_at)
- **HealthMetric**: Daily health data per user (sleep_hours, resting_heart_rate, stress_level, exercise_minutes)
  - One record per user per day (upsert on duplicate date)
- **WorkMetric**: Work activity data per user (screen_time_minutes, focus_score, active_window_category)
  - Multiple records per user per day (heartbeat packets from desktop client)

All timestamps are stored in UTC.

## Current Development Environment

**IMPORTANT**: When working on this project, use the local development setup:

1. **Backend**: Runs in Python virtual environment at `D:\ai\family_life_hub\backend`
   - Activate: `venv\Scripts\activate`
   - Run: `python main.py`
   - URL: `http://localhost:8000`

2. **Frontend**: Runs in development mode at `D:\ai\family_life_hub\frontend`
   - Run: `npm run dev`
   - URL: `http://localhost:3000`

3. **Docker**: NOT used for active development unless explicitly requested
   - Docker is only used when deploying to production

## Configuration

### Backend Environment Variables
Located in `backend/.env`:
- `DATABASE_URL`: SQLite database path (default: `sqlite:///./family_life_hub.db`)
- `API_KEY`: Secret key for write endpoint authentication
- `ALLOWED_ORIGINS`: CORS allowed origins (comma-separated)
- `APP_NAME`: Application name
- `DEBUG`: Enable debug mode (True/False)

### Frontend Environment Variables
Located in `frontend/.env.local`:
- `NEXT_PUBLIC_API_URL`: Backend API URL (default: `http://localhost:8000`)

## Testing and Data Generation

Use `backend/generate_sample_data.py` to populate the database with sample data for testing:
```bash
cd backend
python generate_sample_data.py
```

## API Authentication

Write endpoints (`POST /api/v1/users`, `POST /api/v1/ingest/*`) require API key authentication:
```bash
curl -X POST http://localhost:8000/api/v1/ingest/health \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "date": "2024-01-31", "sleep_hours": 7.5}'
```

Read endpoints (`GET /api/v1/users`, `GET /api/v1/dashboard/*`) are public.

## Key Design Patterns

1. **Dependency Injection**: FastAPI's `Depends()` for database sessions and authentication
2. **Service Layer**: Business logic separated from API endpoints (see `app/services/`)
3. **Schema Validation**: Pydantic models for all request/response data
4. **Upsert Pattern**: Health metrics use upsert (update if exists, insert if not) based on user_id + date
5. **Aggregation**: Work metrics are aggregated daily in the service layer (sum screen time, average focus score)

## Common Tasks

### Adding a New API Endpoint
1. Define Pydantic schemas in `app/schemas/__init__.py`
2. Create endpoint in appropriate router (`app/api/v1/*.py`)
3. Add business logic to service layer if needed (`app/services/`)
4. Update frontend API client (`frontend/lib/api.ts`)
5. Add TypeScript types (`frontend/types/api.ts`)

### Adding a New Database Model
1. Define SQLAlchemy model in `app/models/__init__.py`
2. Create corresponding Pydantic schemas in `app/schemas/__init__.py`
3. Database tables are auto-created on startup via `Base.metadata.create_all()`
4. For production, consider using Alembic migrations

### Modifying the Dashboard
1. Update service layer calculations in `app/services/dashboard.py`
2. Update Pydantic response schemas in `app/schemas/__init__.py`
3. Update frontend types in `frontend/types/api.ts`
4. Update React components in `frontend/components/`

## Database Management

The SQLite database file is located at `backend/family_life_hub.db`.

To reset the database:
```bash
# Stop services
docker-compose down

# Remove database file
rm backend/family_life_hub.db

# Restart (database will be recreated)
docker-compose up -d
```

## Lessons Learned

### API Error Handling Pattern
**CRITICAL**: When writing frontend API functions that use `fetch()` directly (not the `fetchAPI` wrapper), you MUST:

1. Check `res.ok` or `res.status` before parsing JSON
2. Throw a proper error with status code for the caller to handle

**Bad pattern** (causes silent failures and page refresh loops):
```typescript
const res = await fetch(url, options);
const response = await res.json() as SomeType;  // Fails on 401/400!
return response;
```

**Correct pattern**:
```typescript
const res = await fetch(url, options);
if (!res.ok) {
  const error = await res.json().catch(() => ({ detail: 'Unknown error' }));
  const errorObj = new Error(error.detail || `HTTP ${res.status}`) as any;
  errorObj.status = res.status;
  throw errorObj;
}
const response = await res.json() as SomeType;
return response;
```

**Why this matters**: When login fails with 401, the error response is `{"detail": "Incorrect email or password"}`, not a Token. Without checking `res.ok`, the code tries to access `response.access_token` (undefined), stores garbage, then redirects to首页 where the invalid token causes another redirect back to login.

### Restarting Services
When asked to "restart" the project:
1. ALWAYS kill existing processes on ports 3000, 3001, 8000 first
2. Then start fresh backend and frontend
3. Use: `netstat -ano | grep -E ":3000|:3001|:8000" | awk '{print $5}' | sort -u | xargs -I {} cmd.exe /c "taskkill /F /PID {} 2>nul"`

## Future Enhancements

The codebase is designed to support:
- Desktop client (C++) for automatic work metrics collection
- Garmin Connect integration for health data
- Mobile app for quick data entry
- Advanced analytics and ML-based insights
