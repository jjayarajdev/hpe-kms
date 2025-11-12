# Project Structure Changes - JSON Ingestion vs SFDC Extraction

## 🔄 Key Change

**FROM**: Direct SFDC database extraction with PySpark
**TO**: JSON file ingestion from SFDC exports

---

## 📁 Folder Structure Changes

### ✅ What Stays the Same

These folders/files remain **unchanged**:
```
KMS/
├── src/
│   ├── api/                          ✅ No changes
│   │   ├── main.py
│   │   ├── middleware/auth.py
│   │   ├── routes/auth.py
│   │   └── services/search/
│   │       └── hybrid_search_engine.py
│   │
│   ├── pii_removal/                  ✅ No changes
│   │   ├── detectors/
│   │   ├── processors/
│   │   └── validators/
│   │
│   ├── common/                       ✅ No changes
│   │   ├── logging/
│   │   ├── metrics/
│   │   └── config/
│   │
│   └── pipeline/
│       ├── jobs/
│       │   ├── transformation/       ✅ No changes
│       │   │   └── multi_table_joiner.py
│       │   ├── embedding/            ✅ No changes
│       │   │   └── embedding_generator.py
│       │   └── loading/              ✅ No changes
│       │       └── weaviate_loader.py
│       │
│       ├── dags/                     ✅ No changes (content updates only)
│       ├── operators/                ✅ No changes
│       └── sensors/                  ✅ No changes
│
├── tests/                            ✅ No changes
├── config/                           ✅ No changes
├── monitoring/                       ✅ No changes
├── infrastructure/                   ✅ No changes (we use Docker Compose instead)
├── docs/                             ✅ No changes
└── data/                             ⚠️  CHANGES - see below
```

---

## 🔄 What Changes

### 1. **Rename/Repurpose Extraction Module**

#### BEFORE:
```
src/pipeline/jobs/extraction/
└── sfdc_extractor.py    ❌ DELETE or RENAME
```

**Old purpose**: Extract from SFDC database using PySpark
**Technology**: PySpark, JDBC, SQL queries

#### AFTER:
```
src/pipeline/jobs/ingestion/
├── __init__.py          ✅ NEW
├── json_ingester.py     ✅ NEW - Main JSON loader
└── json_validator.py    ✅ NEW - Validate JSON structure
```

**New purpose**: Ingest JSON files from SFDC exports
**Technology**: Python, Pandas, JSON parsing

---

### 2. **Data Folder Structure Changes**

#### BEFORE:
```
data/
├── raw/                           # Empty, data extracted at runtime
├── processed/
├── embeddings/
└── test_datasets/
```

#### AFTER:
```
data/
├── raw/
│   └── sfdc_exports/              ✅ NEW - Receive JSON files here
│       ├── cases.json             ✅ NEW - Case records from SFDC
│       ├── tasks.json             ✅ NEW - Task records from SFDC
│       ├── workorders.json        ✅ NEW - WorkOrder records from SFDC
│       ├── casecomments.json      ✅ NEW - CaseComment records from SFDC
│       │
│       └── archive/               ✅ NEW - Archive processed files
│           ├── 2025-11-12/
│           │   ├── cases.json
│           │   └── ...
│           └── 2025-11-13/
│
├── processed/                     ✅ SAME - Transformed data
│   ├── joined/                    ✅ NEW - After multi-table join
│   ├── pii_clean/                 ✅ NEW - After PII removal
│   └── ready_for_embedding/       ✅ NEW - Ready for embedding
│
├── embeddings/                    ✅ SAME - Generated vectors
│   ├── issue_vectors/
│   └── resolution_vectors/
│
└── test_datasets/                 ✅ SAME - Test data
    └── case-fields-mapping.json
```

---

### 3. **New Scripts**

#### BEFORE:
```
scripts/
├── setup_local.sh                 ✅ EXISTS
└── (no ingestion scripts)
```

