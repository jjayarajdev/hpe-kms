# KMS 2.5 Skeleton Code - TODO Checklist

This document maps skeleton code files to specific tasks from PROJECT_TASKS.md and provides implementation guidance based on `data/case-fields-mapping.json` test data structure.

**Test Data Reference**: `/data/case-fields-mapping.json`
- 5 test datasets covering: DIMM failure, tape drive failure, HDD failure, 3PAR false alarm, order processing
- 26 fields from 4 core tables (Case, Task, WorkOrder, CaseComments)
- Separate Issue and Resolution vectors

---

## Phase 1: Foundation & Setup (Week 1-2)

### ✅ Task 1.1-1.2: Infrastructure Setup
**Status**: Directory structure created
**Location**: `/infrastructure/`

**TODO**:
- [ ] `infrastructure/terraform/modules/weaviate.tf` - Weaviate cluster (32GB RAM, 8 vCPUs)
- [ ] `infrastructure/terraform/modules/airflow.tf` - Airflow cluster (16GB RAM, 4 vCPUs)
- [ ] `infrastructure/terraform/modules/api.tf` - API service (8GB RAM, 2 vCPUs)
- [ ] `infrastructure/kubernetes/base/weaviate-deployment.yaml`
- [ ] `infrastructure/kubernetes/base/airflow-deployment.yaml`
- [ ] `infrastructure/kubernetes/base/api-deployment.yaml`

### ✅ Task 1.3: Weaviate Setup
**Status**: Skeleton created
**Location**: `src/pipeline/jobs/loading/weaviate_loader.py`

**Schema Definition** (Based on case-fields-mapping.json):
- [ ] Complete `create_schema()` method with all 26 fields
- [ ] Configure HNSW index: efConstruction=256, maxConnections=64, distance=cosine
- [ ] Implement dual vector support (Issue + Resolution, 3,072 dims each)
- [ ] Test schema creation with 5 test datasets

**Test Data Mapping**:
```
Case Fields (20):
- Core: caseId, caseNumber, subject, description
- Issue: causeText, issueText, issueType, environment
- Resolution: resolutionText, resolutionCode, rootCause
- Metadata: productLine, productNumber, productSeries, errorCodes, closeComments, parentId

Task Fields (2):
- taskType, taskDescription, taskSubject

WorkOrder Fields (3):
- closingSummary, onsiteAction, problemDescription

CaseComments Field (1):
- commentBody
```

### ✅ Task 1.4: Airflow Setup
**Status**: Directory structure created
**Location**: `src/pipeline/dags/`

**TODO**:
- [ ] `config/airflow/airflow.cfg` - Airflow configuration with KubernetesExecutor
- [ ] `config/airflow/connections/sfdc_connection.json`
- [ ] `config/airflow/connections/weaviate_connection.json`
- [ ] `config/airflow/connections/chathpe_connection.json`

### ✅ Task 1.5: Monitoring Setup
**Status**: Directory structure created
**Location**: `monitoring/`

**TODO**:
- [ ] `monitoring/prometheus/prometheus.yml` - Scrape configuration
- [ ] `monitoring/prometheus/rules/pipeline_alerts.yml` - Pipeline failure alerts
- [ ] `monitoring/prometheus/rules/search_alerts.yml` - Search latency alerts (p95 < 1s)
- [ ] `monitoring/prometheus/rules/pii_alerts.yml` - PII leakage alerts (zero tolerance)
- [ ] `monitoring/grafana/dashboards/pipeline_health.json`
- [ ] `monitoring/grafana/dashboards/search_performance.json`
- [ ] `monitoring/grafana/dashboards/pii_compliance.json`
- [ ] `monitoring/grafana/dashboards/resource_utilization.json`

---

## Phase 2: Data Pipeline Development (Week 3-4)

### ✅ Task 2.1: SFDC Data Extraction
**Status**: Skeleton created ✓
**Location**: `src/pipeline/jobs/extraction/sfdc_extractor.py`

**Implementation TODO**:
- [ ] Implement `extract_case_data()` - Extract 20 Case fields
- [ ] Implement `extract_task_data()` - Extract 2 Task fields (filter: Type IN ('Plan of Action', 'Trouble Shooting'))
- [ ] Implement `extract_workorder_data()` - Extract 3 WorkOrder fields
- [ ] Implement `extract_casecomment_data()` - Extract 1 CaseComments field
- [ ] Add CDC (Change Data Capture) logic for incremental extraction
- [ ] Implement data quality checks at extraction
- [ ] Add error handling with circuit breaker pattern
- [ ] Save to staging in Parquet format with partitioning
- [ ] Add extraction metrics (Prometheus)

