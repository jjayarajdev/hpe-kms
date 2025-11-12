# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**KMS 2.5 - Vector Search Implementation**
- **Client**: HPE (Hewlett Packard Enterprise)
- **Vendor**: Algoleap Technologies
- **Purpose**: Data Transformation & LLM Enrichment for Semantic Historical Case Search using Weaviate Vector Database
- **Timeline**: 12 weeks (~$93,725 USD)
- **Date**: November 2025

This repository contains comprehensive technical planning documentation for implementing a semantic search system over HPE's historical support cases using vector embeddings and hybrid search.

## Repository Structure

```
/reference_docs/
├── 00_Technical_Planning_Index.md           # Master index and overview
├── 01_Text_Field_Embedding_Strategy.md      # Multi-table text concatenation & embedding
├── 02_Hybrid_Search_Strategy.md             # Vector + metadata filtering
├── 03_Quality_Verification_Early_Phases.md  # Testing & validation approach
├── 04_Reconciliation_Processes_*.md         # Data consistency & recovery
├── 05_PII_Data_Handling_*.md                # PII removal & encryption
├── 06_Logging_Alerting_Prometheus.md        # Observability stack
├── 07_Early_Sample_Data_Load_*.md           # Phased data loading
├── 08_Metadata_Filter_Creation.md           # Metadata enrichment
├── 09_Metadata_Creation_Algorithms.md       # Algorithmic metadata generation
└── KMS_2.6.pdf                              # Latest proposal document
```

## Architecture Overview

### Data Pipeline Flow

```
SFDC (6 Tables) → Staging Layer → Multi-Table JOIN (44 fields)
    → PII Removal → Embedding Generation → Weaviate Vector DB
```

### Technology Stack

- **Vector Database**: Weaviate with HNSW indexing, cosine similarity
- **Embedding Model**: ChatHPE text-embedding-3-large (3,072 dimensions) with Nomic fallback
- **Orchestration**: Apache Airflow for DAG management
- **Processing**: PySpark for distributed data transformation
- **Observability**: Prometheus (metrics), Loki (logs), Grafana (dashboards), Jaeger (tracing)
- **Authentication**: OIDC/Keycloak with RBAC
- **Infrastructure**: Kubernetes on PC AI
- **Reconciliation DB**: PostgreSQL for data lineage tracking

### Six Source SFDC Tables (44 Total Fields)

1. **Case** (21 fields) - Primary table with issue/resolution details
2. **Task** (2 fields) - Plan of Action, Troubleshooting steps
3. **WorkOrder** (3 fields) - Field engineer summaries, onsite actions
4. **CaseComments** (1 field) - Engineer comments
5. **WorkOrderFeed** (2 fields) - Feed updates
6. **EmailMessage** (2 fields) - Email communications

## Key Architecture Patterns

### Multi-Table Text Concatenation Strategy

The system creates a **composite semantic representation** by joining 44 fields from 6 SFDC tables with structured delimiters. This approach prioritizes:
- Single vector per case (not multi-vector)
- Weighted field importance (case details > comments)
- Structured sections: CASE ID → ISSUE → RESOLUTION → ACTIONS → COMMUNICATIONS

### Hybrid Search Implementation

Combines two approaches:
1. **Semantic Search**: Vector similarity using HNSW approximate nearest neighbor
2. **Metadata Filtering**: Structured filters on product, error codes, dates, categories

Critical filterable metadata fields:
- `productNumber`, `productLine`, `productSeries`, `productHierarchy`
- `errorCodes` (e.g., "iLO_400_MemoryErrors", "218004")
- `issueType`, `resolutionCode`, `rootCause`
- `status`, `priority`, `createdDate`, `closedDate`

### PII Removal Pipeline

Multi-stage detection and removal (ZERO PII in Weaviate):
1. **Regex patterns**: Email, phone, IP addresses, SSNs
2. **Named Entity Recognition**: spaCy for person/organization names
3. **Microsoft Presidio**: Additional PII detection
4. **Custom HPE patterns**: HPE-specific identifiers

**High-risk tables for PII**:
- EmailMessage (CRITICAL - contains signatures, contact info)
- CaseComments (HIGH - engineer discussions)
- WorkOrder (HIGH - customer site addresses)

### Reconciliation & Idempotency

**Four-layer reconciliation strategy**:
1. **Source → Staging**: Track all SFDC table loads
2. **Staging → Transformation**: Monitor multi-table join completeness
3. **Transformation → Embedding**: Validate PII removal and embedding generation
4. **Embedding → Weaviate**: Ensure vector DB load success

PostgreSQL reconciliation DB tracks data lineage with checksums for idempotent reprocessing.

### Quality Verification Phases

**Phase 1 (Week 2-3)**: 1K dev sample
- Schema validation
- Mock API for frontend development
- Initial search testing

**Phase 2 (Week 6)**: 100K validation sample
- GRS team human-in-the-loop evaluation
- Golden query set (50 test queries)
- Precision@K metrics (P@1, P@3, P@5, P@10)
- Performance testing (latency <1s p95)