#### AFTER:
```
scripts/
├── setup_local.sh                 ✅ EXISTS
├── prepare_sample_json.py         ✅ NEW - Convert test data to JSON
├── ingest_sfdc_json.py            ✅ NEW - Main ingestion script
├── validate_json_structure.py     ✅ NEW - Validate JSON format
└── archive_processed_files.py     ✅ NEW - Move processed JSON to archive
```

---

### 4. **Configuration Changes**

#### `.env` file updates:

**REMOVE** (no longer needed):
```bash
# SFDC Database Connection
SFDC_HOST=your-sfdc-host.salesforce.com
SFDC_USERNAME=your-sfdc-username
SFDC_PASSWORD=your-sfdc-password
SFDC_DATABASE=sfdc_db
```

**ADD**:
```bash
# SFDC JSON Ingestion
SFDC_JSON_INPUT_DIR=data/raw/sfdc_exports
SFDC_JSON_ARCHIVE_DIR=data/raw/sfdc_exports/archive
SFDC_JSON_PROCESSED_DIR=data/processed
JSON_VALIDATION_ENABLED=true
JSON_AUTO_ARCHIVE=true
```

---

## 📊 Complete Updated Structure

### Full Directory Tree:
```
KMS/
├── CLAUDE.md
├── PROJECT_STRUCTURE.md
├── PROJECT_TASKS.md
├── SKELETON_TODO.md
├── LOCAL_SETUP.md
├── LOCAL_DEV_SUMMARY.md
├── CORRECTED_NEXT_TASKS.md        ✅ NEW
├── PROJECT_STRUCTURE_CHANGES.md   ✅ NEW (this file)
│
├── .env.example
├── .env
├── .gitignore
├── requirements.txt
├── docker-compose.yml
├── Dockerfile.api
│
├── src/
│   ├── api/
│   │   ├── main.py
│   │   ├── middleware/
│   │   │   └── auth.py
│   │   ├── routes/
│   │   │   ├── auth.py
│   │   │   └── search.py            ✅ TO CREATE
│   │   ├── services/
│   │   │   ├── search/
│   │   │   │   └── hybrid_search_engine.py
│   │   │   └── cases/
│   │   │       └── case_service.py   ✅ TO CREATE
│   │   ├── models/
│   │   └── schemas/
│   │       └── search_schemas.py     ✅ TO CREATE
│   │
│   ├── pipeline/
│   │   ├── jobs/
│   │   │   ├── ingestion/           ✅ RENAMED from extraction/
│   │   │   │   ├── __init__.py      ✅ NEW
│   │   │   │   ├── json_ingester.py ✅ NEW (replaces sfdc_extractor.py)
│   │   │   │   └── json_validator.py ✅ NEW
│   │   │   │
│   │   │   ├── transformation/
│   │   │   │   └── multi_table_joiner.py ✅ EXISTS
│   │   │   │
│   │   │   ├── embedding/
│   │   │   │   └── embedding_generator.py ✅ EXISTS
│   │   │   │
│   │   │   ├── loading/
│   │   │   │   └── weaviate_loader.py ✅ EXISTS
│   │   │   │
│   │   │   └── reconciliation/
│   │   │       └── reconciliation_engine.py ✅ TO CREATE
│   │   │
│   │   ├── dags/
│   │   │   ├── case_processing_dag.py ✅ TO CREATE (updated flow)
│   │   │   ├── incremental_update_dag.py ✅ TO CREATE
│   │   │   └── reconciliation_dag.py ✅ TO CREATE
│   │   │
│   │   ├── operators/
│   │   │   ├── json_ingestion_operator.py ✅ NEW
│   │   │   ├── pii_removal_operator.py ✅ TO CREATE
│   │   │   └── embedding_operator.py ✅ TO CREATE
│   │   │
│   │   └── utils/
│   │       └── file_utils.py        ✅ NEW
│   │
│   ├── pii_removal/
│   │   ├── detectors/
│   │   │   ├── regex_detector.py    ✅ EXISTS
│   │   │   ├── ner_detector.py      ✅ EXISTS
│   │   │   └── presidio_detector.py ✅ EXISTS
│   │   ├── processors/
│   │   │   └── pii_remover.py       ✅ EXISTS
│   │   └── validators/
│   │       └── leakage_validator.py ✅ TO CREATE
│   │
│   └── common/
│       ├── logging/
│       ├── metrics/
│       ├── config/
│       ├── exceptions/
│       └── utils/
│
├── data/
│   ├── raw/
│   │   └── sfdc_exports/            ✅ NEW
│   │       ├── cases.json           ✅ NEW - Receive from SFDC
│   │       ├── tasks.json           ✅ NEW - Receive from SFDC
│   │       ├── workorders.json      ✅ NEW - Receive from SFDC
│   │       ├── casecomments.json    ✅ NEW - Receive from SFDC
│   │       └── archive/             ✅ NEW - Processed files
│   │
│   ├── processed/
│   │   ├── joined/                  ✅ NEW
│   │   ├── pii_clean/               ✅ NEW
│   │   └── ready_for_embedding/     ✅ NEW
│   │
│   ├── embeddings/
│   │   ├── issue_vectors/
│   │   └── resolution_vectors/
│   │
│   ├── test_datasets/
│   │   └── case-fields-mapping.json ✅ EXISTS
│   │
│   └── users.db                     ✅ EXISTS (SQLite auth)
│
├── scripts/
│   ├── setup_local.sh               ✅ EXISTS
│   ├── prepare_sample_json.py       ✅ NEW
│   ├── ingest_sfdc_json.py          ✅ NEW
│   ├── validate_json_structure.py   ✅ NEW
│   └── archive_processed_files.py   ✅ NEW
│
├── tests/
│   ├── unit/
│   │   ├── pipeline/
│   │   │   ├── test_json_ingester.py ✅ NEW (replaces test_sfdc_extractor.py)
│   │   │   └── test_multi_table_joiner.py
│   │   ├── api/
│   │   └── pii_removal/
│   │
│   ├── integration/
│   │   ├── search/
│   │   ├── embedding/
│   │   └── pipeline/
│   │       └── test_json_to_weaviate.py ✅ NEW
│   │
│   └── e2e/
│       ├── scenarios/
│       └── fixtures/
│
├── config/
│   ├── airflow/
│   ├── weaviate/
│   ├── prometheus/
│   └── grafana/
│
├── monitoring/
│   ├── prometheus/
│   ├── grafana/
│   ├── loki/
│   └── jaeger/
│
├── infrastructure/
│   └── (docker-compose only for local dev)
│
├── docs/
│   ├── README.md
│   ├── project-flow-and-architecture.md
│   └── implementation-guide.md
│
├── notebooks/
│   └── (analysis notebooks)
│
├── logs/
│   └── (application logs)
│
└── reference_docs/
    └── (planning documents)
```

