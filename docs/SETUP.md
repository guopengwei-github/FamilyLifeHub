# FamilyLifeHub Setup Guide

## Complete Project Structure

```
family_life_hub/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── dashboard.py      # Dashboard endpoints
│   │   │       ├── ingest.py         # Data ingestion endpoints
│   │   │       └── users.py          # User management endpoints
│   │   ├── core/
│   │   │   ├── config.py             # Configuration management
│   │   │   ├── database.py           # Database connection
│   │   │   └── security.py           # API key authentication
│   │   ├── models/
│   │   │   └── __init__.py           # SQLAlchemy models
│   │   ├── schemas/
│   │   │   └── __init__.py           # Pydantic schemas
│   │   └── services/
│   │       └── dashboard.py          # Business logic
│   ├── .env.example                  # Environment template
│   ├── Dockerfile                    # Backend container
│   ├── main.py                       # Application entry point
│   └── requirements.txt              # Python dependencies
├── frontend/
│   ├── app/
│   │   ├── globals.css               # Global styles
│   │   ├── layout.tsx                # Root layout
│   │   └── page.tsx                  # Main dashboard page
│   ├── components/
│   │   ├── ui/
│   │   │   └── card.tsx              # Card component
│   │   ├── overview-panel.tsx        # Overview metrics panel
│   │   └── trend-chart.tsx           # Trend visualization
│   ├── lib/
│   │   ├── api.ts                    # API client
│   │   └── utils.ts                  # Utility functions
│   ├── types/
│   │   └── api.ts                    # TypeScript definitions
│   ├── .env.local.example            # Frontend environment template
│   ├── Dockerfile                    # Frontend container
│   ├── next.config.js                # Next.js configuration
│   ├── package.json                  # Node dependencies
│   ├── postcss.config.js             # PostCSS configuration
│   ├── tailwind.config.js            # Tailwind configuration
│   └── tsconfig.json                 # TypeScript configuration
├── docs/                             # Documentation (future)
├── .gitignore                        # Git ignore rules
├── docker-compose.yml                # Docker orchestration
├── README.md                         # Project documentation
├── start.sh                          # Linux/Mac start script
└── start.bat                         # Windows start script
```

## Step-by-Step Setup

### Option 1: Docker Compose (Recommended)

1. **Prerequisites**
   - Install Docker Desktop (includes Docker Compose)
   - Windows: https://docs.docker.com/desktop/install/windows-install/
   - Mac: https://docs.docker.com/desktop/install/mac-install/
   - Linux: https://docs.docker.com/desktop/install/linux-install/

2. **Clone and Configure**
   ```bash
   cd family_life_hub

   # Create backend environment file
   cp backend/.env.example backend/.env

   # Edit backend/.env and set a secure API key
   # API_KEY=your-secure-random-key-here
   ```

3. **Start Services**

   **Windows:**
   ```cmd
   start.bat
   ```

   **Linux/Mac:**
   ```bash
   chmod +x start.sh
   ./start.sh
   ```

   **Or manually:**
   ```bash
   docker-compose up -d
   ```

4. **Verify Services**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

5. **View Logs**
   ```bash
   docker-compose logs -f
   ```

6. **Stop Services**
   ```bash
   docker-compose down
   ```

### Option 2: Local Development

#### Backend Setup

1. **Install Python 3.11+**
   - Download from https://www.python.org/downloads/

2. **Setup Virtual Environment**
   ```bash
   cd backend
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Run Backend**
   ```bash
   python main.py
   ```

   Backend will be available at http://localhost:8000

#### Frontend Setup

1. **Install Node.js 20+**
   - Download from https://nodejs.org/

2. **Install Dependencies**
   ```bash
   cd frontend
   npm install
   ```

3. **Configure Environment**
   ```bash
   cp .env.local.example .env.local
   # Edit .env.local if needed
   ```

4. **Run Frontend**
   ```bash
   npm run dev
   ```

   Frontend will be available at http://localhost:3000

## Initial Data Setup

### 1. Create Users

Use the API documentation at http://localhost:8000/docs or curl:

```bash
# Create first user
curl -X POST http://localhost:8000/api/v1/users \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alice",
    "avatar": null
  }'

# Create second user
curl -X POST http://localhost:8000/api/v1/users \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Bob",
    "avatar": null
  }'
```

### 2. Add Sample Health Data

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

### 3. Add Sample Work Data

```bash
curl -X POST http://localhost:8000/api/v1/ingest/work \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "timestamp": "2024-01-31T10:00:00Z",
    "screen_time_minutes": 60,
    "focus_score": 85,
    "active_window_category": "coding"
  }'
```

## Database Schema

### Users Table
- `id`: Primary key
- `name`: User name (unique)
- `avatar`: Avatar URL/path (optional)
- `created_at`: Creation timestamp (UTC)

### HealthMetrics Table
- `id`: Primary key
- `user_id`: Foreign key to users
- `date`: Date of metric (UTC)
- `sleep_hours`: Sleep duration (0-24)
- `resting_heart_rate`: RHR in BPM
- `stress_level`: Stress score (0-100)
- `exercise_minutes`: Exercise duration
- `created_at`, `updated_at`: Timestamps (UTC)

### WorkMetrics Table
- `id`: Primary key
- `user_id`: Foreign key to users
- `timestamp`: Metric timestamp (UTC)
- `screen_time_minutes`: Active screen time
- `focus_score`: Focus score (0-100)
- `active_window_category`: Activity category
- `created_at`: Creation timestamp (UTC)

## API Endpoints

### Authentication
All write endpoints require `X-API-Key` header.

### Users
- `POST /api/v1/users` - Create user (auth required)
- `GET /api/v1/users` - List all users
- `GET /api/v1/users/{id}` - Get user by ID

### Data Ingestion
- `POST /api/v1/ingest/health` - Submit health metrics (auth required)
- `POST /api/v1/ingest/work` - Submit work metrics (auth required)

### Dashboard
- `GET /api/v1/dashboard/overview?target_date=YYYY-MM-DD` - Get overview
- `GET /api/v1/dashboard/trends?days=30&end_date=YYYY-MM-DD` - Get trends

## Troubleshooting

### Docker Issues

**Port already in use:**
```bash
# Change ports in docker-compose.yml
ports:
  - "8001:8000"  # Backend
  - "3001:3000"  # Frontend
```

**Container won't start:**
```bash
# Check logs
docker-compose logs backend
docker-compose logs frontend

# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Database Issues

**Reset database:**
```bash
# Stop services
docker-compose down

# Remove database file
rm backend/family_life_hub.db

# Restart services (database will be recreated)
docker-compose up -d
```

### Frontend Issues

**API connection error:**
- Verify backend is running: http://localhost:8000/health
- Check NEXT_PUBLIC_API_URL in frontend/.env.local
- Check CORS settings in backend/.env

## Next Steps

1. **Integrate with Garmin**: Set up Garmin Connect API integration
2. **Build Desktop Client**: Develop C++ client for work metrics
3. **Add Notifications**: Implement alerts for unhealthy patterns
4. **Mobile App**: Create mobile app for quick data entry
5. **Advanced Analytics**: Add ML-based insights and predictions

## Security Notes

- Change the default API key in production
- Use HTTPS in production environments
- Keep the database file secure (contains personal health data)
- Consider adding user authentication for multi-family deployments
- Regularly backup the SQLite database file

## Support

For issues or questions:
- Check the API documentation: http://localhost:8000/docs
- Review logs: `docker-compose logs -f`
- Open an issue on GitHub
