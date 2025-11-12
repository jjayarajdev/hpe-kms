# Section 6: Logging and Alerting Mechanisms (Prometheus & Observability)

## 6.1 Overview

**Objective**: Implement comprehensive observability stack for real-time monitoring, alerting, and troubleshooting of the vector search pipeline and infrastructure.

**Observability Stack**:
```
┌─────────────┐    ┌──────────────┐    ┌───────────┐
│ Prometheus  │───▶│  Grafana     │───▶│  Alerts   │
│  (Metrics)  │    │ (Dashboards) │    │(Alertmgr) │
└─────────────┘    └──────────────┘    └───────────┘
       │
┌──────▼──────┐    ┌──────────────┐    ┌───────────┐
│    Loki     │───▶│   Grafana    │    │  Jaeger   │
│    (Logs)   │    │  (Log Query) │    │ (Traces)  │
└─────────────┘    └──────────────┘    └───────────┘
```

---

## 6.2 Metrics Collection with Prometheus

### 6.2.1 Pipeline Metrics

**Airflow DAG Metrics**:
```python
from prometheus_client import Counter, Histogram, Gauge, Summary
import time

# Define metrics
pipeline_runs_total = Counter(
    'vector_pipeline_runs_total',
    'Total number of pipeline runs',
    ['status', 'dag_id']
)

pipeline_duration_seconds = Histogram(
    'vector_pipeline_duration_seconds',
    'Pipeline execution duration in seconds',
    ['dag_id', 'task_id'],
    buckets=[60, 300, 600, 1800, 3600, 7200, 14400]  # 1min to 4hrs
)

records_processed_total = Counter(
    'vector_pipeline_records_processed_total',
    'Total records processed',
    ['stage', 'status']
)

records_processing_rate = Gauge(
    'vector_pipeline_records_per_minute',
    'Current processing rate (records/min)',
    ['stage']
)

pii_detections_total = Counter(
    'vector_pipeline_pii_detections_total',
    'Total PII instances detected and removed',
    ['pii_type', 'field', 'table']  # NEW: Added table dimension
)

# NEW: Multi-table join metrics
multi_table_join_count = Counter(
    'multi_table_join_total',
    'Total multi-table joins performed',
    ['join_type']
)

multi_table_coverage = Gauge(
    'multi_table_coverage_ratio',
    'Percentage of cases with data from each table',
    ['table_name']
)

fields_populated_per_case = Histogram(
    'fields_populated_per_case',
    'Distribution of populated fields per case',
    buckets=[10, 20, 30, 35, 40, 44]
)

embedding_api_requests_total = Counter(
    'embedding_api_requests_total',
    'Total embedding API requests',
    ['provider', 'status']
)

embedding_api_latency_seconds = Histogram(
    'embedding_api_latency_seconds',
    'Embedding API request latency',
    ['provider'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

weaviate_load_duration_seconds = Histogram(
    'weaviate_load_duration_seconds',
    'Duration to load batch to Weaviate',
    ['batch_size'],
    buckets=[1, 5, 10, 30, 60, 120, 300]
)

# Instrumentation example
def process_case_batch(cases, stage='pii_removal'):
    """
    Process case batch with metrics instrumentation
    """
    start_time = time.time()

    try:
        # Process cases
        for case in cases:
            process_single_case(case)

            # Increment processed counter
            records_processed_total.labels(
                stage=stage,
                status='success'
            ).inc()

        # Record duration
        duration = time.time() - start_time
        pipeline_duration_seconds.labels(
            dag_id='case_vector_pipeline',
            task_id=stage
        ).observe(duration)

        # Update processing rate
        rate = len(cases) / (duration / 60)  # records per minute
        records_processing_rate.labels(stage=stage).set(rate)

        # Increment run counter
        pipeline_runs_total.labels(
            status='success',
            dag_id='case_vector_pipeline'
        ).inc()

    except Exception as e:
        # Increment failure counter
        pipeline_runs_total.labels(
            status='failure',
            dag_id='case_vector_pipeline'
        ).inc()

        records_processed_total.labels(
            stage=stage,
            status='failure'
        ).inc()

        raise e
```

