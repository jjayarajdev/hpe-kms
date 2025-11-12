# Infrastructure

Kubernetes, Terraform, and Helm configurations for deployment.

## Structure

- **kubernetes/**: Kubernetes manifests
  - base/: Base configurations
  - overlays/: Environment-specific overlays (dev, staging, prod)
- **terraform/**: Infrastructure as Code
  - modules/: Reusable Terraform modules
  - environments/: Environment-specific configurations
- **helm/**: Helm charts
  - kms-api/: API service chart
  - kms-pipeline/: Airflow pipeline chart
  - kms-monitoring/: Observability stack chart

## Deployment

### Prerequisites
- Kubernetes cluster on HPE PC AI
- kubectl configured
- Helm 3.x installed
- Terraform 1.5+ installed

### Deploy to Development
```bash
kubectl apply -k infrastructure/kubernetes/overlays/dev
```

### Deploy to Production
```bash
kubectl apply -k infrastructure/kubernetes/overlays/prod
```

## Resources

- Weaviate: 32GB RAM, 8 vCPUs
- Airflow: 16GB RAM, 4 vCPUs
- API Service: 8GB RAM, 2 vCPUs
