# Source Code

This directory contains all source code for the KMS 2.5 Vector Search application.

## Structure

- **pipeline/**: Airflow DAGs and PySpark jobs for data processing
- **api/**: REST API service for search and vector queries
- **pii_removal/**: PII detection and removal service
- **common/**: Shared utilities, logging, metrics, and configuration

## Development Guidelines

- Follow Python PEP 8 style guide
- Add unit tests for all new features
- Use type hints for function signatures
- Document all public APIs with docstrings