**Test with**: All 5 test datasets from `case-fields-mapping.json`

**Dependencies**: None

---

### ✅ Task 2.2: Multi-Table Transformation
**Status**: Skeleton created ✓
**Location**: `src/pipeline/jobs/transformation/multi_table_joiner.py`

**Implementation TODO** (Based on case-fields-mapping.json structure):

**1. Multi-Table Joins**:
- [ ] Case LEFT JOIN Task ON Case.Id = Task.WhatId
- [ ] Case LEFT JOIN WorkOrder ON Case.Id = WorkOrder.CaseId
- [ ] Case LEFT JOIN CaseComments ON Case.Id = CaseComments.ParentId
- [ ] Aggregate multiple Tasks per Case (concatenate with delimiter)
- [ ] Aggregate multiple WorkOrders per Case
- [ ] Aggregate multiple CaseComments per Case

**2. Issue Text Creation** (response_type='Issue' from mapping):
- [ ] Concatenate: Subject + Description + Cause_Plain_Text__c + Issue_Plain_Text__c + GSD_Environment_Plain_Text__c
- [ ] Handle NULL values (replace with empty string)
- [ ] Add delimiter between fields (e.g., " | ")

**3. Resolution Text Creation** (response_type='Resolution' from mapping):
- [ ] Concatenate Case resolution fields: Case_Resolution_Summary__c + Resolution__c + Resolution_Plain_Text__c + Root_Cause__c
- [ ] Add Task fields: Task.Description + Task.Subject
- [ ] Add WorkOrder fields: Closing_Summary__c + Onsite_Action__c + Problem_Description__c
- [ ] Add CaseComments: CommentBody (aggregated)
- [ ] Strip HTML tags from Resolution__c fields (e.g., `<p>DIMM replaced</p>` → `DIMM replaced`)

**4. Data Cleaning**:
- [ ] Remove HTML tags using regex or BeautifulSoup
- [ ] Handle empty strings and NULL values
- [ ] Validate Issue text not empty
- [ ] Validate Resolution text not empty

**Test Data Examples**:
- Test dataset 1 (DIMM Failure): Verify all Issue/Resolution fields concatenated correctly
- Test dataset 2 (Tape Drive): Verify WorkOrder fields included
- Test dataset 3 (HDD Failure): Verify Task description included
- Test dataset 4 (False Alarm): Verify CaseComments included
- Test dataset 5 (Order Processing): Verify all fields handled with NULLs

**Dependencies**: Task 2.1 (Extraction)

---

### ✅ Task 2.3: PII Removal Service
**Status**: Skeleton created ✓
**Locations**:
- `src/pii_removal/detectors/regex_detector.py` ✓
- `src/pii_removal/detectors/ner_detector.py` ✓
- `src/pii_removal/detectors/presidio_detector.py` ✓
- `src/pii_removal/processors/pii_remover.py` ✓

**Implementation TODO**:

**1. Regex Detector** (regex_detector.py):
- [ ] Implement email detection (test: `john.doe@hpe.com`)
- [ ] Implement phone detection (test: `555-123-4567`, `+1-555-123-4567`)
- [ ] Implement IPv4 detection (test: `10.20.30.40`)
- [ ] Implement IPv6 detection
- [ ] Implement HPE serial number detection (test: `CZ34278RY2`)
- [ ] Implement credit card detection
- [ ] Implement SSN detection (test: `123-45-6789`)
- [ ] Add unit tests with 100% coverage

**2. NER Detector** (ner_detector.py):
- [ ] Install spaCy: `pip install spacy`
- [ ] Download model: `python -m spacy download en_core_web_sm`
- [ ] Implement `detect()` for PERSON, ORG, GPE, DATE entities
- [ ] Implement `detect_batch()` using spaCy pipe for performance
- [ ] Add unit tests

**3. Presidio Detector** (presidio_detector.py):
- [ ] Install Presidio: `pip install presidio-analyzer presidio-anonymizer`
- [ ] Initialize AnalyzerEngine
- [ ] Implement `detect()` with all entity types
- [ ] Create custom recognizer for HPE-specific patterns
- [ ] Add confidence thresholding

