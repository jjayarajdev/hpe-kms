# KMS 2.5 Project Structure

This document describes the complete folder structure for the HPE Knowledge Management System (KMS) 2.5 Vector Search application.

## Root Directory Structure

```
KMS/
├── CLAUDE.md                      # AI assistant guidance
├── PROJECT_STRUCTURE.md           # This file
├── README.md                      # Project overview
├── .gitignore                     # Git ignore rules
├── requirements.txt               # Python dependencies
├── setup.py                       # Package setup
├── pyproject.toml                 # Project metadata
│
├── src/                           # Source code
├── tests/                         # Test suite
├── config/                        # Configuration files
├── data/                          # Data storage
├── docs/                          # Documentation
├── infrastructure/                # Deployment configs
├── monitoring/                    # Observability stack
├── scripts/                       # Utility scripts
├── notebooks/                     # Jupyter notebooks
├── logs/                          # Application logs
└── reference_docs/                # Planning documents
```

## Detailed Structure

### Source Code (`src/`)

```
src/
├── README.md
├── __init__.py
│
├── pipeline/                      # Data processing pipeline
│   ├── README.md
│   ├── __init__.py
│   ├── dags/                      # Airflow DAG definitions
│   ├── operators/                 # Custom Airflow operators
│   ├── sensors/                   # Custom Airflow sensors
│   ├── hooks/                     # External system connections
│   ├── utils/                     # Pipeline utilities
│   └── jobs/                      # PySpark job implementations
│       ├── extraction/            # SFDC data extraction
│       ├── transformation/        # Multi-table joins
│       ├── embedding/             # Text embedding generation
│       ├── loading/               # Weaviate loading
│       └── reconciliation/        # Data validation
│
├── api/                           # REST API service
│   ├── README.md
│   ├── __init__.py
│   ├── main.py                    # FastAPI application
│   ├── routes/                    # API endpoints
│   ├── models/                    # Data models
│   ├── schemas/                   # Request/response schemas
│   ├── middleware/                # Auth, logging, rate limiting
│   └── services/                  # Business logic
│       ├── search/                # Hybrid search engine
│       ├── vector/                # Vector operations
│       ├── metadata/              # Metadata filtering
│       └── recommendations/       # Case recommendations
│
├── pii_removal/                   # PII detection & removal
│   ├── README.md
│   ├── __init__.py
│   ├── detectors/                 # Regex, NER, Presidio
│   ├── processors/                # Removal & masking logic
│   ├── validators/                # Leakage validation
│   └── rules/                     # Custom detection rules
│
└── common/                        # Shared utilities
    ├── __init__.py
    ├── logging/                   # Logging configuration
    ├── metrics/                   # Prometheus metrics
    ├── config/                    # Config management
    ├── exceptions/                # Custom exceptions
    └── utils/                     # Helper functions
```

### Tests (`tests/`)

```
tests/
├── README.md
├── conftest.py                    # Pytest configuration
│
├── unit/                          # Unit tests
│   ├── pipeline/                  # Pipeline unit tests
│   ├── api/                       # API unit tests
│   └── pii_removal/               # PII unit tests
│
├── integration/                   # Integration tests
│   ├── search/                    # Search functionality
│   ├── embedding/                 # Embedding generation
│   └── reconciliation/            # Data validation
│
├── e2e/                           # End-to-end tests
│   ├── scenarios/                 # User journey tests
│   └── fixtures/                  # Test data
│
└── performance/                   # Load & performance tests
```

### Configuration (`config/`)

```
config/
├── README.md
│
├── airflow/                       # Airflow configuration
│   ├── dags/                      # DAG configs
│   ├── plugins/                   # Plugin configs
│   └── connections/               # Connection configs
│
├── weaviate/                      # Vector database
│   ├── schemas/                   # Collection schemas
│   └── backups/                   # Backup configs
│
├── spark/                         # Spark configuration
│   ├── conf/                      # Spark properties
│   └── jars/                      # External JARs
│
├── prometheus/                    # Monitoring
│   ├── rules/                     # Alert rules
│   └── targets/                   # Scrape targets
│
└── grafana/                       # Dashboards
    ├── dashboards/                # Dashboard JSONs
    └── datasources/               # Data sources
```

### Data (`data/`)

```
data/
├── README.md
├── case-fields-mapping.json       # Field mapping & test data
├── sample.txt                     # Sample data format
│
├── raw/                           # Raw SFDC data
│   ├── vw_de_sfdc_case_snapshot/
│   ├── vw_de_sfdc_task_snapshot/
│   ├── vw_de_sfdc_workorder_snapshot/
│   └── vw_de_sfdc_casecomment_snapshot/
│
├── processed/                     # Cleaned & joined data
│   └── pii_clean/                 # PII-removed data
│
├── embeddings/                    # Vector embeddings
│   ├── issue_vectors/             # Issue embeddings
│   └── resolution_vectors/        # Resolution embeddings
│
└── test_datasets/                 # Test data
    ├── dimm_failure/
    ├── tape_drive_failure/
    ├── hdd_failure/
    ├── false_alarm/
    └── order_processing/
```

