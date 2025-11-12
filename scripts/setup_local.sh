#!/bin/bash

# KMS 2.5 Local Setup Script
# Quick setup for local development

set -e

echo "=========================================="
echo "KMS 2.5 Vector Search - Local Setup"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not found. Please install Docker Desktop.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker found${NC}"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗ Docker Compose not found. Please install Docker Compose.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose found${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found. Please install Python 3.10+.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 found${NC}"

echo ""
echo -e "${BLUE}Step 1: Creating directories...${NC}"
mkdir -p data/raw data/processed data/embeddings data/test_datasets logs

echo -e "${GREEN}✓ Directories created${NC}"

echo ""
echo -e "${BLUE}Step 2: Setting up environment...${NC}"

if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env file${NC}"
    echo -e "${BLUE}  → Please update .env with your configuration${NC}"
else
    echo -e "${GREEN}✓ .env file already exists${NC}"
fi

echo ""
echo -e "${BLUE}Step 3: Starting services with Docker Compose...${NC}"
docker-compose up -d

echo -e "${GREEN}✓ Services started${NC}"

echo ""
echo -e "${BLUE}Step 4: Waiting for services to be ready...${NC}"

# Wait for Weaviate
echo -n "  Waiting for Weaviate..."
until curl -s http://localhost:8080/v1/.well-known/ready > /dev/null 2>&1; do
    echo -n "."
    sleep 2
done
echo -e " ${GREEN}Ready!${NC}"

# Wait for API
echo -n "  Waiting for API..."
until curl -s http://localhost:8000/ > /dev/null 2>&1; do
    echo -n "."
    sleep 2
done
echo -e " ${GREEN}Ready!${NC}"

echo ""
echo -e "${BLUE}Step 5: Creating test users...${NC}"

# Create Python virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "  Creating Python virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
source venv/bin/activate

# Install minimal dependencies for auth script
pip install -q pyjwt

# Create test users
python src/api/middleware/auth.py

echo ""
echo "=========================================="
echo -e "${GREEN}✓ Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Services are running:"
echo ""
echo "  • API:        http://localhost:8000"
echo "  • API Docs:   http://localhost:8000/api/docs"
echo "  • Weaviate:   http://localhost:8080"
echo "  • Airflow:    http://localhost:8081 (admin/admin)"
echo "  • Prometheus: http://localhost:9090"
echo "  • Grafana:    http://localhost:3000 (admin/admin)"
echo ""
echo "Test Users:"
echo ""
echo "  Username   | Password | Email"
echo "  -----------|----------|------------------"
echo "  admin      | admin123 | admin@kms.local"
echo "  test_user  | test123  | test@kms.local"
echo "  grs_agent  | grs123   | grs@hpe.com"
echo ""
echo "Quick Test:"
echo ""
echo "  # Login"
echo "  curl -X POST http://localhost:8000/api/v1/auth/login \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"username\": \"admin\", \"password\": \"admin123\"}'"
echo ""
echo "For detailed documentation, see LOCAL_SETUP.md"
echo ""