**Search API Metrics**:
```python
from flask import Flask, request
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
metrics = PrometheusMetrics(app)

# Custom metrics
search_requests_total = Counter(
    'search_requests_total',
    'Total search requests',
    ['endpoint', 'status', 'product_family']
)

search_latency_seconds = Histogram(
    'search_latency_seconds',
    'Search request latency',
    ['endpoint', 'hybrid_alpha'],
    buckets=[0.1, 0.25, 0.5, 0.75, 1.0, 2.0, 5.0]
)

search_results_count = Histogram(
    'search_results_count',
    'Number of results returned',
    ['endpoint'],
    buckets=[0, 1, 5, 10, 20, 50, 100]
)

search_zero_results_total = Counter(
    'search_zero_results_total',
    'Total searches with zero results',
    ['query_length_bucket']
)

@app.route('/api/v1/search', methods=['POST'])
@metrics.counter('search_endpoint_requests', 'Search endpoint requests')
def search_endpoint():
    start_time = time.time()

    try:
        data = request.get_json()
        query = data.get('query', '')
        filters = data.get('filters', {})
        alpha = data.get('alpha', 0.75)

        # Execute search
        results = hybrid_search(query, filters, alpha=alpha)

        # Record metrics
        latency = time.time() - start_time
        search_latency_seconds.labels(
            endpoint='/api/v1/search',
            hybrid_alpha=str(alpha)
        ).observe(latency)

        search_results_count.labels(
            endpoint='/api/v1/search'
        ).observe(len(results))

        # Zero results tracking
        if len(results) == 0:
            query_length = 'short' if len(query) < 20 else ('medium' if len(query) < 50 else 'long')
            search_zero_results_total.labels(
                query_length_bucket=query_length
            ).inc()

        search_requests_total.labels(
            endpoint='/api/v1/search',
            status='success',
            product_family=filters.get('productFamily', 'all')
        ).inc()

        return jsonify({"results": results}), 200

    except Exception as e:
        search_requests_total.labels(
            endpoint='/api/v1/search',
            status='error',
            product_family='unknown'
        ).inc()

        return jsonify({"error": str(e)}), 500
```

**Weaviate Metrics**:
```python
# Weaviate-specific metrics
weaviate_objects_total = Gauge(
    'weaviate_objects_total',
    'Total objects in Weaviate',
    ['class_name', 'tenant']
)

weaviate_index_size_bytes = Gauge(
    'weaviate_index_size_bytes',
    'Weaviate index size in bytes',
    ['class_name']
)

weaviate_query_latency_seconds = Histogram(
    'weaviate_query_latency_seconds',
    'Weaviate query latency',
    ['operation'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0]
)

def collect_weaviate_metrics():
    """
    Periodically collect Weaviate metrics
    """
    client = get_weaviate_client()

    # Get object count
    result = client.query.aggregate('CaseVectorized').with_meta_count().do()
    count = result['data']['Aggregate']['CaseVectorized'][0]['meta']['count']

    weaviate_objects_total.labels(
        class_name='CaseVectorized',
        tenant='tenant_cognate'
    ).set(count)

    # Get index size (from Weaviate metrics endpoint)
    # ... implementation depends on Weaviate version

# Run collector in background
import threading
def metrics_collector_loop():
    while True:
        collect_weaviate_metrics()
        time.sleep(60)  # Every minute

collector_thread = threading.Thread(target=metrics_collector_loop, daemon=True)
collector_thread.start()
```

### 6.2.2 Prometheus Configuration

**prometheus.yml**:
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'pc-ai-production'
    environment: 'production'

# Alertmanager configuration
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093

# Rule files
rule_files:
  - '/etc/prometheus/rules/*.yml'

# Scrape configurations
scrape_configs:
  # Airflow pipeline metrics
  - job_name: 'airflow-pipeline'
    static_configs:
      - targets: ['airflow-webserver:8080']
    metrics_path: '/metrics'

  # Search API metrics
  - job_name: 'search-api'
    kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
            - vector-search
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        regex: search-api
        action: keep

  # Weaviate metrics
  - job_name: 'weaviate'
    static_configs:
      - targets: ['weaviate:2112']
    metrics_path: '/metrics'

  # Node exporter (infrastructure)
  - job_name: 'node-exporter'
    kubernetes_sd_configs:
      - role: node
    relabel_configs:
      - source_labels: [__address__]
        regex: '(.*):10250'
        replacement: '${1}:9100'
        target_label: __address__

  # Kubernetes metrics
  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