**4. PII Remover** (pii_remover.py):
- [ ] Implement `detect_all_pii()` - Run all 3 layers
- [ ] Implement `_merge_detections()` - Deduplicate overlapping detections
- [ ] Implement `remove_pii()` - Replace PII with `[REDACTED]` token
- [ ] Implement `remove_pii_batch()` - Process ≥ 300 cases/minute
- [ ] Add validation layer (zero leakage check)

**5. Validators**:
- [ ] `src/pii_removal/validators/leakage_validator.py` - Zero leakage verification
- [ ] Scan output text for any remaining PII patterns
- [ ] Generate PII compliance report

**Test with case-fields-mapping.json examples**:
- Extract text fields with potential PII
- Test with: emails in comments, IPs in environment fields, serial numbers in descriptions
- Verify 100% detection rate, zero false negatives

**Performance Target**: ≥ 300 cases/minute

**Dependencies**: Task 2.2 (Transformation)

---

### ✅ Task 2.4: Text Embedding Service
**Status**: Skeleton created ✓
**Location**: `src/pipeline/jobs/embedding/embedding_generator.py`

**Implementation TODO**:

**1. ChatHPE API Integration**:
- [ ] Set up API connection with authentication
- [ ] Implement `generate_embedding()` for single text
- [ ] Implement `generate_embeddings_batch()` with batch_size=100
- [ ] Configure model: `text-embedding-3-large`, dimensions=3,072

**2. Issue and Resolution Embeddings** (KEY REQUIREMENT):
- [ ] Implement `generate_issue_resolution_embeddings()` - Generate SEPARATE vectors
- [ ] Issue vector: From Issue text (Subject + Description + Cause + Issue + Environment)
- [ ] Resolution vector: From Resolution text (All resolution-related fields)
- [ ] Validate both vectors are 3,072 dimensions

**3. Performance Optimization**:
- [ ] Implement retry logic with exponential backoff
- [ ] Add rate limiting to respect API limits
- [ ] Implement caching for duplicate texts (using hash as key)
- [ ] Add batch processing with parallel requests

**4. Quality Checks**:
- [ ] Validate vector dimensions (must be 3,072)
- [ ] Check for NaN/Inf values
- [ ] Validate non-zero magnitude
- [ ] Optional: Normalize vectors

**5. Metrics**:
- [ ] Track embedding generation rate (embeddings/second)
- [ ] Track API latency
- [ ] Track error rate
- [ ] Export Prometheus metrics

**Test Data**:
- Use Issue and Resolution texts from all 5 test datasets
- Verify separate vectors generated correctly
- Test batch processing performance

**Dependencies**: Task 2.3 (PII Removal)

---

### ✅ Task 2.5: Weaviate Loading Service
**Status**: Skeleton created ✓
**Location**: `src/pipeline/jobs/loading/weaviate_loader.py`

**Implementation TODO**:

**1. Schema Creation** (Based on case-fields-mapping.json):
- [ ] Complete `create_schema()` with all 26 fields
- [ ] Configure dual vector support:
  - `issue_vector`: Named vector for Issue (3,072 dims)
  - `resolution_vector`: Named vector for Resolution (3,072 dims)
- [ ] Set HNSW config: efConstruction=256, maxConnections=64, distance=cosine

**2. Data Loading**:
- [ ] Implement `load_case()` - Single case loading with both vectors
- [ ] Implement `load_batch()` - Batch loading with batch_size=100
- [ ] Add parallel loading optimization
- [ ] Implement checkpointing for resume capability

**3. Upsert Logic** (for incremental updates):
- [ ] Implement `upsert_case()` - Check if exists, update or insert
- [ ] Handle vector updates correctly

**4. Validation**:
- [ ] Validate data before loading
- [ ] Validate vector dimensions
- [ ] Check for required fields

**5. Metrics**:
- [ ] Track objects loaded per minute (target: ≥ 300)
- [ ] Track success/failure rate
- [ ] Track Weaviate storage size
- [ ] Implement `get_collection_stats()`

**Test Data**:
- Load all 5 test datasets
- Verify both Issue and Resolution vectors stored correctly
- Test retrieval and search

**Dependencies**: Task 2.4 (Embedding)

---

### ✅ Task 2.6: Data Reconciliation Service
**Status**: Skeleton needed
**Location**: `src/pipeline/jobs/reconciliation/reconciliation_engine.py`

