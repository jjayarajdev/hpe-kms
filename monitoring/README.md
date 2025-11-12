# Monitoring and Observability

Prometheus, Grafana, Loki, and Jaeger configurations for observability.

## Components

- **prometheus/**: Prometheus configuration and service discovery
- **grafana/**: Grafana dashboards and datasources
- **loki/**: Log aggregation configuration
- **jaeger/**: Distributed tracing configuration
- **dashboards/**: Pre-built Grafana dashboards
- **alerts/**: Prometheus alert rules

## Key Dashboards

1. **Pipeline Health**: DAG success rates, processing times, failure alerts
2. **Search Performance**: Query latency, throughput, precision metrics
3. **PII Compliance**: Detection rates, false positives, leakage monitoring
4. **Resource Utilization**: CPU, memory, storage, network metrics

## Alert Rules

- Pipeline failure rate > 5%
- Search latency p95 > 1 second
- PII leakage detected (zero tolerance)
- Embedding processing backlog > 10,000 cases
- Weaviate disk usage > 85%

## Access

- Grafana: https://grafana.kms.hpe.internal
- Prometheus: https://prometheus.kms.hpe.internal
- Jaeger: https://jaeger.kms.hpe.internal
