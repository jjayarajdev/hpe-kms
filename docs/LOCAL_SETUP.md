# KMS 2.5 Local Development Setup

Complete guide for running KMS Vector Search locally without Kubernetes, Helm, or HPE SSO.

## Prerequisites

- **Docker Desktop** (or Docker Engine + Docker Compose)
- **Python 3.10+**
- **8GB+ RAM** (for running all services)
- **Git**

## Quick Start (5 minutes)

### 1. Clone and Setup

```bash
# Clone repository
cd /Users/jjayaraj/workspaces/HPE/KMS

# Copy environment file
cp .env.example .env

# Update .env with your settings (optional for quick start)
```

### 2. Start All Services with Docker Compose

```bash
# Start all services (Weaviate, Airflow, API, Prometheus, Grafana)
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

**Services will be available at**:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs
- **Weaviate**: http://localhost:8080
- **Airflow**: http://localhost:8081 (username: admin, password: admin)
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (username: admin, password: admin)

### 3. Initialize Test Users

```bash
# Create test users in SQLite database
python src/api/middleware/auth.py
```

**Default Test Users**:
| Username | Password | Email | Role |
|----------|----------|-------|------|
| admin | admin123 | admin@kms.local | Admin |
| test_user | test123 | test@kms.local | User |
| grs_agent | grs123 | grs@hpe.com | GRS Agent |

### 4. Test API

```bash
# Login to get token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Use token in subsequent requests
TOKEN="your-token-from-login"

# Test authenticated endpoint
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

---

## Manual Setup (Without Docker)

### 1. Install Python Dependencies

```bash
# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm
```

### 2. Start Weaviate Locally

```bash
# Option A: Docker
docker run -d \
  -p 8080:8080 \
  -e QUERY_DEFAULTS_LIMIT=25 \
  -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
  -e PERSISTENCE_DATA_PATH='/var/lib/weaviate' \
  -e DEFAULT_VECTORIZER_MODULE='none' \
  -e CLUSTER_HOSTNAME='node1' \
  semitechnologies/weaviate:1.23.0

# Option B: Download binary
# https://weaviate.io/developers/weaviate/installation/docker-compose
```

### 3. Initialize SQLite Database

```bash
# Create users database and test users
python src/api/middleware/auth.py
```

### 4. Start API Server

```bash
# Development mode with auto-reload
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

# Production mode
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 5. Start Airflow (Optional)

```bash
# Initialize Airflow database
airflow db init

# Create admin user
airflow users create \
  --username admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com \
  --password admin

# Start webserver (in one terminal)
airflow webserver --port 8081

# Start scheduler (in another terminal)
airflow scheduler
```

---

## Authentication Guide

### SQLite-Based Authentication

For local development, we use SQLite instead of HPE SSO.

#### Login Flow

1. **Register User** (optional, test users already created):
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "newuser@example.com",
    "password": "password123",
    "full_name": "New User"
  }'
```

2. **Login**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@kms.local",
    "full_name": "Admin User"
  }
}
```

3. **Use Token in Requests**:
```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Protected endpoint
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"

# Search endpoint (when implemented)
curl -X POST http://localhost:8000/api/v1/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "DIMM memory failure",
    "limit": 10
  }'
```

#### Token Management

- **Token Expiry**: 60 minutes (configurable in `.env`)
- **Token Storage**: Stored in SQLite `sessions` table
- **Token Format**: JWT with user information

#### Database Location

- **Users Database**: `data/users.db`
- **Schema**: `users` table + `sessions` table

---

## Testing with Sample Data

### Load Test Data

```bash
# Load 5 test datasets from case-fields-mapping.json
python scripts/load_test_data.sh
```

Test datasets:
1. **DIMM Failure** - Hardware memory issue (Case: 5000123456)
2. **Tape Drive Failure** - Storage array issue (Case: 5000234567)
3. **HDD Failure** - Hard drive predictive failure (Case: 5000345678)
4. **3PAR False Alarm** - Storage monitoring false positive (Case: 5000456789)
5. **Order Processing** - Order logistics query (Case: 5000567890)

### Test Search

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' | jq -r .access_token)

# Search for DIMM failures
curl -X POST http://localhost:8000/api/v1/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "DL380 Gen10 memory health degraded DIMM failure",
    "search_type": "hybrid",
    "limit": 5
  }' | jq

# Expected: test_dataset_1 (DIMM Failure) as top result
```

---

## Development Workflow

### 1. Code Changes

```bash
# API changes auto-reload (if using --reload flag)
# Edit files in src/api/

# Pipeline changes require restart
# Edit files in src/pipeline/
docker-compose restart airflow
```