**TODO - Create Skeleton**:
```python
"""
Data Reconciliation Service

4-Layer Reconciliation:
1. Source count vs Extracted count
2. Extracted vs Transformed count
3. Transformed vs Embedded count
4. Embedded vs Loaded count

Task Reference: Phase 2, Task 2.6
"""

class ReconciliationEngine:
    def __init__(self):
        pass

    def reconcile_layer1(self):
        """Source vs Extracted"""
        pass

    def reconcile_layer2(self):
        """Extracted vs Transformed"""
        pass

    def reconcile_layer3(self):
        """Transformed vs Embedded"""
        pass

    def reconcile_layer4(self):
        """Embedded vs Loaded"""
        pass

    def generate_report(self):
        """Generate reconciliation report"""
        pass

    def automated_recovery(self):
        """Retry failed records"""
        pass
```

**Implementation TODO**:
- [ ] Count records at each stage
- [ ] Detect discrepancies
- [ ] Track failed records
- [ ] Implement automated retry logic
- [ ] Generate reconciliation reports
- [ ] Create Grafana dashboard
- [ ] Set up alerts for discrepancies > 5%

**Dependencies**: Task 2.5 (Loading)

---

### ✅ Task 2.7: Airflow DAG Development
**Status**: Skeleton needed
**Location**: `src/pipeline/dags/`

**TODO - Create DAG Skeletons**:

**1. Main Pipeline DAG** (`case_processing_dag.py`):
```python
"""
Main Case Processing DAG

Workflow:
1. Extract from SFDC (4 tables)
2. Transform (multi-table join)
3. Remove PII
4. Generate embeddings (Issue + Resolution)
5. Load to Weaviate
6. Reconciliation

Task Reference: Phase 2, Task 2.7
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'kms-team',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5)
}

with DAG(
    'case_processing_dag',
    default_args=default_args,
    description='Main pipeline for case processing',
    schedule_interval='@daily',
    catchup=False
) as dag:

    extract_task = PythonOperator(...)
    transform_task = PythonOperator(...)
    pii_removal_task = PythonOperator(...)
    embedding_task = PythonOperator(...)
    loading_task = PythonOperator(...)
    reconciliation_task = PythonOperator(...)

    extract_task >> transform_task >> pii_removal_task >> embedding_task >> loading_task >> reconciliation_task
```

**2. Incremental Update DAG** (`incremental_update_dag.py`):
- [ ] CDC-based extraction
- [ ] Delta processing
- [ ] Upsert to Weaviate

**3. Reconciliation DAG** (`reconciliation_dag.py`):
- [ ] Daily reconciliation checks
- [ ] Automated recovery

**Implementation TODO**:
- [ ] Create custom operators: `src/pipeline/operators/pii_removal_operator.py`
- [ ] Create custom operators: `src/pipeline/operators/embedding_operator.py`
- [ ] Create custom operators: `src/pipeline/operators/weaviate_operator.py`
- [ ] Configure retry policies
- [ ] Set up SLA monitoring
- [ ] Configure alerts on failure
- [ ] Test end-to-end with 1K sample

**Dependencies**: Tasks 2.1-2.6 (All pipeline jobs)

---

## Phase 3: API Development (Week 5-6)

### ✅ Task 3.1: FastAPI Service Setup
**Status**: Skeleton created ✓
**Location**: `src/api/main.py`

**Implementation TODO**:

**1. Middleware**:
- [ ] `src/api/middleware/auth.py` - HPE SSO integration
- [ ] `src/api/middleware/logging.py` - Request/response logging
- [ ] `src/api/middleware/rate_limiting.py` - Rate limiting per user/IP

**2. Configuration**:
- [ ] Load Weaviate connection config
- [ ] Load embedding service config
- [ ] Configure OpenAPI documentation

**3. Health Checks**:
- [ ] `src/api/routes/health.py`:
  ```python
  @router.get("/api/health")
  async def health_check():
      return {"status": "healthy", "version": "2.5.0"}

  @router.get("/api/health/detailed")
  async def detailed_health():
      return {
          "weaviate": check_weaviate_connection(),
          "embedding_service": check_embedding_service(),
          "memory_usage": get_memory_usage()
      }
  ```

**4. Metrics**:
- [ ] Export Prometheus metrics endpoint `/metrics`
- [ ] Track request count, latency, error rate

**Dependencies**: Task 1.3 (Weaviate setup)