### Infrastructure (`infrastructure/`)

```
infrastructure/
├── README.md
│
├── kubernetes/                    # K8s manifests
│   ├── base/                      # Base configurations
│   └── overlays/                  # Environment overlays
│       ├── dev/
│       ├── staging/
│       └── prod/
│
├── terraform/                     # Infrastructure as Code
│   ├── modules/                   # Reusable modules
│   └── environments/              # Environment configs
│       ├── dev/
│       ├── staging/
│       └── prod/
│
└── helm/                          # Helm charts
    ├── kms-api/                   # API service chart
    ├── kms-pipeline/              # Pipeline chart
    └── kms-monitoring/            # Observability chart
```

### Monitoring (`monitoring/`)

```
monitoring/
├── README.md
│
├── prometheus/                    # Prometheus configs
├── grafana/                       # Grafana setup
├── loki/                          # Log aggregation
├── jaeger/                        # Distributed tracing
├── dashboards/                    # Pre-built dashboards
└── alerts/                        # Alert rules
```

### Documentation (`docs/`)

```
docs/
├── README.md
├── project-flow-and-architecture.md    # 25 Mermaid diagrams
├── implementation-guide.md             # Code patterns & configs
├── api-reference.md                    # API documentation
├── deployment-guide.md                 # Deployment instructions
└── troubleshooting.md                  # Common issues
```

### Scripts (`scripts/`)

```
scripts/
├── README.md
├── setup_dev.sh                   # Dev environment setup
├── run_pipeline.sh                # Manual pipeline trigger
├── backup_weaviate.sh             # Database backup
├── restore_weaviate.sh            # Database restore
├── load_test_data.sh              # Load test datasets
├── check_pii_leakage.sh           # PII validation
├── deploy.sh                      # Deployment script
└── rollback.sh                    # Rollback script
```

### Notebooks (`notebooks/`)

```
notebooks/
├── README.md
├── 01_data_exploration.ipynb      # Explore SFDC data
├── 02_pii_analysis.ipynb          # PII pattern analysis
├── 03_embedding_quality.ipynb     # Embedding evaluation
├── 04_search_accuracy.ipynb       # Search precision testing
├── 05_performance_analysis.ipynb  # Performance metrics
└── 06_case_similarity.ipynb       # Similarity analysis
```

## Key Files

### Root Level
- **CLAUDE.md**: Guidance for AI assistants working on the project
- **PROJECT_STRUCTURE.md**: This document
- **README.md**: Project overview and quick start guide
- **requirements.txt**: Python package dependencies
- **setup.py**: Python package installation configuration
- **pyproject.toml**: Modern Python project metadata
- **.gitignore**: Files to exclude from version control
- **.env.example**: Environment variable template

### Data Files
- **data/case-fields-mapping.json**: Complete field mappings with 5 test datasets
- **data/sample.txt**: Original field mapping source data

### Documentation
- **docs/project-flow-and-architecture.md**: 25 Mermaid diagrams showing system architecture
- **docs/implementation-guide.md**: Practical code patterns and deployment configs
- **CLAUDE.md**: Project context for AI assistants

## Technology Stack

### Core Technologies
- **Vector Database**: Weaviate (HNSW index, cosine similarity)
- **Embeddings**: ChatHPE text-embedding-3-large (3,072 dimensions)
- **Processing**: Apache Airflow + PySpark
- **API Framework**: FastAPI
- **Observability**: Prometheus, Loki, Grafana, Jaeger
- **Infrastructure**: Kubernetes on HPE PC AI
- **Security**: PII removal (Regex + spaCy NER + Microsoft Presidio)

### Languages & Frameworks
- Python 3.10+
- PySpark 3.4+
- FastAPI 0.104+
- Weaviate Python Client

## Performance Targets

| Metric | Target |
|--------|--------|
| Precision at 5 | over 85% |
| Search Latency (p95) | less than 1 second |
| Processing Rate | at least 300 cases/min |
| PII Detection Rate | 100% (zero leakage) |
| Pipeline Success Rate | over 95% |

## Data Sources (4 Core Tables)

1. **Case** (20 fields) - Primary support case data
2. **Task** (2 fields) - Plan of Action and Troubleshooting
3. **WorkOrder** (3 fields) - Onsite actions and resolutions
4. **CaseComments** (1 field) - Additional context and updates

## Phased Deployment

1. **Phase 1 (Week 2-3)**: 1K dev sample - Schema validation
2. **Phase 2 (Week 6)**: 100K validation - GRS team review
3. **Phase 3 (Week 7-8)**: Accuracy tuning - Precision optimization
4. **Phase 4 (Week 9-10)**: Full load - 1M+ historical cases

## Getting Started

1. Review `/docs/README.md` for documentation overview
2. Read `CLAUDE.md` for project context
3. Check `/docs/implementation-guide.md` for code patterns
4. Explore `/data/case-fields-mapping.json` for data structure
5. Review test datasets in `/data/test_datasets/`

---

**Last Updated**: November 12, 2025
**Version**: 1.0
**Status**: Project Structure - Planning Phase
