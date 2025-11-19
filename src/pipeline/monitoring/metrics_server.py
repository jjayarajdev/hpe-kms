"""
KMS 2.6 Prometheus Metrics HTTP Server

Exposes metrics endpoint for Prometheus scraping.

Endpoints:
- GET /metrics - Prometheus metrics in text format
- GET /health - Health check endpoint
"""

import logging
from flask import Flask, Response, request, jsonify
from src.pipeline.monitoring.prometheus_metrics import (
    get_metrics, get_content_type,
    records_processed_total, pipeline_throughput,
    pii_detections_total, reconciliation_mismatch_rate,
    stage_duration_seconds, api_request_duration_seconds,
    active_dag_runs
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)


@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint"""
    try:
        metrics_data = get_metrics()
        return Response(metrics_data, mimetype=get_content_type())
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        return Response("Error generating metrics", status=500)


@app.route('/record_metrics', methods=['POST'])
def record_metrics():
    """Receive and record metrics from DAG runs"""
    try:
        data = request.get_json()

        # Record total records extracted
        if data.get('total_records_extracted'):
            records_processed_total.labels(
                stage='extract',
                table='all',
                status='success'
            ).inc(data['total_records_extracted'])

        # Record PII detections (even if 0, to show in charts)
        pii_count = data.get('total_pii_detected', 0)
        if pii_count >= 0:  # Include 0 to show the metric exists
            pii_detections_total.labels(
                detector_type='all',
                field_name='all',
                table='all'
            ).inc(pii_count)

        # Record enrichment stage
        if data.get('cases_enriched'):
            records_processed_total.labels(
                stage='enrich',
                table='all',
                status='success'
            ).inc(data['cases_enriched'])

        # Set reconciliation mismatch rate
        if 'reconciliation_mismatch_rate' in data:
            reconciliation_mismatch_rate.labels(table='all').set(
                data['reconciliation_mismatch_rate']
            )

        # Record embeddings
        if data.get('embeddings_generated'):
            records_processed_total.labels(
                stage='embedding',
                table='all',
                status='success'
            ).inc(data['embeddings_generated'])

        # Record loaded records
        if data.get('records_loaded'):
            records_processed_total.labels(
                stage='load',
                table='all',
                status='success'
            ).inc(data['records_loaded'])

        # ===== NEW: Record stage durations =====
        if 'extract_duration_seconds' in data:
            stage_duration_seconds.labels(stage='extract', table='all').observe(
                data['extract_duration_seconds']
            )

        if 'pii_duration_seconds' in data:
            stage_duration_seconds.labels(stage='pii', table='all').observe(
                data['pii_duration_seconds']
            )

        if 'enrich_duration_seconds' in data:
            stage_duration_seconds.labels(stage='enrich', table='all').observe(
                data['enrich_duration_seconds']
            )

        if 'embedding_duration_seconds' in data:
            stage_duration_seconds.labels(stage='embedding', table='all').observe(
                data['embedding_duration_seconds']
            )

        if 'load_duration_seconds' in data:
            stage_duration_seconds.labels(stage='load', table='all').observe(
                data['load_duration_seconds']
            )

        if 'reconcile_duration_seconds' in data:
            stage_duration_seconds.labels(stage='reconcile', table='all').observe(
                data['reconcile_duration_seconds']
            )

        # ===== NEW: Record OpenAI API latency =====
        if 'openai_avg_api_latency_seconds' in data:
            api_request_duration_seconds.labels(
                api='openai',
                method='embeddings'
            ).observe(data['openai_avg_api_latency_seconds'])

        logger.info(f"Recorded metrics: {data}")
        return jsonify({'status': 'success', 'recorded': data}), 200

    except Exception as e:
        logger.error(f"Error recording metrics: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/dag_start', methods=['POST'])
def dag_start():
    """Increment active DAG runs counter"""
    try:
        data = request.get_json()
        active_dag_runs.inc()  # Increment by 1
        logger.info(f"DAG started: {data.get('dag_id')} - {data.get('run_id')}")
        return jsonify({'status': 'success', 'active_runs': active_dag_runs._value.get()}), 200
    except Exception as e:
        logger.error(f"Error incrementing active DAG runs: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/dag_end', methods=['POST'])
def dag_end():
    """Decrement active DAG runs counter"""
    try:
        data = request.get_json()
        active_dag_runs.dec()  # Decrement by 1
        logger.info(f"DAG completed: {data.get('dag_id')} - {data.get('run_id')}")
        return jsonify({'status': 'success', 'active_runs': active_dag_runs._value.get()}), 200
    except Exception as e:
        logger.error(f"Error decrementing active DAG runs: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'healthy', 'service': 'kms-metrics'}, 200


@app.route('/')
def index():
    """Index page with links"""
    html = """
    <html>
    <head><title>KMS 2.6 Metrics</title></head>
    <body>
        <h1>KMS 2.6 Prometheus Metrics</h1>
        <ul>
            <li><a href="/metrics">Metrics</a> - Prometheus metrics endpoint</li>
            <li><a href="/health">Health</a> - Health check</li>
        </ul>
    </body>
    </html>
    """
    return html


def run_server(host: str = '0.0.0.0', port: int = 9090):
    """Run metrics server"""
    logger.info(f"Starting metrics server on {host}:{port}")
    app.run(host=host, port=port, debug=False)


if __name__ == '__main__':
    run_server()