---

### ✅ Task 3.2: Hybrid Search Service
**Status**: Skeleton created ✓
**Location**: `src/api/services/search/hybrid_search_engine.py`

**Implementation TODO**:

**1. Vector Search** (Separate Issue and Resolution):
- [ ] Implement `_search_issue_vector()` - Search Issue vectors with cosine similarity
- [ ] Implement `_search_resolution_vector()` - Search Resolution vectors
- [ ] Implement `_combine_results()` - Merge Issue and Resolution results with scoring

**2. Hybrid Search**:
- [ ] Implement `_hybrid_search()` with alpha=0.7 (70% vector, 30% BM25)
- [ ] Generate query embedding
- [ ] Execute Weaviate hybrid query
- [ ] Combine vector and BM25 scores

**3. Metadata Filtering** (Based on case-fields-mapping.json):
- [ ] Implement `_apply_filters()` with support for:
  - `product_line` (e.g., "34", "TI", "3S")
  - `issue_type` (e.g., "Product Non-functional")
  - `resolution_code` (e.g., "Onsite Repair", "Part Shipped")
  - `date_range` (start/end dates)
  - `product_number` (e.g., "815098-B21")

**4. Result Ranking**:
- [ ] Score combination from Issue and Resolution searches
- [ ] Remove duplicates
- [ ] Sort by combined score
- [ ] Implement pagination

**5. Performance**:
- [ ] Optimize query to achieve p95 < 1 second
- [ ] Add result caching for common queries
- [ ] Add metrics: query latency, results count, filter usage

**Test Queries** (From test datasets):
- "DIMM memory failure DL380 Gen10"
- "Tape drive broken MSL6480"
- "Hard drive predictive failure"
- "3PAR storage alert false alarm"
- "Order processing delay"

**Expected Results**:
- Query 1 should return test_dataset_1 (DIMM Failure) as top result
- Query 2 should return test_dataset_2 (Tape Drive Failure)
- etc.

**Dependencies**: Task 3.1 (FastAPI setup)

---

### Task 3.3: Case Retrieval & Similarity Service
**Status**: Skeleton needed
**Location**: `src/api/services/cases/case_service.py`

**TODO - Create Skeleton**:
```python
"""
Case Retrieval and Similarity Service

Task Reference: Phase 3, Task 3.3
"""

class CaseService:
    def get_case_by_id(self, case_id: str):
        """Retrieve case by ID"""
        pass

    def find_similar_cases(self, case_id: str, limit: int = 5):
        """Find similar cases based on Issue vector"""
        pass

    def find_similar_resolutions(self, case_id: str, limit: int = 5):
        """Find cases with similar resolutions"""
        pass

    def recommend_cases(self, filters: dict, limit: int = 10):
        """Recommend cases based on criteria"""
        pass
```

**Implementation TODO**:
- [ ] Implement case retrieval by ID
- [ ] Implement similar cases search (using Issue vector)
- [ ] Implement similar resolutions search (using Resolution vector)
- [ ] Add caching for frequently accessed cases
- [ ] Add metrics

**Dependencies**: Task 3.2 (Search service)

---

### Task 3.4: API Routes Implementation
**Status**: Skeleton needed
**Locations**: `src/api/routes/` and `src/api/schemas/`

**TODO - Create Route Skeletons**:

**1. Search Routes** (`routes/search.py`):
```python
from fastapi import APIRouter, Query
from ..schemas.search_schemas import SearchRequest, SearchResponse

router = APIRouter()

@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Hybrid semantic search

    Example request:
    {
        "query": "DIMM memory failure",
        "search_type": "hybrid",
        "filters": {
            "product_line": "34"
        },
        "limit": 10
    }
    """
    pass

@router.post("/similar")
async def find_similar(case_id: str, limit: int = 5):
    """Find similar cases"""
    pass
```

**2. Case Routes** (`routes/cases.py`):
```python
@router.get("/cases/{case_id}")
async def get_case(case_id: str):
    """Retrieve case by ID"""
    pass
```

**3. Metadata Routes** (`routes/metadata.py`):
```python
@router.get("/filters")
async def get_available_filters():
    """Get available filter values"""
    return {
        "product_lines": ["34", "35", "3S", "TI", "WB"],
        "issue_types": ["Product Non-functional", "Help me/How to", ...],
        "resolution_codes": ["Onsite Repair", "Part Shipped", ...]
    }

@router.get("/stats")
async def get_system_stats():
    """Get system statistics"""
    pass
```

