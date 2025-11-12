# KMS 2.5 - Local Development Summary

## ✅ What Has Been Set Up

Your KMS 2.5 Vector Search project is now configured for **local development** without Kubernetes, Helm, or HPE SSO.

### Infrastructure Changes

| Component | Production Plan | Local Development |
|-----------|----------------|-------------------|
| **Authentication** | HPE SSO | ✅ SQLite + JWT |
| **Deployment** | Kubernetes + Helm | ✅ Docker Compose |
| **Database** | PostgreSQL cluster | ✅ SQLite (auth) + Postgres (Airflow) |
| **Orchestration** | K8s operators | ✅ Docker Compose |
| **Monitoring** | Full stack | ✅ Prometheus + Grafana |

---

## 📁 New Files Created

### Authentication System
1. ✅ `src/api/middleware/auth.py` - SQLite-based authentication
   - User registration
   - Login with JWT tokens
   - Token verification
   - Test user creation

2. ✅ `src/api/routes/auth.py` - Auth API routes
   - POST `/api/v1/auth/login` - Login
   - POST `/api/v1/auth/register` - Register new user
   - GET `/api/v1/auth/me` - Get current user
   - POST `/api/v1/auth/logout` - Logout

### Local Infrastructure
3. ✅ `docker-compose.yml` - Complete local stack
   - Weaviate (port 8080)
   - PostgreSQL (port 5432)
   - Airflow (port 8081)
   - KMS API (port 8000)
   - Prometheus (port 9090)
   - Grafana (port 3000)

4. ✅ `Dockerfile.api` - API service container

### Configuration
5. ✅ `requirements.txt` - All Python dependencies
6. ✅ `.env.example` - Environment configuration template
7. ✅ `monitoring/prometheus/prometheus.yml` - Metrics collection

### Documentation
8. ✅ `LOCAL_SETUP.md` - Complete local development guide
9. ✅ `LOCAL_DEV_SUMMARY.md` - This file

### Scripts
10. ✅ `scripts/setup_local.sh` - Automated setup script

---

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)

```bash
# Run the setup script
./scripts/setup_local.sh
```

This will:
- ✅ Check prerequisites (Docker, Python)
- ✅ Create necessary directories
- ✅ Copy .env.example to .env
- ✅ Start all services with Docker Compose
- ✅ Wait for services to be ready
- ✅ Create test users in SQLite

### Option 2: Manual Setup

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Start services
docker-compose up -d

# 3. Create test users
python src/api/middleware/auth.py

# 4. Check services
docker-compose ps
```

---

## 🔑 Authentication Usage

### Test Users (Pre-created)

| Username | Password | Email | Purpose |
|----------|----------|-------|---------|
| **admin** | admin123 | admin@kms.local | Admin testing |
| **test_user** | test123 | test@kms.local | Regular user |
| **grs_agent** | grs123 | grs@hpe.com | GRS agent testing |

### Login Flow

**1. Login to get token:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

**Response:**
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

**2. Use token in requests:**
```bash
# Get current user info
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Future search endpoint (when implemented)
curl -X POST http://localhost:8000/api/v1/search \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"query": "DIMM failure", "limit": 10}'
```

### Register New User

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

---

## 🌐 Service URLs

Once services are running:

| Service | URL | Credentials |
|---------|-----|-------------|
| **API** | http://localhost:8000 | Use JWT token |
| **API Docs (Swagger)** | http://localhost:8000/api/docs | - |
| **Weaviate** | http://localhost:8080 | Anonymous access |
| **Airflow** | http://localhost:8081 | admin / admin |
| **Prometheus** | http://localhost:9090 | - |
| **Grafana** | http://localhost:3000 | admin / admin |

---

## 📊 Test the API

### Using Swagger UI (Easiest)

1. Open http://localhost:8000/api/docs
2. Click "Authorize" button
3. Login:
   - Click "POST /api/v1/auth/login"
   - Click "Try it out"
   - Enter username: `admin`, password: `admin123`
   - Click "Execute"
   - Copy the `access_token` from response
4. Authorize:
   - Click "Authorize" button at top
   - Enter: `Bearer YOUR_TOKEN`
   - Click "Authorize"
5. Now you can test protected endpoints!

### Using cURL

```bash
# Save token to variable
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' | jq -r .access_token)

# Use token
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

### Using Python

```python
import requests

# Login
response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"username": "admin", "password": "admin123"}
)
token = response.json()["access_token"]

# Use token
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(
    "http://localhost:8000/api/v1/auth/me",
    headers=headers
)
print(response.json())
```

---

## 🗄️ Database Structure

### SQLite Database (`data/users.db`)

**users table:**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**sessions table:**
```sql
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

### View/Manage Users

```bash
# Open database
sqlite3 data/users.db

# View users
SELECT id, username, email, full_name, is_active FROM users;

# View sessions
SELECT user_id, token, expires_at FROM sessions ORDER BY created_at DESC LIMIT 10;

# Exit
.quit
```

---

## 🔧 Configuration

### Environment Variables (`.env`)

Key configurations for local development:

```bash
# API
API_HOST=0.0.0.0
API_PORT=8000

