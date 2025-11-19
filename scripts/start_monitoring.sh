#!/bin/bash

# KMS 2.6 Monitoring Stack Startup Script
# Starts all monitoring services and validates health

set -e

echo "=========================================="
echo "KMS 2.6 Monitoring Stack Startup"
echo "=========================================="
echo

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "Please create .env file with required environment variables"
    echo "See .env.example for reference"
    exit 1
fi

# Source environment variables
export $(cat .env | grep -v '^#' | xargs)

# Create required directories
echo "📁 Creating required directories..."
mkdir -p logs dags/logs plugins data/raw/sfdc_exports
mkdir -p monitoring/prometheus monitoring/grafana/dashboards monitoring/alertmanager

# Start services
echo
echo "🚀 Starting monitoring stack..."
docker-compose up -d

# Wait for services to initialize
echo
echo "⏳ Waiting for services to initialize (60 seconds)..."
sleep 60

# Health checks
echo
echo "🏥 Performing health checks..."
echo

# Check Prometheus
echo -n "Checking Prometheus... "
if curl -s http://localhost:9091/-/healthy > /dev/null; then
    echo "✅ Healthy"
else
    echo "❌ Unhealthy"
fi

# Check Grafana
echo -n "Checking Grafana... "
if curl -s http://localhost:3000/api/health > /dev/null; then
    echo "✅ Healthy"
else
    echo "❌ Unhealthy"
fi

# Check KMS Metrics
echo -n "Checking KMS Metrics Server... "
if curl -s http://localhost:9090/health > /dev/null; then
    echo "✅ Healthy"
else
    echo "❌ Unhealthy"
fi

# Check Weaviate
echo -n "Checking Weaviate... "
if curl -s http://localhost:8080/v1/.well-known/ready > /dev/null; then
    echo "✅ Healthy"
else
    echo "❌ Unhealthy"
fi

# Check Airflow Webserver
echo -n "Checking Airflow... "
if curl -s http://localhost:8080/health > /dev/null; then
    echo "✅ Healthy"
else
    echo "❌ Unhealthy"
fi

# Check Alertmanager
echo -n "Checking Alertmanager... "
if curl -s http://localhost:9093/-/healthy > /dev/null; then
    echo "✅ Healthy"
else
    echo "❌ Unhealthy"
fi

# Display service URLs
echo
echo "=========================================="
echo "Services are ready!"
echo "=========================================="
echo
echo "📊 Grafana:        http://localhost:3000"
echo "   Credentials:    admin / admin"
echo
echo "📈 Prometheus:     http://localhost:9091"
echo "🔔 Alertmanager:   http://localhost:9093"
echo "📊 KMS Metrics:    http://localhost:9090/metrics"
echo "✈️  Airflow:        http://localhost:8080"
echo "   Credentials:    airflow / airflow"
echo "🔍 Weaviate:       http://localhost:8080"
echo
echo "=========================================="
echo "Next Steps:"
echo "=========================================="
echo
echo "1. Open Grafana: http://localhost:3000"
echo "2. Navigate to 'KMS 2.6 Pipeline Monitoring' dashboard"
echo "3. Run the pipeline:"
echo "   docker-compose exec airflow-scheduler airflow dags trigger kms_2_6_daily_pipeline"
echo "4. Watch metrics in real-time on Grafana dashboard"
echo
echo "For more information, see:"
echo "  - docs/MONITORING_SETUP.md"
echo "  - docs/TECHNICAL_IMPLEMENTATION.md"
echo