**4. Request/Response Schemas** (`schemas/search_schemas.py`):
```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, List

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query")
    search_type: str = Field("hybrid", description="hybrid, vector, or bm25")
    filters: Optional[Dict] = Field(None, description="Metadata filters")
    limit: int = Field(10, ge=1, le=100)

class SearchResult(BaseModel):
    case_id: str
    case_number: str
    subject: str
    description: str
    score: float
    # ... other fields

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int
    query: str
    search_type: str
```

**Implementation TODO**:
- [ ] Create all route files
- [ ] Create all schema files with Pydantic models
- [ ] Add request validation
- [ ] Add error handling (404, 400, 500)
- [ ] Update OpenAPI documentation
- [ ] Add integration tests

**Dependencies**: Task 3.3 (Case service)

---

### Task 3.5: API Deployment & Testing
**Status**: Skeleton needed
**Locations**: `src/api/Dockerfile`, `infrastructure/kubernetes/`

**TODO - Create Deployment Skeletons**:

**1. Dockerfile** (`src/api/Dockerfile`):
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**2. Kubernetes Deployment** (`infrastructure/kubernetes/base/api-deployment.yaml`):
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kms-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: kms-api
  template:
    metadata:
      labels:
        app: kms-api
    spec:
      containers:
      - name: kms-api
        image: kms-api:2.5.0
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "8Gi"
            cpu: "2"
          limits:
            memory: "8Gi"
            cpu: "2"
        env:
        - name: WEAVIATE_URL
          value: "http://weaviate:8080"
```

**3. Service and Ingress**:
- [ ] `infrastructure/kubernetes/base/api-service.yaml`
- [ ] `infrastructure/kubernetes/base/api-ingress.yaml`

**4. HorizontalPodAutoscaler**:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: kms-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: kms-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

**Implementation TODO**:
- [ ] Build Docker image
- [ ] Push to container registry
- [ ] Deploy to dev environment
- [ ] Run smoke tests
- [ ] Run load tests (Locust or JMeter)
- [ ] Verify monitoring integration
- [ ] Document deployment process

**Dependencies**: Task 3.4 (API routes)

---

## Phase 4: Testing & Quality Assurance (Week 7-8)

### Task 4.1: Unit Test Suite
**Status**: Skeleton needed
**Location**: `tests/unit/`

**TODO - Create Test Skeletons**:

**1. Pipeline Tests** (`tests/unit/pipeline/`):
- [ ] `test_sfdc_extractor.py` - Test extraction from all 4 tables
- [ ] `test_multi_table_joiner.py` - Test joins and text creation
- [ ] `test_embedding_generator.py` - Test Issue/Resolution embeddings
- [ ] `test_weaviate_loader.py` - Test batch loading

**2. PII Tests** (`tests/unit/pii_removal/`):
- [ ] `test_regex_detector.py` - Test all regex patterns with 100% coverage
- [ ] `test_ner_detector.py` - Test entity recognition
- [ ] `test_presidio_detector.py` - Test Presidio detection
- [ ] `test_pii_remover.py` - Test multi-layer removal with test cases

**3. API Tests** (`tests/unit/api/`):
- [ ] `test_hybrid_search.py` - Test all search types
- [ ] `test_case_service.py` - Test case retrieval
- [ ] `test_routes.py` - Test all API endpoints

**Test Data**: Use examples from `case-fields-mapping.json`

**Coverage Target**: 80%+

**Dependencies**: Tasks 2.1-2.7, 3.1-3.4

---

### Task 4.2: Integration Test Suite
**Status**: Skeleton needed
**Location**: `tests/integration/`

**TODO - Create Test Skeletons**:

**1. Search Flow Tests** (`tests/integration/search/`):
```python
def test_end_to_end_search():
    """
    Test: Query → Embedding → Vector Search → Results
    Uses real Weaviate instance
    """
    # 1. Load test data
    # 2. Generate query embedding
    # 3. Execute search
    # 4. Verify results
    pass

def test_hybrid_search_with_filters():
    """Test hybrid search with metadata filters"""
    pass
```

**2. Pipeline Tests** (`tests/integration/pipeline/`):
```python
def test_full_pipeline():
    """
    Test: Extract → Transform → PII → Embed → Load
    Uses test datasets from case-fields-mapping.json
    """
    pass