---

## 🔄 Updated Data Flow

### Before (Incorrect):
```
SFDC Database
    ↓ (PySpark JDBC)
Extract with SQL queries
    ↓
Transform
    ↓
PII Removal
    ↓
Embedding
    ↓
Weaviate
```

### After (Correct):
```
SFDC System
    ↓ (Export/API)
JSON Files (4 files)
    ↓
📁 data/raw/sfdc_exports/
    ├── cases.json
    ├── tasks.json
    ├── workorders.json
    └── casecomments.json
    ↓
JSON Ingester (Python/Pandas)
    ↓
Multi-Table Join
    ↓
PII Removal
    ↓
Text Concatenation (Issue + Resolution)
    ↓
Embedding Generation (ChatHPE)
    ↓
Weaviate Storage
    ↓
Search API
```

---

## 📝 Files to Create/Update

### ✅ New Files to Create:
```
src/pipeline/jobs/ingestion/
├── __init__.py
├── json_ingester.py              ← Main JSON loader
└── json_validator.py             ← Validate JSON structure

scripts/
├── prepare_sample_json.py        ← Convert test data to JSON
├── ingest_sfdc_json.py           ← CLI for ingestion
├── validate_json_structure.py    ← Validate JSON files
└── archive_processed_files.py    ← Archive processed files

tests/unit/pipeline/
└── test_json_ingester.py         ← Test JSON ingestion
```

