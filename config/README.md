# Configuration

Configuration files for all KMS components.

## Structure

- **airflow/**: Airflow configuration
  - dags/: DAG configuration files
  - plugins/: Plugin configurations
  - connections/: External system connections
- **weaviate/**: Weaviate vector database
  - schemas/: Collection schemas
  - backups/: Backup configurations
- **spark/**: Apache Spark configuration
  - conf/: Spark properties
  - jars/: External JARs
- **prometheus/**: Prometheus monitoring
  - rules/: Alert rules
  - targets/: Scrape targets
- **grafana/**: Grafana dashboards
  - dashboards/: Dashboard JSON
  - datasources/: Data source configurations

## Environment Variables

Key environment variables are defined in:
- `.env.dev` - Development environment
- `.env.staging` - Staging environment
- `.env.prod` - Production environment

## Secrets Management

Sensitive configurations are managed via:
- Kubernetes Secrets
- HashiCorp Vault integration
- Never commit secrets to version control