### 2. Run Tests

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests (requires running services)
pytest tests/integration/ -v

# E2E tests
pytest tests/e2e/ -v

# With coverage
pytest --cov=src tests/ --cov-report=html
```

### 3. Code Quality

```bash
# Format code
black src/ tests/

# Lint
flake8 src/ tests/

# Type checking
mypy src/
```

---

## Monitoring

### Prometheus Metrics

Access: http://localhost:9090

**Key Metrics**:
- `api_requests_total` - Total API requests
- `api_request_duration_seconds` - Request latency
- `search_queries_total` - Search query count
- `weaviate_objects_total` - Total objects in Weaviate
- `pii_detections_total` - PII detections

### Grafana Dashboards

Access: http://localhost:3000 (admin/admin)

**Pre-configured Dashboards**:
1. **Pipeline Health** - DAG runs, success rates, processing times
2. **Search Performance** - Query latency, throughput, precision metrics
3. **PII Compliance** - Detection rates, false positives
4. **Resource Utilization** - CPU, memory, disk usage

---

## Troubleshooting

### Services Won't Start

```bash
# Check Docker status
docker ps

# Check logs
docker-compose logs weaviate
docker-compose logs api
docker-compose logs airflow

# Restart services
docker-compose restart

# Clean restart
docker-compose down -v
docker-compose up -d
```

### Weaviate Connection Issues

```bash
# Check Weaviate health
curl http://localhost:8080/v1/.well-known/ready

# Check Weaviate schema
curl http://localhost:8080/v1/schema
```

### Authentication Issues

```bash
# Recreate users database
rm data/users.db
python src/api/middleware/auth.py

# Check database
sqlite3 data/users.db "SELECT * FROM users;"
```

### API Won't Start

```bash
# Check logs
docker-compose logs api

# Check Python dependencies
pip install -r requirements.txt

# Test API manually
python -m src.api.main
```

### Port Conflicts

If ports are already in use, edit `docker-compose.yml`:

```yaml
services:
  api:
    ports:
      - "8001:8000"  # Change to 8001

  weaviate:
    ports:
      - "8081:8080"  # Change to 8081
```

---

## Production Considerations

### Switch to Production Authentication

When deploying to production, replace SQLite authentication with:

1. **HPE SSO Integration**
   - Update `src/api/middleware/auth.py`
   - Implement OAuth2/OIDC flow
   - Configure SSO provider settings

2. **Database**
   - Replace SQLite with PostgreSQL
   - Update connection string in `.env`

3. **Security**
   - Use strong secret keys (generate with `openssl rand -hex 32`)
   - Enable HTTPS
   - Configure CORS properly
   - Set `API_RELOAD=false`

### Environment Variables

Update `.env` for production:

```bash
ENVIRONMENT=production
LOG_LEVEL=WARNING
API_RELOAD=false
API_WORKERS=8  # Based on CPU cores

# Strong secrets
AUTH_SECRET_KEY=<generate-with-openssl-rand-hex-32>
AIRFLOW__CORE__FERNET_KEY=<generate-with-python>

# Production URLs
WEAVIATE_URL=https://weaviate.prod.internal
CHATHPE_API_ENDPOINT=https://chathpe.prod.internal/v1/embeddings
```

---

## Performance Tuning

### API Performance

```bash
# Increase workers
API_WORKERS=8  # Set to 2x CPU cores

# Tune timeouts
API_TIMEOUT=60
WEAVIATE_TIMEOUT=30
```

### Weaviate Performance

```yaml
# docker-compose.yml
services:
  weaviate:
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      QUERY_MAXIMUM_RESULTS: 10000
    deploy:
      resources:
        limits:
          memory: 32G  # Increase for large datasets
```

### Pipeline Performance

```bash
# .env
PIPELINE_BATCH_SIZE=5000  # Increase for better throughput
SPARK_MEMORY=8g
SPARK_CORES=4
```

---

## Next Steps

1. **Load Real Data**: See `SKELETON_TODO.md` for pipeline implementation
2. **Implement Search**: Complete search service in `src/api/services/search/`
3. **Add Tests**: Create tests for all components
4. **Configure Monitoring**: Set up Grafana dashboards
5. **Deploy Pipeline**: Implement Airflow DAGs for data processing

---

## Getting Help

- **Documentation**: `/docs/README.md`
- **API Docs**: http://localhost:8000/api/docs (when running)
- **Project Tasks**: `PROJECT_TASKS.md`
- **Implementation TODO**: `SKELETON_TODO.md`

---

**Last Updated**: November 12, 2025
**Version**: 1.0
**Status**: Local Development Guide
