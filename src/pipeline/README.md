# Data Pipeline

Apache Airflow orchestrated data pipeline for processing SFDC case data.

## Components

- **dags/**: Airflow DAG definitions
- **operators/**: Custom Airflow operators
- **sensors/**: Custom Airflow sensors
- **hooks/**: Connection hooks for external systems
- **utils/**: Pipeline utility functions
- **jobs/**: PySpark job implementations
  - extraction/: Data extraction from SFDC tables
  - transformation/: Multi-table joins and transformations
  - embedding/: Text embedding generation
  - loading/: Vector database loading
  - reconciliation/: Data validation and reconciliation

## Key DAGs

- `case_processing_dag`: Main pipeline for processing cases
- `incremental_update_dag`: Daily incremental updates
- `reconciliation_dag`: Data quality validation