**Phase 3 (Week 7-8)**: Accuracy tuning
- Hyperparameter optimization (alpha, ef, thresholds)
- NDCG and MRR calculations
- Regression testing

**Phase 4 (Week 9-10)**: Full historical load (1M+ cases)

## Key Performance Targets

| Metric | Target | Reference |
|--------|--------|-----------|
| Precision@5 | >85% | Section 03 |
| Search Latency (p95) | <1 second | Section 03, 07 |
| Processing Rate | ≥300 cases/min | Section 04, 06 |
| PII Detection Rate | 100% (zero leakage) | Section 05 |
| Pipeline Success Rate | >95% | Section 04, 06 |
| Embedding Dimensions | 3,072 (ChatHPE) | Section 01 |
| Vector Similarity | Cosine similarity >0.7 threshold | Section 02 |

## Documentation Conventions

### Reading the Documentation

1. **Start with**: `00_Technical_Planning_Index.md` for complete overview
2. **For implementation details**: Read the full-length documents (not summaries)
3. **Code examples**: All Python, SQL, YAML examples in docs are production-ready templates
4. **Cross-references**: Each section links to related sections

### Document Naming Pattern

- `0X_Topic_Name.md` - Full detailed documentation
- `0X_Topic_Name_Summary.md` - Executive summary (when available)

### Key Questions Answered

Each section addresses specific Solution Architect concerns:
- Section 01: Multiple text field embedding strategy
- Section 02: Hybrid search with metadata filters
- Section 03: Early-phase quality verification
- Section 04: Reconciliation for data errors/outages
- Section 05: PII removal and encryption
- Section 06: Logging and alerting (Prometheus)
- Section 07: Phased sample data loading

## Working with This Repository

### Common Tasks

**Review architecture decisions**:
```bash
# Read the master index first
cat reference_docs/00_Technical_Planning_Index.md

# Then dive into specific sections
cat reference_docs/01_Text_Field_Embedding_Strategy.md
```

**Understand data flow**:
- Start with Section 01 (embedding strategy)
- Then Section 04 (reconciliation architecture)
- Finally Section 02 (search implementation)

**Review observability setup**:
```bash
cat reference_docs/06_Logging_Alerting_Prometheus.md
# Contains Prometheus metrics definitions, Grafana dashboards, alert rules
```

**Check PII handling**:
```bash
cat reference_docs/05_PII_Data_Handling_Removal_Encryption.md
# Critical for compliance - all PII removal patterns documented
```

### Important Technical Constraints

1. **No code implementation exists yet** - This is planning documentation only
2. **All Python/SQL examples** are design templates, not running code
3. **Multi-table complexity**: Must handle 6 SFDC tables with varying join completeness (30-80%)
4. **PII is critical**: Zero-tolerance policy for PII in vector database
5. **Idempotency required**: All pipeline stages must be safely reprocessable
6. **Phased approach**: 1K → 100K → 1M+ progressive data loading

### Search Strategy Context

When discussing search implementation, note:
- **Single vector per case** (not multi-vector) with composite text
- **Hybrid search** always combines vector + metadata filters
- **Fallback strategy**: If filtered search returns <N results, expand filters
- **Error code matching**: Critical for technical troubleshooting scenarios
- **Product hierarchy**: Supports both specific products and product families

### Data Quality Metrics

All quality metrics align with industry standards:
- **Precision@K**: Percentage of relevant results in top K
- **NDCG**: Normalized Discounted Cumulative Gain for ranking quality
- **MRR**: Mean Reciprocal Rank for first relevant result
- **Human evaluation**: GRS team validates search relevance

## Development Workflow (When Implementation Begins)

### Phase 1: Schema & API Setup (Week 2-3)
- Load 1K stratified sample to Weaviate
- Validate schema with all 44 fields
- Create mock search API for frontend development
- Initial precision testing with golden queries

### Phase 2: Validation (Week 6)
- Load 100K representative sample
- GRS team human-in-the-loop evaluation
- Performance testing (concurrent users, latency)
- Hyperparameter tuning

### Phase 3: Production Readiness (Week 7-8)
- Regression testing with golden query set
- A/B testing framework
- Monitoring dashboards (Grafana)
- Alert rule configuration

### Phase 4: Full Load (Week 9-10)
- Incremental daily batch processing
- Reconciliation validation
- Production deployment preparation

## Critical Success Factors

1. **PII removal must be perfect** - Zero leakage to vector DB
2. **Join completeness tracking** - Not all cases have tasks/workorders/comments
3. **Search quality validation** - GRS team must validate relevance
4. **Performance targets** - <1s latency at p95 with 100K+ cases
5. **Idempotent pipelines** - Safe reprocessing for reconciliation
6. **Metadata enrichment** - Product families, category hierarchies critical for filtering

## References

- **Proposal**: `reference_docs/KMS_2.6.pdf`
- **Master Index**: `reference_docs/00_Technical_Planning_Index.md`
- **All sections**: Comprehensive technical details with code examples
- **Client**: HPE Global Response Center (GRS) team
- **Solution Architect**: Jay (HPE)