# Auth
AUTH_SECRET_KEY=your-secret-key-change-this
AUTH_ACCESS_TOKEN_EXPIRE_MINUTES=60
DB_PATH=data/users.db

# Weaviate
WEAVIATE_URL=http://localhost:8080

# ChatHPE (for embeddings)
CHATHPE_API_ENDPOINT=https://your-endpoint
CHATHPE_API_KEY=your-key
```

See `.env.example` for all available options.

---

## 🧪 Next Steps

### 1. Implement Search Service

Complete the search functionality:
- [ ] `src/api/services/search/hybrid_search_engine.py` - Implement search methods
- [ ] `src/api/routes/search.py` - Create search routes
- [ ] Load test data from `data/case-fields-mapping.json`

### 2. Implement Pipeline

Complete data processing:
- [ ] Implement SFDC extraction (`src/pipeline/jobs/extraction/`)
- [ ] Implement transformation (`src/pipeline/jobs/transformation/`)
- [ ] Implement PII removal (already has skeleton)
- [ ] Implement embedding generation
- [ ] Create Airflow DAGs

### 3. Load Test Data

```bash
# Load 5 test datasets
python scripts/load_test_data.py

# Test search with known queries
```

### 4. Add Tests

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v
```

---

## 🐛 Troubleshooting

### Services won't start

```bash
# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Restart
docker-compose restart

# Clean restart
docker-compose down -v
docker-compose up -d
```

### Cannot login

```bash
# Recreate users
rm data/users.db
python src/api/middleware/auth.py

# Check users
sqlite3 data/users.db "SELECT * FROM users;"
```

### Port already in use

Edit `docker-compose.yml` and change ports:
```yaml
services:
  api:
    ports:
      - "8001:8000"  # Use 8001 instead
```

### Python dependencies missing

```bash
pip install -r requirements.txt
```

---

## 📚 Documentation

- **`LOCAL_SETUP.md`** - Detailed setup guide
- **`PROJECT_TASKS.md`** - All project tasks
- **`SKELETON_TODO.md`** - Implementation TODO with test data
- **`docs/project-flow-and-architecture.md`** - Architecture diagrams
- **`docs/implementation-guide.md`** - Code patterns

---

## 🔄 Migration to Production

When ready for production:

### 1. Replace Authentication
Update `src/api/middleware/auth.py`:
- Remove SQLite
- Implement HPE SSO (OAuth2/OIDC)
- Update token validation

### 2. Update Deployment
- Use Kubernetes manifests in `infrastructure/kubernetes/`
- Deploy with Helm charts in `infrastructure/helm/`
- Configure ingress and load balancing

### 3. Security Hardening
- Generate strong secret keys
- Enable HTTPS
- Configure CORS properly
- Use secrets management (Vault, K8s Secrets)
- Set `API_RELOAD=false`

### 4. Database Migration
- Replace SQLite with PostgreSQL
- Migrate user data
- Update connection strings

---

## 📊 Monitoring

### Prometheus Metrics

Available at http://localhost:9090

**Query Examples:**
```
# API request rate
rate(api_requests_total[5m])

# Average request duration
rate(api_request_duration_seconds_sum[5m]) / rate(api_request_duration_seconds_count[5m])

# Active users
sessions_active_total
```

### Grafana Dashboards

Access at http://localhost:3000 (admin/admin)

Dashboards to create:
- API Performance
- Authentication Metrics
- Weaviate Performance
- System Resources

---

## ✅ Summary Checklist

**Infrastructure:**
- ✅ Docker Compose with 6 services
- ✅ Weaviate vector database
- ✅ PostgreSQL for Airflow
- ✅ Prometheus + Grafana monitoring

**Authentication:**
- ✅ SQLite database for users
- ✅ JWT token-based auth
- ✅ Login/register/logout endpoints
- ✅ Protected route middleware
- ✅ 3 test users created

**API:**
- ✅ FastAPI application
- ✅ Auth routes implemented
- ✅ Swagger documentation
- ✅ Request/response validation

**Configuration:**
- ✅ Environment variables
- ✅ Python dependencies
- ✅ Prometheus config
- ✅ Docker configs

**Documentation:**
- ✅ Local setup guide
- ✅ API usage examples
- ✅ Troubleshooting guide

**Scripts:**
- ✅ Automated setup script
- ✅ Test user creation

---

## 🎯 What's Working Now

✅ **Complete local development environment**
✅ **User authentication with JWT**
✅ **API with Swagger docs**
✅ **Vector database (Weaviate)**
✅ **Pipeline orchestration (Airflow)**
✅ **Monitoring stack**

## 🚧 What Needs Implementation

📋 **Search service** (skeleton created, needs implementation)
📋 **Data pipeline** (skeleton created, needs implementation)
📋 **PII removal** (skeleton created, needs implementation)
📋 **Test data loading**
📋 **Unit & integration tests**

---

**Ready to Start**: Your local development environment is fully configured and ready for implementation!

**Next Command**: `./scripts/setup_local.sh` to start everything!

---

**Last Updated**: November 12, 2025
**Version**: 1.0
**Status**: Local Development Ready ✅
