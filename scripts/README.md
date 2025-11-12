# Scripts

Utility scripts for development, deployment, and maintenance.

## Purpose

This directory contains helper scripts for:
- Environment setup
- Data migration
- Database backups
- Performance testing
- Deployment automation
- Monitoring setup

## Common Scripts

- `setup_dev.sh`: Set up local development environment
- `run_pipeline.sh`: Manually trigger pipeline execution
- `backup_weaviate.sh`: Backup Weaviate vector database
- `restore_weaviate.sh`: Restore from backup
- `load_test_data.sh`: Load test datasets into system
- `check_pii_leakage.sh`: Validate PII removal
- `deploy.sh`: Deploy to Kubernetes cluster
- `rollback.sh`: Rollback to previous version

## Usage

All scripts should be executable and include help text:

```bash
# Make script executable
chmod +x scripts/setup_dev.sh

# Run with help
./scripts/setup_dev.sh --help
```

## Safety

- All production scripts require confirmation prompts
- Backup scripts run before destructive operations
- Dry-run mode available for testing
