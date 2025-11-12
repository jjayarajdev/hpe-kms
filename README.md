# KMS 2.5 Documentation

This directory contains comprehensive technical documentation for the HPE Knowledge Management System (KMS) 2.5 Vector Search implementation.

## Documents

### 1. [project-flow-and-architecture.md](./project-flow-and-architecture.md)
**Main architecture and flow documentation with 25 Mermaid diagrams**

Covers:
- Overall System Architecture
- Data Pipeline Flow (7 stages)
- Multi-Table Data Integration (6 SFDC tables)
- Text Embedding Strategy
- Hybrid Search Architecture
- PII Removal Pipeline (4 stages)
- Reconciliation & Recovery (4 layers)
- Observability Stack (Prometheus/Loki/Grafana/Jaeger)
- Phased Deployment (Gantt chart)
- Technology Stack
- Search Query Flow (sequence diagram)
- Performance Optimization
- Quality Verification Process
- Compliance & Security
- Disaster Recovery
- Cost Analysis

### 2. [implementation-guide.md](./implementation-guide.md)
**Practical developer guide with code patterns and configurations**

Includes:
- Airflow DAG structure and configuration
- PySpark multi-table join implementation
- Weaviate schema definition
- Hybrid search engine implementation
- Error handling with circuit breakers and retries
- Testing strategies (unit, integration, E2E)
- Kubernetes deployment manifests
- Prometheus configuration and alert rules
- Best practices summary

## Quick Start

1. **For Architecture Review**: Start with `project-flow-and-architecture.md` to understand the big picture
2. **For Implementation**: Use `implementation-guide.md` for code examples and deployment configs
3. **For Context**: See `/CLAUDE.md` at the repository root for high-level guidance

## Diagrams

All diagrams are created using Mermaid and can be viewed:
- On GitHub (automatic rendering)
- In VS Code (with Mermaid preview extension)
- In documentation platforms (GitBook, MkDocs, etc.)
- Online at https://mermaid.live/

## Key Technologies

- **Vector Database**: Weaviate (HNSW index, cosine similarity)
- **Embeddings**: ChatHPE text-embedding-3-large (3,072 dimensions)
- **Processing**: Apache Airflow + PySpark
- **Observability**: Prometheus, Loki, Grafana, Jaeger
- **Infrastructure**: Kubernetes on HPE PC AI
- **Security**: PII removal (Regex + spaCy NER + Microsoft Presidio)

## Project Overview

- **Timeline**: 12 weeks
- **Budget**: ~93,725 USD
- **Client**: HPE Global Response Center (GRS)
- **Vendor**: Algoleap Technologies
- **Goal**: Transform 1M+ historical support cases into semantic search system

## Performance Targets

| Metric | Target |
|--------|--------|
| Precision@5 | > 85% |
| Search Latency (p95) | < 1 second |
| Processing Rate | ≥ 300 cases/min |
| PII Detection Rate | 100% (zero leakage) |
| Pipeline Success Rate | > 95% |

## Phased Approach

1. **Phase 1 (Week 2-3)**: 1K dev sample - Schema validation, API development
2. **Phase 2 (Week 6)**: 100K validation sample - GRS team review, performance testing
3. **Phase 3 (Week 7-8)**: Accuracy tuning - Precision optimization, regression testing
4. **Phase 4 (Week 9-10)**: Full load - 1M+ historical cases

## Contact

For questions or clarifications, refer to:
- Technical planning documents in `/reference_docs/`
- Project proposal: `/reference_docs/KMS_2.6.pdf`
- Master index: `/reference_docs/00_Technical_Planning_Index.md`

---

**Last Updated**: November 11, 2025
**Version**: 1.0
**Status**: Technical Documentation - Planning Phase
