"""
KMS 2.6 Monitoring Module

Provides Prometheus metrics instrumentation and metrics server for monitoring
pipeline performance, data quality, system health, and business metrics.
"""

from src.pipeline.monitoring.prometheus_metrics import (
    # Context managers
    StageTimer,
    APITimer,
    
    # Recording functions
    record_records_processed,
    record_pii_detection,
    update_pii_redaction_rate,
    record_schema_validation_error,
    record_reconciliation_mismatch,
    update_reconciliation_mismatch_rate,
    update_pipeline_throughput,
    update_vector_db_count,
    record_search_query,
    record_embedding_generation,
    record_openai_usage,
    update_memory_usage,
    update_db_connections,
    
    # Info functions
    set_pipeline_info,
    set_last_run_info,
    
    # Metrics export
    get_metrics,
    get_content_type,
)

__all__ = [
    'StageTimer',
    'APITimer',
    'record_records_processed',
    'record_pii_detection',
    'update_pii_redaction_rate',
    'record_schema_validation_error',
    'record_reconciliation_mismatch',
    'update_reconciliation_mismatch_rate',
    'update_pipeline_throughput',
    'update_vector_db_count',
    'record_search_query',
    'record_embedding_generation',
    'record_openai_usage',
    'update_memory_usage',
    'update_db_connections',
    'set_pipeline_info',
    'set_last_run_info',
    'get_metrics',
    'get_content_type',
]