```

**3. Reconciliation Tests** (`tests/integration/reconciliation/`):
- [ ] Test discrepancy detection
- [ ] Test automated recovery

**Test Data**: Use all 5 test datasets

**Dependencies**: Task 4.1

---

### Task 4.3: End-to-End Test Suite
**Status**: Skeleton needed
**Location**: `tests/e2e/scenarios/`

**TODO - Create E2E Test Scenarios**:

**Scenario 1**: DIMM Failure Search
```python
def test_dimm_failure_search():
    """
    Test searching for DIMM failures
    Expected: test_dataset_1 as top result
    """
    query = "DL380 Gen10 memory health degraded DIMM failure"
    results = api_client.post("/api/v1/search", json={
        "query": query,
        "limit": 5
    })

    assert results.status_code == 200
    assert len(results.json()['results']) > 0
    # Verify test_dataset_1 is in top 5 (Precision@5)
    top_case = results.json()['results'][0]
    assert "DIMM" in top_case['subject']
```

**Scenario 2**: Tape Drive Failure Search
**Scenario 3**: HDD Failure Search
**Scenario 4**: False Alarm Search
**Scenario 5**: Order Processing Search

**Fixtures** (`tests/e2e/fixtures/test_data.py`):
- [ ] Load all 5 test datasets into test Weaviate instance
- [ ] Generate embeddings
- [ ] Provide fixture for API client

**Accuracy Testing**:
- [ ] Calculate Precision@5 for each scenario
- [ ] Target: Precision@5 > 85%

**Dependencies**: Task 4.2

---

### Task 4.4: Performance & Load Testing
**Status**: Skeleton needed
**Location**: `tests/performance/`

**TODO - Create Load Test Skeletons**:

**1. Search Latency Test** (`tests/performance/test_search_latency.py`):
```python
from locust import HttpUser, task, between

class SearchUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def search_cases(self):
        self.client.post("/api/v1/search", json={
            "query": "DIMM memory failure",
            "limit": 10
        })

# Run: locust -f test_search_latency.py --host=http://localhost:8000
# Test with 10, 50, 100 concurrent users
# Target: p95 latency < 1 second
```

**2. Pipeline Throughput Test** (`tests/performance/test_pipeline_throughput.py`):
- [ ] Test processing 1K cases
- [ ] Measure time and calculate cases/minute
- [ ] Target: ≥ 300 cases/minute

**3. Weaviate Performance** (`tests/performance/test_weaviate_performance.py`):
- [ ] Test vector search latency
- [ ] Test batch loading throughput

**Performance Targets**:
- Search latency p95: < 1 second
- Processing rate: ≥ 300 cases/min
- Pipeline success rate: > 95%

**Dependencies**: Task 4.3

---

### Task 4.5: PII Compliance Validation
**Status**: Skeleton needed
**Location**: `tests/unit/pii_removal/test_pii_compliance.py`

**TODO - Create Compliance Tests**:

```python
def test_pii_detection_100_percent():
    """
    Test 100% PII detection with known PII dataset
    Zero tolerance for false negatives
    """
    pii_test_cases = [
        {
            'text': 'Contact john.doe@hpe.com or 555-123-4567',
            'expected_pii_count': 2,
            'expected_types': ['email', 'phone']
        },
        {
            'text': 'Server IP: 10.20.30.40 Serial: CZ34278RY2',
            'expected_pii_count': 2,
            'expected_types': ['ipv4', 'serial_number']
        },
        # Add more test cases
    ]

    remover = PIIRemover()

    for test_case in pii_test_cases:
        detections = remover.detect_all_pii(test_case['text'])
        assert len(detections) == test_case['expected_pii_count']

def test_zero_pii_leakage():
    """
    Verify zero PII leakage in cleaned text
    Test with 100K sample from real data
    """
    pass

def test_false_positive_rate():
    """Test false positive rate < 5%"""
    pass
```

**Compliance Targets**:
- 100% PII detection (zero false negatives)
- Zero PII leakage in output
- False positive rate < 5%

**Dependencies**: Task 2.3 (PII removal)

---

## Phase 5-10: Deployment & Operations

(See PROJECT_TASKS.md for full details)

**Key Tasks**:
- Phase 5: 1K dev sample deployment
- Phase 6: 100K validation sample
- Phase 7: Accuracy tuning (Precision@5 > 85%)
- Phase 8: Full 1M+ production load
- Phase 9: User training and documentation
- Phase 10: Go-live and handover

---

## Configuration Files

### TODO - Create Configuration Skeletons:

**1. Python Dependencies** (`requirements.txt`):
```txt
# Core
fastapi==0.104.1
uvicorn[standard]==0.24.0
pyspark==3.4.1
apache-airflow==2.7.3

