# API Service

REST API service for semantic search and vector queries.

## Structure

- **routes/**: API endpoint definitions
- **models/**: Data models and ORM definitions
- **services/**: Business logic layer
  - search/: Hybrid search implementation
  - vector/: Vector similarity operations
  - metadata/: Metadata filtering
  - recommendations/: Case recommendation engine
- **middleware/**: Authentication, logging, rate limiting
- **schemas/**: Request/response validation schemas

## Key Endpoints

- `POST /api/v1/search`: Hybrid semantic search
- `GET /api/v1/cases/{id}`: Retrieve case by ID
- `POST /api/v1/similar`: Find similar cases
- `GET /api/health`: Health check endpoint

## Technology

- Framework: FastAPI
- Database: Weaviate (vector store)
- Authentication: HPE SSO integration