```

---

## 6.3 Structured Logging with Loki

### 6.3.1 Python Logging Configuration

```python
import logging
import json
import sys
from pythonjsonlogger import jsonlogger

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter with standard fields
    """
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)

        # Add standard fields
        log_record['timestamp'] = record.created
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno

        # Add trace context if available
        if hasattr(record, 'trace_id'):
            log_record['trace_id'] = record.trace_id
        if hasattr(record, 'span_id'):
            log_record['span_id'] = record.span_id

        # Add custom fields
        if hasattr(record, 'case_id'):
            log_record['case_id'] = record.case_id
        if hasattr(record, 'dag_id'):
            log_record['dag_id'] = record.dag_id
        if hasattr(record, 'task_id'):
            log_record['task_id'] = record.task_id

        # NEW: Multi-table context
        if hasattr(record, 'source_table'):
            log_record['source_table'] = record.source_table
        if hasattr(record, 'join_table'):
            log_record['join_table'] = record.join_table
        if hasattr(record, 'fields_populated'):
            log_record['fields_populated'] = record.fields_populated

def setup_logging(service_name='vector-pipeline'):
    """
    Configure structured JSON logging
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Remove existing handlers
    logger.handlers = []

    # Console handler with JSON format
    handler = logging.StreamHandler(sys.stdout)
    formatter = CustomJsonFormatter(
        '%(timestamp)s %(level)s %(logger)s %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger

# Usage
logger = setup_logging()

logger.info(
    "Processing case batch",
    extra={
        'case_id': '5007T000002AbcD',
        'batch_size': 100,
        'stage': 'pii_removal',
        'dag_id': 'case_vector_pipeline',
        'task_id': 'pii_removal_task'
    }
)
```

### 6.3.2 Log Aggregation with Promtail

**promtail-config.yml**:
```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  # Airflow logs
  - job_name: airflow
    static_configs:
      - targets:
          - localhost
        labels:
          job: airflow
          service: vector-pipeline
          __path__: /opt/airflow/logs/**/*.log

  # Search API logs (Kubernetes pods)
  - job_name: kubernetes-pods
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        target_label: app
      - source_labels: [__meta_kubernetes_pod_label_component]
        target_label: component
      - source_labels: [__meta_kubernetes_namespace]
        target_label: namespace
      - source_labels: [__meta_kubernetes_pod_name]
        target_label: pod
    pipeline_stages:
      # Parse JSON logs
      - json:
          expressions:
            timestamp: timestamp
            level: level
            message: message
            trace_id: trace_id
            case_id: case_id

      # Extract labels
      - labels:
          level:
          trace_id:

      # Add timestamp
      - timestamp:
          source: timestamp
          format: Unix
```

### 6.3.3 Log Query Examples (LogQL)

```logql
# All ERROR logs from pipeline
{service="vector-pipeline"} |= "level" |= "ERROR"

# PII removal logs for specific case
{service="vector-pipeline"} | json | case_id="5007T000002AbcD" | stage="pii_removal"

# High-latency search requests
{app="search-api"} | json | latency > 1.0

# Failed embedding API calls
{service="vector-pipeline"} | json | task_id="generate_embeddings" | status="failure"

# Rate of errors per minute
rate({service="vector-pipeline"} | json | level="ERROR" [1m])

# Top 10 most common errors
topk(10, sum by (error_type) (count_over_time({service="vector-pipeline"} | json | level="ERROR" [24h])))

# NEW: Multi-table join logs for specific case
{service="vector-pipeline"} | json | case_id="5007T000002AbcD" | join_table!=""

# NEW: Cases with incomplete multi-table joins
{service="vector-pipeline"} | json | message=~"incomplete join" | fields_populated < 30

# NEW: PII detections in EmailMessage table (high-risk)
{service="vector-pipeline"} | json | source_table="EmailMessage" | stage="pii_removal" | pii_detected="true"

# NEW: Table-specific error rate
sum by (source_table) (rate({service="vector-pipeline"} | json | level="ERROR" | source_table!="" [5m]))

# NEW: Cases missing Task data
{service="vector-pipeline"} | json | message=~"no tasks found" | case_id!=""

# NEW: Multi-table join performance
{service="vector-pipeline"} | json | task_id="multi_table_join" | fields_populated!="" | line_format "Case {{.case_id}}: {{.fields_populated}} fields in {{.duration}}ms"
```

---

## 6.4 Distributed Tracing with Jaeger

### 6.4.1 OpenTelemetry Instrumentation

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# Initialize tracer
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Configure Jaeger exporter
jaeger_exporter = JaegerExporter(
    agent_host_name='jaeger-agent',
    agent_port=6831,
)

span_processor = BatchSpanProcessor(jaeger_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Auto-instrument Flask
FlaskInstrumentor().instrument_app(app)

# Auto-instrument requests library
RequestsInstrumentor().instrument()

# Manual instrumentation example
def process_case_with_tracing(case_record):
    """
    Process case with distributed tracing
    """
    with tracer.start_as_current_span("process_case") as span:
        span.set_attribute("case.id", case_record['Id'])
        span.set_attribute("case.number", case_record['CaseNumber'])
        span.set_attribute("product", case_record.get('Product__c', ''))

        # PII removal span
        with tracer.start_as_current_span("pii_removal") as pii_span:
            cleaned_record, pii_detected = remove_pii_from_record(case_record)
            pii_span.set_attribute("pii.detected_count", len(pii_detected))
            pii_span.set_attribute("pii.types", [p['type'] for p in pii_detected])

        # Embedding generation span
        with tracer.start_as_current_span("generate_embedding") as embed_span:
            composite_text = prepare_embedding_text(cleaned_record)
            embed_span.set_attribute("text.length", len(composite_text))

            embedding = generate_embedding(composite_text)
            embed_span.set_attribute("embedding.dimension", len(embedding))
            embed_span.set_attribute("embedding.provider", "chathpe")

        # Weaviate load span
        with tracer.start_as_current_span("weaviate_load") as load_span:
            load_record_to_weaviate(cleaned_record, embedding)
            load_span.set_attribute("weaviate.class", "CaseVectorized")
            load_span.set_attribute("weaviate.tenant", "tenant_cognate")

        span.set_attribute("processing.status", "success")

        return cleaned_record
```

---

## 6.5 Grafana Dashboards

### 6.5.1 Pipeline Performance Dashboard

**Dashboard JSON (excerpt)**:
```json
{
  "dashboard": {
    "title": "Vector Pipeline Performance",
    "panels": [
      {
        "id": 1,
        "title": "Pipeline Success Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(rate(vector_pipeline_runs_total{status=\"success\"}[5m])) / sum(rate(vector_pipeline_runs_total[5m]))",
            "legendFormat": "Success Rate"
          }
        ],
        "thresholds": [
          {"value": 0.95, "color": "green"},
          {"value": 0.90, "color": "yellow"},
          {"value": 0, "color": "red"}
        ]
      },
      {
        "id": 2,
        "title": "Processing Rate (records/min)",
        "type": "graph",
        "targets": [
          {
            "expr": "vector_pipeline_records_per_minute",
            "legendFormat": "{{stage}}"
          }
        ],
        "yaxis": {"label": "Records per Minute"}
      },
      {
        "id": 3,
        "title": "Pipeline Duration by Stage",
        "type": "heatmap",
        "targets": [
          {
            "expr": "rate(vector_pipeline_duration_seconds_bucket[5m])",
            "legendFormat": "{{task_id}}"
          }
        ]
      },
      {
        "id": 4,
        "title": "PII Detections by Type",
        "type": "piechart",
        "targets": [
          {
            "expr": "sum by (pii_type) (vector_pipeline_pii_detections_total)",
            "legendFormat": "{{pii_type}}"
          }
        ]
      },
      {
        "id": 6,
        "title": "Multi-Table Join Coverage",
        "type": "stat",
        "targets": [
          {
            "expr": "multi_table_coverage_ratio{table_name=\"Task\"}",
            "legendFormat": "Tasks"
          },
          {
            "expr": "multi_table_coverage_ratio{table_name=\"WorkOrder\"}",
            "legendFormat": "Work Orders"
          },
          {
            "expr": "multi_table_coverage_ratio{table_name=\"CaseComments\"}",
            "legendFormat": "Comments"
          },
          {
            "expr": "multi_table_coverage_ratio{table_name=\"EmailMessage\"}",
            "legendFormat": "Emails"
          }
        ],
        "thresholds": [
          {"value": 0.70, "color": "green"},
          {"value": 0.50, "color": "yellow"},
          {"value": 0, "color": "red"}
        ]
      },
      {
        "id": 7,
        "title": "Fields Populated per Case",
        "type": "histogram",
        "targets": [
          {
            "expr": "rate(fields_populated_per_case_bucket[5m])",
            "legendFormat": "{{le}} fields"
          }
        ],
        "yaxis": {"label": "Cases per minute"}
      },
      {
        "id": 8,
        "title": "PII Detections by Table",
        "type": "bargauge",
        "targets": [
          {
            "expr": "sum by (table) (rate(vector_pipeline_pii_detections_total[1h]))",
            "legendFormat": "{{table}}"
          }
        ],
        "thresholds": [
          {"value": 10, "color": "green"},
          {"value": 50, "color": "yellow"},
          {"value": 100, "color": "red"}
        ]
      },
      {
        "id": 5,
        "title": "Embedding API Latency (p95)",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(embedding_api_latency_seconds_bucket[5m]))",
            "legendFormat": "{{provider}}"
          }
        ],
        "alert": {
          "conditions": [
            {
              "evaluator": {"type": "gt", "params": [5.0]},
              "operator": {"type": "and"},
              "query": {"params": ["A", "5m", "now"]},
              "reducer": {"type": "avg"}
            }
          ],
          "name": "High Embedding API Latency"
        }
      }
    ]
  }
}
```

### 6.5.2 Search Quality Dashboard

```json
{
  "dashboard": {
    "title": "Search Quality Metrics",
    "panels": [
      {
        "id": 1,
        "title": "Search Latency (p50, p95, p99)",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.50, rate(search_latency_seconds_bucket[5m]))",
            "legendFormat": "p50"
          },
          {
            "expr": "histogram_quantile(0.95, rate(search_latency_seconds_bucket[5m]))",
            "legendFormat": "p95"
          },
          {
            "expr": "histogram_quantile(0.99, rate(search_latency_seconds_bucket[5m]))",
            "legendFormat": "p99"
          }
        ],
        "thresholds": [
          {"value": 1.0, "color": "green"},
          {"value": 2.0, "color": "yellow"},
          {"value": 5.0, "color": "red"}
        ]
      },
      {
        "id": 2,
        "title": "Zero Results Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(rate(search_zero_results_total[5m])) / sum(rate(search_requests_total[5m]))",
            "legendFormat": "Zero Results %"
          }
        ]
      },
      {
        "id": 3,
        "title": "Search Requests by Product Family",
        "type": "bargauge",
        "targets": [
          {
            "expr": "sum by (product_family) (rate(search_requests_total[1h]))",
            "legendFormat": "{{product_family}}"
          }
        ]
      }
    ]
  }
}
```

---

## 6.6 Alerting Rules

### 6.6.1 Prometheus Alert Rules

**alerts.yml**:
```yaml
groups:
  - name: pipeline_alerts
    interval: 30s
    rules:
      # Critical: Pipeline failure rate > 10%
      - alert: HighPipelineFailureRate
        expr: |
          (sum(rate(vector_pipeline_runs_total{status="failure"}[5m]))
          / sum(rate(vector_pipeline_runs_total[5m]))) > 0.10
        for: 5m
        labels:
          severity: critical
          team: algoleap
        annotations:
          summary: "High pipeline failure rate detected"
          description: "Pipeline failure rate is {{ $value | humanizePercentage }}. Investigate immediately."

      # Critical: Processing rate too low
      - alert: LowProcessingRate
        expr: vector_pipeline_records_per_minute < 200
        for: 10m
        labels:
          severity: high
          team: algoleap
        annotations:
          summary: "Processing rate below target"
          description: "Current rate: {{ $value }} records/min. Target: ≥300 records/min."

      # Critical: PII detected in Weaviate
      - alert: PIILeakDetected
        expr: pii_leak_validation_failures_total > 0
        for: 1m
        labels:
          severity: critical
          team: algoleap
          team: security
        annotations:
          summary: "PII LEAK DETECTED IN WEAVIATE"
          description: "{{ $value }} PII instances detected in vector database. Immediate action required."

      # NEW: Multi-table join coverage below threshold
      - alert: LowMultiTableCoverage
        expr: |
          multi_table_coverage_ratio < 0.70
        for: 15m
        labels:
          severity: high
          team: algoleap
        annotations:
          summary: "Low multi-table join coverage detected"
          description: "Table {{ $labels.table_name }} coverage is {{ $value | humanizePercentage }}. Target: ≥70%. Cases may be missing important context."

      # NEW: Too many cases with incomplete data
      - alert: HighIncompleteDataRate
        expr: |
          (sum(rate(multi_table_join_count{join_type="incomplete"}[10m]))
          / sum(rate(multi_table_join_count[10m]))) > 0.30
        for: 10m
        labels:
          severity: medium
          team: algoleap
        annotations:
          summary: "High rate of incomplete multi-table joins"
          description: "{{ $value | humanizePercentage }} of cases have incomplete data. Check data sources and join logic."

      # NEW: PII detections by table exceeding threshold
      - alert: HighTablePIIDetectionRate
        expr: |
          rate(vector_pipeline_pii_detections_total{table="EmailMessage"}[5m]) > 50
        for: 5m
        labels:
          severity: medium
          team: algoleap
        annotations:
          summary: "Elevated PII detections in EmailMessage table"
          description: "{{ $value }} PII patterns/min detected in EmailMessage table. Review PII removal logic."

      # High: Embedding API latency
      - alert: HighEmbeddingAPILatency
        expr: |
          histogram_quantile(0.95,
            rate(embedding_api_latency_seconds_bucket[5m])
          ) > 5.0
        for: 10m
        labels:
          severity: high
          team: algoleap
        annotations:
          summary: "High embedding API latency"
          description: "p95 latency: {{ $value }}s. Consider scaling or switching to fallback."

      # Medium: Weaviate cluster health
      - alert: WeaviateClusterDegraded
        expr: up{job="weaviate"} == 0
        for: 2m
        labels:
          severity: critical
          team: algoleap
        annotations:
          summary: "Weaviate cluster is down"
          description: "Weaviate cluster unavailable. Search functionality impacted."

  - name: search_quality_alerts
    interval: 1m
    rules:
      # High: Search latency degradation
      - alert: HighSearchLatency
        expr: |
          histogram_quantile(0.95,
            rate(search_latency_seconds_bucket[5m])
          ) > 2.0
        for: 5m
        labels:
          severity: high
          team: algoleap
        annotations:
          summary: "Search latency degraded"
          description: "p95 latency: {{ $value }}s. Target: <1s."

      # Medium: High zero results rate
      - alert: HighZeroResultsRate
        expr: |
          (sum(rate(search_zero_results_total[5m]))
          / sum(rate(search_requests_total[5m]))) > 0.15
        for: 15m
        labels:
          severity: medium
          team: algoleap
        annotations:
          summary: "High zero results rate"
          description: "{{ $value | humanizePercentage }} of searches return zero results."

      # Low: Search API errors
      - alert: SearchAPIErrors
        expr: |
          sum(rate(search_requests_total{status="error"}[5m])) > 10
        for: 5m
        labels:
          severity: medium
          team: algoleap
        annotations:
          summary: "Elevated search API errors"
          description: "{{ $value }} errors/sec in search API."
```

### 6.6.2 Alertmanager Configuration

**alertmanager.yml**:
```yaml
global:
  resolve_timeout: 5m
  slack_api_url: 'https://hooks.slack.com/services/xxx'

# Route tree
route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'

  routes:
    # Critical alerts → PagerDuty + Slack
    - match:
        severity: critical
      receiver: 'pagerduty-critical'
      continue: true

    - match:
        severity: critical
      receiver: 'slack-critical'

    # High severity → Slack
    - match:
        severity: high
      receiver: 'slack-high'

    # Medium severity → Slack (less frequent)
    - match:
        severity: medium
      receiver: 'slack-medium'
      repeat_interval: 24h

# Receivers
receivers:
  - name: 'default'
    slack_configs:
      - channel: '#vector-search-alerts'
        title: 'Alert: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

  - name: 'pagerduty-critical'
    pagerduty_configs:
      - service_key: 'xxx'
        description: '{{ .GroupLabels.alertname }}: {{ .CommonAnnotations.summary }}'

  - name: 'slack-critical'
    slack_configs:
      - channel: '#vector-search-critical'
        color: 'danger'
        title: '🚨 CRITICAL: {{ .GroupLabels.alertname }}'
        text: |
          *Summary:* {{ .CommonAnnotations.summary }}
          *Description:* {{ .CommonAnnotations.description }}
          *Severity:* {{ .CommonLabels.severity }}

  - name: 'slack-high'
    slack_configs:
      - channel: '#vector-search-alerts'
        color: 'warning'
        title: '⚠️ HIGH: {{ .GroupLabels.alertname }}'

  - name: 'slack-medium'
    slack_configs:
      - channel: '#vector-search-alerts'
        color: 'good'
        title: 'ℹ️ MEDIUM: {{ .GroupLabels.alertname }}'
```

---

## Summary: Observability Best Practices

1. **Metrics**: Use Prometheus for time-series metrics (RED method - Rate, Errors, Duration)
2. **Logs**: Structured JSON logs aggregated in Loki for searchability
3. **Traces**: Distributed tracing with Jaeger for end-to-end request flow
4. **Dashboards**: Grafana for visualization and real-time monitoring
5. **Alerts**: Proactive alerting with severity-based routing

---

## Multi-Table Monitoring Summary

### Key Metrics Added for Multi-Table Architecture

**1. Join Coverage Metrics**
```python
multi_table_coverage_ratio  # Percentage of cases with data from each table
```
- **Target**: ≥70% for Task, WorkOrder tables
- **Alert**: LowMultiTableCoverage when below threshold

**2. Join Performance Metrics**
```python
multi_table_join_count  # Total joins by type (complete/incomplete)
fields_populated_per_case  # Distribution of field counts (buckets: 10, 20, 30, 35, 40, 44)
```
- **Target**: ≥80% complete joins, avg 35+ fields populated
- **Alert**: HighIncompleteDataRate when >30% incomplete

**3. Table-Specific PII Metrics**
```python
vector_pipeline_pii_detections_total{table="EmailMessage"}  # High-risk table
```
- **Target**: Monitor for spikes indicating new PII patterns
- **Alert**: HighTablePIIDetectionRate when >50 detections/min

### Grafana Dashboard Panels for Multi-Table

**Panel 6: Multi-Table Join Coverage**
- Shows coverage % for Task, WorkOrder, CaseComments, EmailMessage
- Color thresholds: Green (≥70%), Yellow (50-70%), Red (<50%)

**Panel 7: Fields Populated per Case**
- Histogram showing distribution of populated fields (out of 44 total)
- Helps identify incomplete data issues

**Panel 8: PII Detections by Table**
- Bar gauge showing PII detection rate per table
- Highlights high-risk tables (EmailMessage, WorkOrder, CaseComments)

### LogQL Queries for Multi-Table Debugging

```logql
# Cases with incomplete joins
{service="vector-pipeline"} | json | fields_populated < 30

# Table-specific errors
sum by (source_table) (rate({service="vector-pipeline"} | json | level="ERROR" | source_table!="" [5m]))

# Multi-table join performance
{service="vector-pipeline"} | json | task_id="multi_table_join" | fields_populated!=""
```

### Alert Rules for Multi-Table Health

1. **LowMultiTableCoverage** (High severity)
   - Fires when table coverage drops below 70%
   - Indicates data source issues or join failures

2. **HighIncompleteDataRate** (Medium severity)
   - Fires when >30% of cases have incomplete data
   - Suggests missing child records (Tasks, WorkOrders)

3. **HighTablePIIDetectionRate** (Medium severity)
   - Fires when EmailMessage table shows >50 PII detections/min
   - Indicates potential PII removal logic issues

---

## References
- Prometheus Best Practices
- Grafana Loki Documentation
- OpenTelemetry Instrumentation Guide
- The RED Method (Rate, Errors, Duration)
- The Four Golden Signals of Monitoring