# Vector DB
weaviate-client==3.25.0

# NLP & Embeddings
spacy==3.7.2
transformers==4.35.0

# PII Detection
presidio-analyzer==2.2.33
presidio-anonymizer==2.2.33

# Testing
pytest==7.4.3
pytest-cov==4.1.0
locust==2.17.0

# Monitoring
prometheus-client==0.19.0

# Utilities
pydantic==2.5.0
python-dotenv==1.0.0
```

**2. Setup Configuration** (`setup.py`):
```python
from setuptools import setup, find_packages

setup(
    name="kms-vector-search",
    version="2.5.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        # See requirements.txt
    ],
    python_requires=">=3.10",
)
```

**3. Environment Template** (`.env.example`):
```bash
# Weaviate
WEAVIATE_URL=http://localhost:8080
WEAVIATE_API_KEY=your-api-key

# ChatHPE API
CHATHPE_API_ENDPOINT=https://chathpe.api.endpoint
CHATHPE_API_KEY=your-chathpe-api-key

# SFDC
SFDC_HOST=your-sfdc-host
SFDC_USERNAME=your-username
SFDC_PASSWORD=your-password

# Airflow
AIRFLOW__CORE__EXECUTOR=KubernetesExecutor
AIRFLOW__CORE__SQL_ALCHEMY_CONN=postgresql://...

# API
API_HOST=0.0.0.0
API_PORT=8000

# Logging
LOG_LEVEL=INFO
```

**4. Docker Compose** (`docker-compose.yml`) for local development:
```yaml
version: '3.8'

services:
  weaviate:
    image: semitechnologies/weaviate:1.23.0
    ports:
      - "8080:8080"
    environment:
      - PERSISTENCE_DATA_PATH=/var/lib/weaviate

  api:
    build: ./src/api
    ports:
      - "8000:8000"
    depends_on:
      - weaviate
    environment:
      - WEAVIATE_URL=http://weaviate:8080
```

---

## Summary: Implementation Priority

### ✅ COMPLETED (Skeleton Created):
1. Pipeline jobs: extraction, transformation, embedding, loading
2. PII detection: regex, NER, Presidio, remover
3. API: main app, hybrid search engine

### 🚀 HIGH PRIORITY (Create Next):
1. **Reconciliation service** - Phase 2, Task 2.6
2. **Airflow DAGs** - Phase 2, Task 2.7 (blocks pipeline execution)
3. **API routes and schemas** - Phase 3, Task 3.4
4. **Configuration files** - requirements.txt, setup.py, .env.example

### 📋 MEDIUM PRIORITY:
1. **Case service** - Phase 3, Task 3.3
2. **Unit tests** - Phase 4, Task 4.1
3. **Deployment files** - Dockerfile, K8s manifests

### 📊 LOW PRIORITY:
1. **Integration tests** - Phase 4, Task 4.2
2. **E2E tests** - Phase 4, Task 4.3
3. **Load tests** - Phase 4, Task 4.4

---

## Key Implementation Notes

### Data Structure (From case-fields-mapping.json):
- **26 total fields** from 4 core tables
- **Separate vectors**: Issue (3,072 dims) + Resolution (3,072 dims)
- **5 test datasets** covering different scenarios

### Performance Targets:
- Search latency p95: **< 1 second**
- Processing rate: **≥ 300 cases/minute**
- PII detection: **100% (zero leakage)**
- Search accuracy: **Precision@5 > 85%**
- Pipeline success: **> 95%**

### Critical Path:
1. Complete pipeline skeletons → Test with 1K sample
2. Complete API skeletons → Test search functionality
3. Integration testing with 5 test datasets
4. Performance optimization
5. 100K validation
6. Full 1M+ production load

---

**Next Steps**:
1. Implement TODO items in existing skeleton files
2. Create missing skeleton files (reconciliation, DAGs, tests)
3. Test with 5 test datasets from case-fields-mapping.json
4. Iterate based on test results

**Document Version**: 1.0
**Last Updated**: November 12, 2025
**Status**: Development TODO - Ready for Implementation
