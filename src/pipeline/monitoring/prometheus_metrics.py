"""
KMS 2.6 Prometheus Metrics Module

Exports metrics for monitoring pipeline performance, data quality, and system health.

Metrics Categories:
1. Pipeline Performance (throughput, latency, processing time)
2. Data Quality (PII detection, validation errors, mismatch rates)
3. System Health (API errors, database connections, memory usage)
4. Business Metrics (records processed, search queries, cache hits)
"""

import logging
from typing import Dict, Any
from prometheus_client import Counter, Gauge, Histogram, Summary, Info
from prometheus_client import CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST

logger = logging.getLogger(__name__)


# ============================================================================
# Registry Setup
# ============================================================================

# Default registry for application metrics
registry = CollectorRegistry()


# ============================================================================
# 1. Pipeline Performance Metrics
# ============================================================================

# Record processing counters
records_processed_total = Counter(
    'kms_records_processed_total',
    'Total number of records processed by stage',
    ['stage', 'table', 'status'],
    registry=registry
)

# Stage execution time
stage_duration_seconds = Histogram(
    'kms_stage_duration_seconds',
    'Time spent in each pipeline stage',
    ['stage', 'table'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
    registry=registry
)

# Pipeline throughput
pipeline_throughput = Gauge(
    'kms_pipeline_throughput_records_per_minute',
    'Current pipeline throughput in records per minute',
    ['stage'],
    registry=registry
)

# End-to-end pipeline latency
pipeline_latency_seconds = Summary(
    'kms_pipeline_latency_seconds',
    'End-to-end pipeline processing latency',
    registry=registry
)

# Active DAG runs
active_dag_runs = Gauge(
    'kms_active_dag_runs',
    'Number of currently active DAG runs',
    registry=registry
)


# ============================================================================
# 2. Data Quality Metrics
# ============================================================================

# PII detection results
pii_detections_total = Counter(
    'kms_pii_detections_total',
    'Total PII patterns detected and redacted',
    ['detector_type', 'field_name', 'table'],
    registry=registry
)

# PII redaction rate (percentage of fields with PII)
pii_redaction_rate = Gauge(
    'kms_pii_redaction_rate_percent',
    'Percentage of fields containing PII',
    ['table'],
    registry=registry
)

# Schema validation errors
schema_validation_errors_total = Counter(
    'kms_schema_validation_errors_total',
    'Total schema validation errors',
    ['table', 'field', 'error_type'],
    registry=registry
)

# Data reconciliation mismatches
reconciliation_mismatches_total = Counter(
    'kms_reconciliation_mismatches_total',
    'Total checksum mismatches during reconciliation',
    ['table'],
    registry=registry
)

# Data reconciliation mismatch rate
reconciliation_mismatch_rate = Gauge(
    'kms_reconciliation_mismatch_rate_percent',
    'Percentage of records with checksum mismatches',
    ['table'],
    registry=registry
)


# ============================================================================
# 3. System Health Metrics
# ============================================================================

# API call metrics (OpenAI, Weaviate)
api_requests_total = Counter(
    'kms_api_requests_total',
    'Total API requests made',
    ['api', 'method', 'status'],
    registry=registry
)

api_request_duration_seconds = Histogram(
    'kms_api_request_duration_seconds',
    'API request duration',
    ['api', 'method'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry
)

# API error rate
api_error_rate = Gauge(
    'kms_api_error_rate_percent',
    'API error rate percentage',
    ['api'],
    registry=registry
)

# Database connection pool
db_connections_active = Gauge(
    'kms_db_connections_active',
    'Number of active database connections',
    ['database'],
    registry=registry
)

db_connections_idle = Gauge(
    'kms_db_connections_idle',
    'Number of idle database connections',
    ['database'],
    registry=registry
)

# Memory usage
memory_usage_bytes = Gauge(
    'kms_memory_usage_bytes',
    'Memory usage in bytes',
    ['component'],
    registry=registry
)


# ============================================================================
# 4. Business Metrics
# ============================================================================

# Total records in vector database
vector_db_records_total = Gauge(
    'kms_vector_db_records_total',
    'Total number of records in Weaviate',
    ['collection'],
    registry=registry
)

# Search query metrics
search_queries_total = Counter(
    'kms_search_queries_total',
    'Total number of search queries',
    ['search_type', 'fallback_stage'],
    registry=registry
)

search_query_latency_seconds = Histogram(
    'kms_search_query_latency_seconds',
    'Search query response time',
    ['search_type'],
    buckets=[0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.25, 0.5, 1.0],
    registry=registry
)

# Search result quality
search_results_returned = Histogram(
    'kms_search_results_returned',
    'Number of results returned per query',
    ['search_type'],
    buckets=[0, 1, 5, 10, 20, 50, 100],
    registry=registry
)

# Embedding generation metrics
embeddings_generated_total = Counter(
    'kms_embeddings_generated_total',
    'Total embeddings generated',
    ['model', 'status'],
    registry=registry
)

embedding_generation_time_seconds = Histogram(
    'kms_embedding_generation_time_seconds',
    'Time to generate embeddings',
    ['batch_size'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
    registry=registry
)

# Token usage and cost
openai_tokens_used_total = Counter(
    'kms_openai_tokens_used_total',
    'Total OpenAI tokens consumed',
    ['model', 'operation'],
    registry=registry
)

openai_cost_usd_total = Counter(
    'kms_openai_cost_usd_total',
    'Total OpenAI API cost in USD',
    ['model'],
    registry=registry
)


# ============================================================================
# 5. Pipeline Status Information
# ============================================================================

pipeline_info = Info(
    'kms_pipeline_info',
    'KMS 2.6 Pipeline version and configuration',
    registry=registry
)

last_run_info = Info(
    'kms_last_run_info',
    'Information about the last pipeline run',
    registry=registry
)


# ============================================================================
# Helper Functions
# ============================================================================

def set_pipeline_info(version: str, tables: int, fields: int, model: str):
    """Set pipeline configuration information"""
    pipeline_info.info({
        'version': version,
        'tables': str(tables),
        'fields': str(fields),
        'embedding_model': model,
        'vector_dimensions': '3072'
    })


def set_last_run_info(status: str, start_time: str, end_time: str, records: int):
    """Set information about last pipeline run"""
    last_run_info.info({
        'status': status,
        'start_time': start_time,
        'end_time': end_time,
        'records_processed': str(records)
    })


def get_metrics() -> bytes:
    """Generate Prometheus metrics output in text format"""
    return generate_latest(registry)


def get_content_type() -> str:
    """Get content type for Prometheus metrics endpoint"""
    return CONTENT_TYPE_LATEST


# ============================================================================
# Context Managers for Timing
# ============================================================================

class StageTimer:
    """Context manager for timing pipeline stages"""

    def __init__(self, stage: str, table: str = 'all'):
        self.stage = stage
        self.table = table
        self.histogram = stage_duration_seconds.labels(stage=stage, table=table)

    def __enter__(self):
        self.timer = self.histogram.time()
        self.timer.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.timer.__exit__(exc_type, exc_val, exc_tb)


class APITimer:
    """Context manager for timing API requests"""

    def __init__(self, api: str, method: str):
        self.api = api
        self.method = method
        self.histogram = api_request_duration_seconds.labels(api=api, method=method)

    def __enter__(self):
        self.timer = self.histogram.time()
        self.timer.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.timer.__exit__(exc_type, exc_val, exc_tb)

        # Record API request status
        status = 'success' if exc_type is None else 'error'
        api_requests_total.labels(api=self.api, method=self.method, status=status).inc()


# ============================================================================
# Metrics Recording Functions
# ============================================================================

def record_records_processed(stage: str, table: str, count: int, status: str = 'success'):
    """Record number of records processed"""
    records_processed_total.labels(stage=stage, table=table, status=status).inc(count)


def record_pii_detection(detector_type: str, field_name: str, table: str, count: int = 1):
    """Record PII detection"""
    pii_detections_total.labels(
        detector_type=detector_type,
        field_name=field_name,
        table=table
    ).inc(count)


def update_pii_redaction_rate(table: str, rate_percent: float):
    """Update PII redaction rate"""
    pii_redaction_rate.labels(table=table).set(rate_percent)


def record_schema_validation_error(table: str, field: str, error_type: str):
    """Record schema validation error"""
    schema_validation_errors_total.labels(
        table=table,
        field=field,
        error_type=error_type
    ).inc()


def record_reconciliation_mismatch(table: str, count: int = 1):
    """Record reconciliation mismatch"""
    reconciliation_mismatches_total.labels(table=table).inc(count)


def update_reconciliation_mismatch_rate(table: str, rate_percent: float):
    """Update reconciliation mismatch rate"""
    reconciliation_mismatch_rate.labels(table=table).set(rate_percent)


def update_pipeline_throughput(stage: str, records_per_minute: float):
    """Update pipeline throughput"""
    pipeline_throughput.labels(stage=stage).set(records_per_minute)


def update_vector_db_count(collection: str, count: int):
    """Update vector database record count"""
    vector_db_records_total.labels(collection=collection).set(count)


def record_search_query(search_type: str, latency_seconds: float,
                        results_count: int, fallback_stage: str = 'none'):
    """Record search query metrics"""
    search_queries_total.labels(
        search_type=search_type,
        fallback_stage=fallback_stage
    ).inc()

    search_query_latency_seconds.labels(search_type=search_type).observe(latency_seconds)
    search_results_returned.labels(search_type=search_type).observe(results_count)


def record_embedding_generation(model: str, batch_size: int,
                                time_seconds: float, status: str = 'success'):
    """Record embedding generation metrics"""
    embeddings_generated_total.labels(model=model, status=status).inc(batch_size)
    embedding_generation_time_seconds.labels(batch_size=str(batch_size)).observe(time_seconds)


def record_openai_usage(model: str, operation: str, tokens: int, cost_usd: float):
    """Record OpenAI API usage and cost"""
    openai_tokens_used_total.labels(model=model, operation=operation).inc(tokens)
    openai_cost_usd_total.labels(model=model).inc(cost_usd)


def update_memory_usage(component: str, bytes_used: int):
    """Update memory usage"""
    memory_usage_bytes.labels(component=component).set(bytes_used)


def update_db_connections(database: str, active: int, idle: int):
    """Update database connection pool metrics"""
    db_connections_active.labels(database=database).set(active)
    db_connections_idle.labels(database=database).set(idle)


# ============================================================================
# Initialization
# ============================================================================

def initialize_metrics():
    """Initialize metrics with default values"""
    logger.info("Initializing Prometheus metrics")

    # Set pipeline info
    set_pipeline_info(
        version='2.6',
        tables=6,
        fields=44,
        model='text-embedding-3-large'
    )

    logger.info("Prometheus metrics initialized")


# Initialize on import
initialize_metrics()