### 🔄 Files to Update:
```
PROJECT_TASKS.md                  ← Update Task 2.1 (Extraction → Ingestion)
SKELETON_TODO.md                  ← Update references
.env.example                      ← Remove SFDC DB config, add JSON config
docker-compose.yml                ← No PySpark needed (can remove if not used elsewhere)
requirements.txt                  ← Remove pyspark if not needed
```

### ❌ Files to Delete/Archive:
```
src/pipeline/jobs/extraction/sfdc_extractor.py  ← Delete or move to archive/
```

---

## 🎯 Migration Steps

### Step 1: Create New Structure
```bash
# Create new directories
mkdir -p data/raw/sfdc_exports/archive
mkdir -p data/processed/{joined,pii_clean,ready_for_embedding}
mkdir -p src/pipeline/jobs/ingestion

# Create __init__.py
touch src/pipeline/jobs/ingestion/__init__.py
```

### Step 2: Move/Rename Files
```bash
# Archive old extraction module
mkdir -p archive/old_extraction
mv src/pipeline/jobs/extraction/sfdc_extractor.py archive/old_extraction/

# Or just rename the directory
mv src/pipeline/jobs/extraction src/pipeline/jobs/ingestion
```

### Step 3: Create New Files
```bash
# Create JSON ingestion files
touch src/pipeline/jobs/ingestion/json_ingester.py
touch src/pipeline/jobs/ingestion/json_validator.py

# Create utility scripts
touch scripts/prepare_sample_json.py
touch scripts/ingest_sfdc_json.py
```

### Step 4: Update Configuration
```bash
# Update .env file
# Remove SFDC database config
# Add JSON ingestion config
```

---

## 🔍 Key Differences Summary

| Aspect | Before (SFDC Extraction) | After (JSON Ingestion) |
|--------|-------------------------|------------------------|
| **Data Source** | SFDC Database (direct) | JSON files (exported) |
| **Technology** | PySpark + JDBC | Python + Pandas |
| **Connection** | Database connection required | File system access only |
| **Module Name** | `extraction/sfdc_extractor.py` | `ingestion/json_ingester.py` |
| **Dependencies** | PySpark, JDBC driver | Standard Python (json, pandas) |
| **Input** | SQL queries | JSON files |
| **Data Location** | Runtime extraction | `data/raw/sfdc_exports/` |
| **Scalability** | PySpark distributed | Single-node Python (sufficient for daily batches) |

---

## 📊 Impact on Other Components

### ✅ No Impact:
- API service (unchanged)
- PII removal (unchanged)
- Embedding generation (unchanged)
- Weaviate loading (unchanged)
- Authentication (unchanged)
- Monitoring (unchanged)

### ⚠️ Minor Updates Needed:
- **Airflow DAGs**: Update first task from "Extract" to "Ingest JSON"
- **Documentation**: Update references from extraction to ingestion
- **Tests**: Create tests for JSON ingestion instead of database extraction

---

## 🚀 What This Means for You

### Simplifications:
1. ✅ **No PySpark needed** for ingestion (can still use for transformation if needed)
2. ✅ **No database connections** to manage
3. ✅ **Simpler deployment** - just need file system access
4. ✅ **Easier testing** - use sample JSON files
5. ✅ **Lower resource requirements** - no Spark cluster needed for ingestion

### New Requirements:
1. ⚠️ **Need to receive JSON files** from SFDC regularly
2. ⚠️ **Need file storage** for JSON files
3. ⚠️ **Need archive strategy** for processed files

---

## 📋 Next Actions

1. **Confirm JSON format** you receive from SFDC
2. **Create sample JSON files** from test data
3. **Implement JSON ingester**
4. **Test ingestion → transformation → loading** pipeline
5. **Update documentation**

---

**Ready to proceed?** The structural changes are minimal - mainly renaming `extraction` to `ingestion` and creating JSON loading scripts! 🚀

**Last Updated**: November 12, 2025
