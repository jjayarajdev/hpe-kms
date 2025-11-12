# Hybrid Search Strategy & Metadata Creation (KMS 2.6)

**Document Type**: Technical Architecture Guide
**Version**: KMS 2.6
**Last Updated**: November 12, 2025
**Source**: KMS_2.6.pdf (Pages 7, 8, 9, 23, 25, 26)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Hybrid Search Strategy](#hybrid-search-strategy)
   - [Three-Pillar Approach](#three-pillar-approach)
   - [Semantic/Vector Search](#1-semanticvector-search)
   - [Keyword/BM25 Search](#2-keywordbm25-search)
   - [Metadata Filters](#3-metadata-filters)
   - [Fusion Formula (Alpha Parameter)](#fusion-formula-alpha-parameter)
   - [Adaptive Fallback Strategy](#adaptive-fallback-strategy)
3. [Metadata Creation](#metadata-creation)
   - [Direct Metadata](#direct-metadata-from-salesforce)
   - [Enriched Metadata](#enriched-metadata-computed)
   - [Metadata Pipeline Flow](#metadata-pipeline-flow)
   - [Indexing Strategy](#metadata-indexing-strategy)
   - [Validation Rules](#metadata-validation-rules)
4. [Implementation Guidelines](#implementation-guidelines)
5. [Performance Optimization](#performance-optimization)
6. [Examples and Use Cases](#examples-and-use-cases)

---

## Executive Summary

**Hybrid Search** in KMS 2.6 combines three complementary search methods to find semantically similar historical support cases:

1. **Vector/Semantic Search** - Understands meaning and concepts
2. **BM25/Keyword Search** - Finds exact term matches
3. **Metadata Filters** - Narrows results by structured data

**Metadata Creation** involves extracting and enriching case attributes to enable powerful filtering, sorting, and analytics capabilities.

**Key Benefits**:
- ✅ >85% precision@5 (validated by GRS team)
- ✅ Sub-second query response time
- ✅ Graceful degradation with adaptive fallback
- ✅ 17 metadata fields (12 direct + 5 enriched)
- ✅ Context-aware search with smart filtering

---

## Hybrid Search Strategy

### Three-Pillar Approach

```
User Query: "server memory error causing crash during boot"
                              ↓
        ┌──────────────────────┼──────────────────────┐
        ↓                      ↓                      ↓
   SEMANTIC                KEYWORD              METADATA
   (Vector)                (BM25)               (Filters)
        ↓                      ↓                      ↓
   Understands             Finds exact          Narrows by
   MEANING                 TERMS                CONTEXT
        ↓                      ↓                      ↓
        └──────────────────────┴──────────────────────┘
                              ↓
                  Hybrid Score Calculation
                  Score = (α × Semantic) + ((1-α) × Keyword)
                              ↓
                      Top 5 Results
```

---

### 1. Semantic/Vector Search

**Purpose**: Understands concepts and intent, not just words.

**Technical Implementation**:
- **Model**: ChatHPE text-embedding-3-large
- **Dimensions**: 3,072 (high-resolution vectors)
- **Context Window**: 8,192 tokens (~6,000 words)
- **Distance Metric**: Cosine similarity
- **Index Algorithm**: HNSW (Hierarchical Navigable Small World)
- **Target Accuracy**: >85% precision@5

**How It Works**:
```
Query: "server memory error causing crash during boot"
         ↓
ChatHPE Embedding API
         ↓
Query Vector: [0.123, -0.456, 0.789, ... 3,069 more numbers]
         ↓
Weaviate Vector Search (HNSW Index)
         ↓
Compare with ALL case vectors using Cosine Similarity
         ↓
Returns cases with similar MEANING
```

**Example**:
- **Query**: "DIMM error"
- **Finds**:
  - Case #1: "memory failure" ← Different words, same concept
  - Case #2: "RAM malfunction" ← Synonym match
  - Case #3: "system memory issue" ← Related concept
  - Case #4: "volatile storage problem" ← Technical equivalent

**Why Semantic Search is Powerful**:
- **Synonyms**: "crash" = "failure" = "hang" = "freeze"
- **Related Concepts**: "boot" → "POST" → "BIOS initialization"
- **Technical Equivalents**: "DIMM" → "RAM module" → "memory stick"
- **Multilingual**: Supports 100+ languages

**HNSW Index Parameters** (Page 21):
- **ef** (search-time): Controls accuracy/speed tradeoff
- **efConstruction** (index-time): Controls graph connectivity
- Tuned for optimal performance with >85% precision target

---

### 2. Keyword/BM25 Search

**Purpose**: Finds exact term matches, critical for technical identifiers.

**Technical Implementation**:
- **Algorithm**: BM25 (Best Match 25)
- **Ranking**: Based on term frequency + inverse document frequency
- **Index**: Full-text inverted index

**How It Works**:
```
Query: "error code 218004"
         ↓
BM25 Algorithm
         ↓
Tokenize query → Look up inverted index
         ↓
Calculate BM25 score per document
         ↓
Rank by term frequency and rarity
         ↓
Returns cases with EXACT term matches
```

**Example**:
- **Query**: "error code 218004"
- **Finds**:
  - Case #1: "Error 218004 detected during boot" ← Exact match
  - Case #2: "System reported code 218004" ← Exact match
  - Case #3: "Part number 867055-B21" ← Exact product SKU

**When Keyword Search Excels**:
- ✅ Error codes (218004, 3020, etc.)
- ✅ Product numbers (867055-B21, etc.)
- ✅ Serial numbers
- ✅ Case numbers
- ✅ Technical IDs (hostnames, IP patterns)

**Why BM25 vs Simple Term Matching**:
- Accounts for term frequency (how often term appears in document)
- Accounts for document length (normalizes scores)
- Accounts for rarity (rare terms get higher weight)

---

### 3. Metadata Filters

**Purpose**: Narrows results by structured data attributes before search.

**How It Works**:
```
Query: "server memory error" + Filters
         ↓
Pre-filter Weaviate Records:
  - product = "ProLiant DL380"
  - priority = "High"
  - createdDate > "2024-01-01"
  - status = "Closed"
         ↓
Only search within filtered subset (e.g., 5,000 of 1M cases)
         ↓
Apply semantic + keyword search
         ↓
Much faster + more relevant results
```

**Available Filter Dimensions**:

| Filter Type | Examples | Use Case |
|-------------|----------|----------|
| **Product** | ProLiant, Synergy, Aruba, Primera, Nimble | Product-specific searches |
| **Product Family** | ProLiant (all models), Synergy (all models) | Broader product filtering |
| **Priority** | High, Medium, Low, Critical | Urgency-based filtering |
| **Status** | New, In Progress, Closed, Cancelled | Lifecycle filtering |
| **Date Ranges** | createdDate > 2024-01-01, Last 30 days | Temporal filtering |
| **Category** | Hardware > Server > Memory | Hierarchical filtering |
| **Resolution Time** | 0-4h, 4-24h, 1-7d, >7d | Time-to-resolution filtering |
| **Temporal** | Q3 2024, 2023, etc. | Quarterly/yearly analysis |
| **Case Age** | ageInDays > 30 | Stale case detection |

**Indexed Metadata Fields** (Fast Filtering):
- ✅ `caseNumber` (text indexed)
- ✅ `caseId` (text indexed)
- ✅ `accountId` (text indexed)
- ✅ `status` (text indexed)
- ✅ `priority` (text indexed)
- ✅ `product` (text indexed)
- ✅ `createdDate` (dateTime indexed)

---

### Fusion Formula (Alpha Parameter)

**Formula**:
```
Hybrid Score = (α × Semantic Score) + ((1-α) × Keyword Score)

Applied ONLY to records passing metadata filters
```

**Alpha (α) Controls the Balance**:

| Alpha Value | Semantic Weight | Keyword Weight | Best For |
|-------------|-----------------|----------------|----------|
| **0.9** | 90% | 10% | Very conceptual queries ("what causes crashes?") |
| **0.75** | 75% | 25% | **Default** - balanced with semantic preference |
| **0.6** | 60% | 40% | **Fallback** - more balanced approach |
| **0.4** | 40% | 60% | Technical/specific queries ("error 218004") |
| **0.2** | 20% | 80% | Exact match queries (product SKUs) |

**Real Example (α = 0.75)** from KMS 2.6 PDF:

**Query**: "server memory error causing crash during boot"

**Three Different Alpha Strategies**:

1. **Discovery (High Semantic α=0.9)**:
   - **Result**: Case #4592 - "System crash after DIMM replacement - POST error 201"
   - **Why**: High semantic relevance (concept match) despite different words
   - **Match**: DIMM=memory, POST=boot, crash=crash

2. **Balanced (Default α=0.75)**:
   - **Result**: Case #3201 - "Memory error code 3020 causing server boot failure"
   - **Why**: Good balance of semantic meaning AND keyword matches
   - **Match**: Has "memory", "error", "server", "boot" plus conceptual similarity

3. **Precise (Lower α=0.6)**:
   - **Result**: Case #5510 - "Server boot error memory crash log attached"
   - **Why**: More exact keyword matches but potentially less conceptual relevance
   - **Match**: Literal word matches ("server", "boot", "error", "memory", "crash")

**Key Insight**: As alpha decreases, results favor exact keyword matches over conceptual similarities.

---

### Adaptive Fallback Strategy

**The Smart Progressive Search** (Page 25):

KMS 2.6 doesn't just do one search - it **adapts** based on result quality:

```
┌─────────────────────────────────────────────────────────┐
│ STAGE 1: Product-Specific Search                       │
│ ─────────────────────────────────────────────────────── │
│ Filter: product = "ProLiant DL380 Gen10"               │
│ Alpha: 0.75 (favor semantic)                           │
│ Search: Hybrid search within exact product             │
│ ─────────────────────────────────────────────────────── │
│ Results: ≥5 cases? ✓ DONE                              │
│          <5 cases? ↓ CONTINUE TO STAGE 2               │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ STAGE 2: Product Family Search                         │
│ ─────────────────────────────────────────────────────── │
│ Filter: productFamily = "ProLiant" (all models)        │
│ Alpha: 0.75 (still favor semantic)                     │
│ Search: Broader product family search                  │
│ ─────────────────────────────────────────────────────── │
│ Results: ≥5 cases? ✓ DONE                              │
│          <5 cases? ↓ CONTINUE TO STAGE 3               │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ STAGE 3: Open Search (No Product Filter)               │
│ ─────────────────────────────────────────────────────── │
│ Filter: NONE (remove product filter entirely)          │
│ Alpha: 0.6 (more balanced, favor keywords slightly)    │
│ Search: Across all products                            │
│ ─────────────────────────────────────────────────────── │
│ Results: Return top 5 (guaranteed results)             │
└─────────────────────────────────────────────────────────┘
```

**Why This Strategy is Brilliant**:

1. **Prioritizes Relevance**:
   - Exact product match first (most relevant)
   - Then product family (still relevant)
   - Finally open search (less specific but still helpful)

2. **Guarantees Results**:
   - Never returns "0 results"
   - Always provides at least 5 similar cases
   - Graceful degradation

3. **Adjusts Strategy Dynamically**:
   - Changes alpha when broadening scope
   - More keyword weight when less context (Stage 3: α=0.6)
   - Adapts to data availability

4. **User Experience**:
   - Users don't see "no results" message
   - System explains if results are from broader search
   - Transparent about search scope

**Example Flow**:

```
User Query: "memory error on ProLiant DL380 Gen11"
                    ↓
Stage 1: Search "ProLiant DL380 Gen11" → Found 2 cases (< 5)
                    ↓
Stage 2: Search "ProLiant" (all models) → Found 8 cases (≥ 5) ✓ DONE
                    ↓
Returns: Top 5 from 8 ProLiant cases
Message: "Results from ProLiant product family (broadened from DL380 Gen11)"
```

---

## Metadata Creation

### Overview

**Metadata** = Structured attributes about a case that enable:
- ✅ **Filtering** (narrow search space)
- ✅ **Sorting** (by date, priority, resolution time)
- ✅ **Grouping** (by product, category, temporal)
- ✅ **Analytics** (trends, patterns, SLA monitoring)

**Total Metadata Fields**: 17 (12 direct + 5 enriched)

---

### Direct Metadata (from Salesforce)

**Extracted "as-is" from SFDC during Extract step (Step 1):**

| SFDC Field | Weaviate Property | Type | Indexed | Example Value |
|------------|-------------------|------|---------|---------------|
| `CaseNumber` | `caseNumber` | text | ✓ | "5007T000002AbcD" |
| `Id` | `caseId` | text | ✓ | "500XXXXXXXXX" |
| `AccountId` | `accountId` | text | ✓ | "001XXXXXXXXX" |
| `Status` | `status` | text | ✓ | "Closed" |
| `Priority` | `priority` | text | ✓ | "High" |
| `Product__c` | `product` | text | ✓ | "ProLiant DL380 Gen10" |
| `Category__c` | `category` | text | - | "HW - Server - Memory" |
| `CreatedDate` | `createdDate` | dateTime | ✓ | "2024-08-15T09:00:00Z" |
| `ClosedDate` | `closedDate` | dateTime | - | "2024-08-16T11:30:00Z" |
| `Subject` | `title` | text | ✓ | "Server memory error" |
| `Description` | `description` | text (vectorized) | ✓ | [Full description] |
| `Resolution__c` | `resolutionSummary` | text (vectorized) | ✓ | [Full resolution] |

**Extraction Process** (Page 11):
1. Pull JSON from PC AI staging folder
2. Schema validation
3. Direct field mapping with type conversion
4. Quality checks (completeness, consistency)

---

### Enriched Metadata (Computed)

**Created during ChatHPE Cleaning step (Step 3) using 5 transformations:**

#### 1. Product Family Extraction

**Method**: Regex pattern matching

**Purpose**: Enable filtering by product line, not just specific model

**Algorithm**:
```python
# Pseudo-code
patterns = [
    r'ProLiant',
    r'Synergy',
    r'SimpliVity',
    r'Aruba',
    r'Primera',
    r'Nimble'
]

for pattern in patterns:
    if re.search(pattern, product_name):
        product_family = pattern
        break
```

**Example**:
```
Input:  "HPE ProLiant DL380 Gen10"
         ↓ [Regex: /ProLiant/]
Output: productFamily = "ProLiant"
```

**Benefits**:
- Users can filter "all ProLiant cases" without knowing exact model
- Enables product family trends and comparisons
- Graceful fallback in adaptive search (Stage 2)

**Complexity**: O(1) - constant time pattern matching

---

#### 2. Category Normalization

**Method**: Split-map-construct to create hierarchy

**Purpose**: Create structured category hierarchy for drill-down filtering

**Algorithm**:
```python
# Pseudo-code
def normalize_category(raw_category):
    # Split on delimiter
    parts = raw_category.split(' - ')

    # Map abbreviations
    mappings = {
        'HW': 'Hardware',
        'SW': 'Software',
        'NET': 'Network',
        'STOR': 'Storage'
    }

    # Construct hierarchy
    normalized = []
    for part in parts:
        normalized.append(mappings.get(part, part))

    return ' > '.join(normalized)
```

**Example**:
```
Input:  "HW - Server - Memory"
         ↓ [Split → Map → Construct]
Output: categoryHierarchy = "Hardware > Server > Memory"
```

**Benefits**:
- Hierarchical filtering: "Hardware" → "Hardware > Server" → "Hardware > Server > Memory"
- Better UI/UX with drill-down navigation
- Consistent category structure across all cases

**Hierarchy Levels**:
- Level 1: Hardware, Software, Network, Storage
- Level 2: Server, Storage, Networking, Application
- Level 3: Memory, CPU, Disk, NIC, etc.

---

#### 3. Resolution Time Calculation

**Method**: Duration calculation + bucket categorization

**Purpose**: Filter by how quickly cases were resolved

**Algorithm**:
```python
# Pseudo-code
def calculate_resolution_time(created_date, closed_date):
    # Calculate duration in hours
    duration_hours = (closed_date - created_date).total_hours()

    # Assign to bucket
    if duration_hours <= 4:
        bucket = "0-4h"
    elif duration_hours <= 24:
        bucket = "4-24h"
    elif duration_hours <= 168:  # 7 days
        bucket = "1-7d"
    else:
        bucket = ">7d"

    return duration_hours, bucket
```

**Example**:
```
Input:  Created: 2024-08-15 09:00
        Closed:  2024-08-16 11:30
         ↓ [Calculate delta = 26.5 hours → Assign bucket]
Output: resolutionTime = 26.5 hours
        resolutionBucket = "1-7d"
```

**Buckets**:
- **0-4h**: Ultra-fast resolution (immediate fixes)
- **4-24h**: Same-day resolution
- **1-7d**: Weekly resolution
- **>7d**: Extended resolution (complex issues)

**Benefits**:
- Search for "fast resolved" cases to learn quick fixes
- Identify patterns in resolution time
- SLA compliance monitoring
- Learn from fastest resolutions

**Complexity**: O(1) - simple date arithmetic

---

#### 4. Temporal Extraction

**Method**: Quarter and year extraction from createdDate

**Purpose**: Enable temporal analysis and filtering

**Algorithm**:
```python
# Pseudo-code
def extract_temporal(created_date):
    year = created_date.year
    month = created_date.month

    # Calculate quarter
    quarter = (month - 1) // 3 + 1

    return f"Q{quarter} {year}", year
```

**Example**:
```
Input:  createdDate = 2024-08-15
         ↓ [Extract month=8 → Q3, year=2024]
Output: quarter = "Q3 2024"
        year = 2024
```

**Benefits**:
- Temporal filtering: "Show me all Q3 2024 cases"
- Quarterly comparisons: "Q3 2024 vs Q3 2023"
- Seasonal trend analysis
- Business reporting by quarter

**Complexity**: O(1) - simple date field extraction

---

#### 5. Case Age Calculation

**Method**: Days since creation (staleness metric)

**Purpose**: Identify old/stale cases still open

**Algorithm**:
```python
# Pseudo-code
def calculate_case_age(created_date, current_date):
    age_in_days = (current_date - created_date).days
    return age_in_days
```

**Example**:
```
Input:  Created: 2024-08-15
        Current: 2024-11-04
         ↓ [Calculate days = 81]
Output: ageInDays = 81
```

**Benefits**:
- Filter "cases open >30 days" (potential stuck cases)
- Prioritize old cases for review
- SLA compliance checking (e.g., "High priority > 7 days")
- Identify cases needing escalation

**Complexity**: O(1) - simple date arithmetic

---

### Metadata Pipeline Flow

```
┌──────────────────────────────────────────────────────────────┐
│ SFDC Source (Salesforce)                                     │
│ 6 Tables: Case, Task, WorkOrder, CaseComments,              │
│            WorkOrderFeed, EmailMessage                        │
└──────────────────────────┬───────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│ Step 1: EXTRACT (PySpark)                                    │
│ ──────────────────────────────────────────────────────────── │
│ • Pull JSON from PC AI staging folder                       │
│ • Schema validation (44 fields from 6 tables)               │
│ • Direct metadata extraction                                 │
│ ──────────────────────────────────────────────────────────── │
│ Output: 12 direct metadata fields                           │
└──────────────────────────┬───────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│ Step 2: PII REMOVAL (6-Stage Pipeline)                       │
│ ──────────────────────────────────────────────────────────── │
│ • Metadata PRESERVED (not affected by PII removal)          │
│ • Only content fields (description, resolution) cleaned     │
│ • Structured metadata fields remain unchanged               │
└──────────────────────────┬───────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│ Step 3: ChatHPE CLEANING                                     │
│ ──────────────────────────────────────────────────────────── │
│ ⭐ METADATA ENRICHMENT HAPPENS HERE! ⭐                      │
│                                                              │
│ 1. Product Family Extraction (Regex)                        │
│    Input: "HPE ProLiant DL380 Gen10"                        │
│    Output: productFamily = "ProLiant"                       │
│                                                              │
│ 2. Category Normalization (Split-Map-Construct)             │
│    Input: "HW - Server - Memory"                            │
│    Output: categoryHierarchy = "Hardware > Server > Memory" │
│                                                              │
│ 3. Resolution Time Calculation (Duration + Bucket)          │
│    Input: Created/Closed dates                              │
│    Output: resolutionTime = 26.5h, bucket = "1-7d"         │
│                                                              │
│ 4. Temporal Extraction (Quarter/Year)                       │
│    Input: 2024-08-15                                         │
│    Output: quarter = "Q3 2024", year = 2024                 │
│                                                              │
│ 5. Case Age Calculation (Staleness)                         │
│    Input: Created date, Current date                        │
│    Output: ageInDays = 81                                   │
│ ──────────────────────────────────────────────────────────── │
│ Output: +5 enriched metadata fields                         │
└──────────────────────────┬───────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│ Step 4: EMBEDDINGS (ChatHPE API)                             │
│ ──────────────────────────────────────────────────────────── │
│ • Vector generation (content only, not metadata)            │
│ • Metadata not vectorized (remains as structured data)      │
│ • Single composite vector: 3,072 dimensions                 │
└──────────────────────────┬───────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│ Step 5: WEAVIATE LOAD                                        │
│ ──────────────────────────────────────────────────────────── │
│ • Metadata INDEXED (12 direct + 5 enriched = 17 fields)    │
│ • Vector stored for semantic search                         │
│ • Optimized for hybrid search (vector + keyword + filters)  │
└──────────────────────────┬───────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│ Weaviate Vector Database                                     │
│ ──────────────────────────────────────────────────────────── │
│ • Vectors: For semantic search (3,072 dims)                 │
│ • Metadata: For filtering and sorting (17 fields)           │
│ • Both combined in hybrid search                            │
│ • HNSW index for fast vector search                         │
│ • Inverted index for keyword search                         │
│ • B-tree index for metadata filtering                       │
└──────────────────────────────────────────────────────────────┘
```

---

### Metadata Indexing Strategy

**Indexed Fields** (Fast Filtering - Milliseconds):

| Field | Type | Use Case |
|-------|------|----------|
| `caseNumber` | text | Unique case lookup |
| `caseId` | text | SFDC reference lookup |
| `accountId` | text | Customer-specific searches |
| `status` | text | Filter by lifecycle (New, Closed) |
| `priority` | text | Filter by urgency (High, Medium, Low) |
| `product` | text | Product-specific searches |
| `productFamily` | text | Product line filtering |
| `createdDate` | dateTime | Date range filtering |
| `categoryHierarchy` | text | Hierarchical drill-down |

**Non-Indexed Fields** (Stored but Not Optimized):

| Field | Type | Why Not Indexed |
|-------|------|-----------------|
| `closedDate` | dateTime | Rarely used for filtering |
| `resolutionTime` | float | Can be recalculated from dates |
| `description` | text | Vectorized, not keyword-indexed |
| `resolutionSummary` | text | Vectorized, not keyword-indexed |

**Vectorized Fields** (Semantic Search):

| Field | Type | Vector Dims | Use Case |
|-------|------|-------------|----------|
| `title` | text | 3,072 | Subject line semantic search |
| `description` | text | 3,072 | Full description semantic search |
| `resolutionSummary` | text | 3,072 | Solution semantic search |

**Note**: In KMS 2.6, all three vectorized fields are combined into a **single composite vector** (3,072 dims) for 98% cost savings.

**Indexing Performance**:
- **Indexed metadata filtering**: <10ms for 1M cases
- **Vector search (HNSW)**: <100ms for 1M cases
- **Hybrid search (combined)**: <150ms (sub-second target: ✓)

---

### Metadata Validation Rules

#### At Extract (Step 1):
- ✅ **Required Fields Present**: caseId, caseNumber, status, createdDate
- ✅ **Date Format Valid**: ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)
- ✅ **Status Values**: Must be in {New, In Progress, Closed, Cancelled}
- ✅ **Priority Values**: Must be in {Low, Medium, High, Critical}
- ✅ **Data Types**: String, dateTime, int validated

#### At ChatHPE Cleaning (Step 3):
- ✅ **Product Family Extraction**: Must match at least one pattern
- ✅ **Category Hierarchy**: No empty levels, well-formed structure
- ✅ **Resolution Time Valid**: closedDate > createdDate (for closed cases)
- ✅ **Temporal Extraction**: Valid quarter (Q1-Q4) and year (4 digits)
- ✅ **Case Age Positive**: ageInDays ≥ 0

#### At Weaviate Load (Step 5):
- ✅ **All Indexed Fields Present**: No null values in indexed fields
- ✅ **Data Types Match Schema**: Type consistency validation
- ✅ **Required Fields Non-Empty**: caseNumber, caseId, status not blank
- ✅ **Relationships Valid**: accountId exists in system
- ✅ **Vector Dimensions**: Exactly 3,072 dimensions
- ✅ **Vector Magnitude**: Non-zero, no NaN/Inf values

**Error Handling**:
- **Validation Failure** → Case logged as FAILED
- **Alert Sent** → Ops team notified
- **Audit Trail** → Failure reason recorded
- **Retry Logic** → Up to 3 retries with exponential backoff

---

## Implementation Guidelines

### 1. Query Construction

**Basic Hybrid Query**:
```python
# Pseudo-code
query = {
    "text": "server memory error causing crash",
    "vector": generate_embedding("server memory error causing crash"),
    "filters": {
        "product": "ProLiant",
        "priority": "High",
        "status": "Closed"
    },
    "alpha": 0.75,
    "limit": 5
}

results = weaviate.hybrid_search(query)
```

**Adaptive Fallback Query**:
```python
# Stage 1: Product-specific
results = hybrid_search(
    query="memory error",
    filters={"product": "ProLiant DL380 Gen10"},
    alpha=0.75,
    limit=5
)

if len(results) < 5:
    # Stage 2: Product family
    results = hybrid_search(
        query="memory error",
        filters={"productFamily": "ProLiant"},
        alpha=0.75,
        limit=5
    )

if len(results) < 5:
    # Stage 3: Open search
    results = hybrid_search(
        query="memory error",
        filters={},  # No product filter
        alpha=0.6,   # More balanced
        limit=5
    )
```

---

### 2. Metadata Enrichment

**Product Family Extraction**:
```python
import re

def extract_product_family(product_name):
    patterns = {
        r'ProLiant': 'ProLiant',
        r'Synergy': 'Synergy',
        r'SimpliVity': 'SimpliVity',
        r'Aruba': 'Aruba',
        r'Primera': 'Primera',
        r'Nimble': 'Nimble'
    }

    for pattern, family in patterns.items():
        if re.search(pattern, product_name, re.IGNORECASE):
            return family

    return "Unknown"
```

**Category Normalization**:
```python
def normalize_category(raw_category):
    mappings = {
        'HW': 'Hardware',
        'SW': 'Software',
        'NET': 'Network',
        'STOR': 'Storage'
    }

    parts = raw_category.split(' - ')
    normalized = [mappings.get(part, part) for part in parts]

    return ' > '.join(normalized)
```

**Resolution Time Calculation**:
```python
from datetime import datetime

def calculate_resolution_time(created_date, closed_date):
    if not closed_date:
        return None, None

    duration = closed_date - created_date
    hours = duration.total_seconds() / 3600

    if hours <= 4:
        bucket = "0-4h"
    elif hours <= 24:
        bucket = "4-24h"
    elif hours <= 168:  # 7 days
        bucket = "1-7d"
    else:
        bucket = ">7d"

    return hours, bucket
```

---

### 3. Alpha Tuning Guidelines

**Choose Alpha Based on Query Type**:

| Query Type | Example | Recommended Alpha | Reason |
|------------|---------|-------------------|--------|
| **Conceptual** | "what causes server crashes?" | 0.8-0.9 | Need semantic understanding |
| **Technical** | "memory error patterns" | 0.7-0.75 | Balance concepts and terms |
| **Specific** | "error code 218004" | 0.4-0.5 | Need exact matches |
| **Product SKU** | "part 867055-B21" | 0.2-0.3 | Literal match critical |

**A/B Testing Recommendations**:
- Test alpha values in 0.1 increments
- Measure precision@5 for each alpha
- User satisfaction surveys
- Click-through rates on results

---

## Performance Optimization

### 1. Vector Search Optimization

**HNSW Parameter Tuning** (Page 21):
```python
# Weaviate configuration
vector_index_config = {
    "efConstruction": 256,  # Index build quality (higher = better, slower)
    "maxConnections": 64,   # Graph connectivity (higher = better recall)
    "ef": 128              # Search-time accuracy (higher = more accurate, slower)
}
```

**Recommendations**:
- **efConstruction**: 256-512 for production
- **maxConnections**: 32-64 (balances recall vs memory)
- **ef**: 64-128 for sub-second queries

---

### 2. Embedding Generation Optimization

**Batch Processing** (Page 12):
```python
# Batch 100 texts per API call
batch_size = 100
texts = [case1_text, case2_text, ..., case100_text]

embeddings = chathpe_api.embed_batch(
    texts=texts,
    model="text-embedding-3-large",
    dimensions=3072
)

# Reduces API overhead 100x vs individual calls
```

**Target**: ≥300 cases/minute processing

---

### 3. Metadata Filtering Optimization

**Index Strategy**:
- Index frequently filtered fields (product, status, priority, dates)
- Don't index rarely used fields (save memory)
- Use B-tree indexes for range queries (dates)
- Use inverted indexes for categorical fields (status, priority)

**Query Optimization**:
```python
# Good: Pre-filter before vector search
results = weaviate.query \
    .get("Case") \
    .with_where({
        "path": ["product"],
        "operator": "Equal",
        "valueText": "ProLiant"
    }) \
    .with_near_vector(query_vector) \
    .with_limit(5) \
    .do()

# Bad: Vector search all, then filter
# (searches 1M cases unnecessarily)
```

---

## Examples and Use Cases

### Use Case 1: Product-Specific Troubleshooting

**Scenario**: Engineer troubleshooting ProLiant memory issue

**Query**:
```python
query = {
    "text": "server experiencing memory errors during POST",
    "filters": {
        "product": "ProLiant DL380 Gen10",
        "status": "Closed",
        "priority": ["High", "Critical"]
    },
    "alpha": 0.75,
    "limit": 5
}
```

**Result**: 5 closed high-priority ProLiant DL380 cases with similar memory issues

**Value**: Fast resolution based on proven solutions for exact product

---

### Use Case 2: Learning from Quick Wins

**Scenario**: Manager wants to understand fast resolution patterns

**Query**:
```python
query = {
    "text": "boot failure quick fix",
    "filters": {
        "resolutionBucket": "0-4h",
        "status": "Closed"
    },
    "alpha": 0.7,
    "limit": 10
}
```

**Result**: 10 cases resolved in <4 hours with boot failure issues

**Value**: Learn fastest resolution strategies, improve MTTR

---

### Use Case 3: Temporal Trend Analysis

**Scenario**: Product manager analyzing Q3 issues

**Query**:
```python
query = {
    "text": "system crashes",
    "filters": {
        "quarter": "Q3 2024",
        "productFamily": "ProLiant"
    },
    "alpha": 0.75,
    "limit": 20
}
```

**Result**: 20 ProLiant crash cases from Q3 2024

**Value**: Identify seasonal patterns, plan Q4 improvements

---

### Use Case 4: Stale Case Escalation

**Scenario**: Support manager identifying cases needing attention

**Query**:
```python
query = {
    "text": "high priority open cases",
    "filters": {
        "status": "In Progress",
        "priority": ["High", "Critical"],
        "ageInDays": {"$gt": 30}
    },
    "alpha": 0.6,
    "limit": 10
}
```

**Result**: 10 high-priority cases open >30 days

**Value**: Proactive case management, reduce aging cases

---

### Use Case 5: Exact Error Code Lookup

**Scenario**: Engineer has specific error code

**Query**:
```python
query = {
    "text": "error code 218004",
    "filters": {
        "status": "Closed"
    },
    "alpha": 0.3,  # Low alpha = favor keyword match
    "limit": 5
}
```

**Result**: Cases with exact error code 218004

**Value**: Precise error code resolution history

---

## Summary Table: Metadata Fields

| Field | Source | Type | Indexed | Enriched | Use Case |
|-------|--------|------|---------|----------|----------|
| `caseNumber` | SFDC | text | ✓ | - | Unique case lookup |
| `caseId` | SFDC | text | ✓ | - | SFDC reference |
| `accountId` | SFDC | text | ✓ | - | Customer filtering |
| `status` | SFDC | text | ✓ | - | Lifecycle filtering |
| `priority` | SFDC | text | ✓ | - | Urgency filtering |
| `product` | SFDC | text | ✓ | - | Product-specific search |
| `category` | SFDC | text | - | - | Issue categorization |
| `createdDate` | SFDC | dateTime | ✓ | - | Date range filtering |
| `closedDate` | SFDC | dateTime | - | - | Resolution date |
| `title` | SFDC | text (vectorized) | ✓ | - | Subject semantic search |
| `description` | SFDC | text (vectorized) | ✓ | - | Description search |
| `resolutionSummary` | SFDC | text (vectorized) | ✓ | - | Solution search |
| `productFamily` | Computed | text | ✓ | ✓ | Product line filtering |
| `categoryHierarchy` | Computed | text | ✓ | ✓ | Hierarchical drill-down |
| `resolutionTime` | Computed | float | - | ✓ | Duration analysis |
| `resolutionBucket` | Computed | text | ✓ | ✓ | Quick win filtering |
| `quarter` | Computed | text | ✓ | ✓ | Temporal analysis |
| `year` | Computed | int | ✓ | ✓ | Yearly filtering |
| `ageInDays` | Computed | int | ✓ | ✓ | Stale case detection |

**Total**: 19 metadata fields (12 direct + 7 enriched)

---

## Key Takeaways

### 1. **Hybrid Search = Best of Three Worlds**
- Semantic understands meaning
- Keyword catches specifics
- Metadata adds context
- Combined = Perfect search experience

### 2. **Alpha Tuning is Critical**
- High alpha (0.75): Conceptual queries
- Low alpha (0.3): Literal/technical queries
- Adaptive: Changes based on result quality

### 3. **Adaptive Fallback = Guaranteed Results**
- Stage 1: Exact product (α=0.75)
- Stage 2: Product family (α=0.75)
- Stage 3: Open search (α=0.6)
- Never returns "0 results"

### 4. **Metadata Enrichment = 5x Filtering Power**
- 5 enrichment transformations
- Product family → Broader filtering
- Category hierarchy → Drill-down
- Resolution buckets → Learn from fast fixes
- Temporal → Trend analysis
- Age → SLA monitoring

### 5. **Performance Targets Met**
- ✅ Sub-second query response (<150ms)
- ✅ >85% precision@5 (validated)
- ✅ ≥300 cases/minute processing
- ✅ Graceful degradation with fallback

---

## References

- **KMS 2.6 PDF**: Pages 7, 8, 9, 23, 25, 26
- **Related Documents**:
  - `ALL_CRITICAL_CHANGES_COMPLETE.md` - Single composite vector implementation
  - `MIGRATION_COMPLETE.md` - JSON ingestion (6 tables, 44 fields)
  - `KMS_2.6_CRITICAL_CHANGES_COMPLETE.md` - Vector strategy alignment

---

**Document Version**: 1.0
**Last Updated**: November 12, 2025
**Status**: ✅ Complete and Aligned with KMS 2.6 Specification
