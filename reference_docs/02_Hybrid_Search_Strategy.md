# Section 2: Hybrid Search Strategy Using Metadata Filters

## 2.1 Overview

**Hybrid Search Definition**: Combines semantic vector similarity with structured metadata filtering to provide precise, contextually relevant results.

**Architecture**:
```
User Query → [Vector Search] + [Metadata Filters] → Ranked Results
              (Semantic)        (Structured)
```

---

## 2.2 Hybrid Search Components

### 2.2.1 Vector Similarity Search (Semantic Component)

**How it works**:
1. User query is embedded using same model (ChatHPE text-embedding-3-large)
2. Weaviate performs HNSW approximate nearest neighbor search
3. Returns top-K most semantically similar cases based on cosine similarity

```python
def semantic_search(query_text, limit=10):
    """
    Pure vector similarity search
    """
    # Generate query embedding
    query_embedding = generate_embedding(query_text)

    # Weaviate nearVector search
    result = (
        client.query
        .get("CaseVectorized", [
            "caseNumber", "title", "description",
            "resolutionSummary", "product", "priority"
        ])
        .with_near_vector({
            "vector": query_embedding,
            "certainty": 0.7  # Minimum similarity threshold
        })
        .with_limit(limit)
        .with_additional(["certainty", "distance"])
        .do()
    )

    return result
```

### 2.2.2 Metadata Filtering (Structured Component)

**Enhanced Filterable Fields** (from JSON data mapping - 44 fields total):

| Filter Category | Fields (Weaviate Properties) | Example Values | Use Case |
|----------------|----------------------------|----------------|----------|
| **Product** | productNumber, productLine, productSeries, productHierarchy, productFamily | "BB958A", "34", "ProLiant DL380" | Product-specific searches |
| **Technical Patterns** | errorCodes, issueType, rootCause, resolutionCode | "iLO_400_MemoryErrors", "Product Non-functional", "Onsite Repair" | Error code-driven troubleshooting |
| **Category** | category, issueType | "Hardware > Server > Boot", "Help me/How to" | Categorical filtering |
| **Status & Priority** | status, priority | "Closed", "High", "Critical" | Resolution filtering |
| **Date Range** | createdDate, closedDate | "2024-01-01 to 2024-12-31" | Temporal analysis |
| **Identifiers** | caseNumber, parentId | "5xxxxxxxxx", SFDC GUID | Case lineage tracking |

**NEW: Error Code Filtering** (Critical for Technical Search):
- Error codes like "218004", "FTO-4D", "iLO_400_MemoryErrors", "cpStatusChanged-cpStatus-failed"
- Enables exact matching on technical error patterns
- Supports multi-value filtering (search multiple error codes at once)

```python
def build_metadata_filter(filters_dict):
    """
    Build Weaviate GraphQL filter from user inputs
    ENHANCED: Now supports error codes, issue types, resolution codes

    filters_dict example:
    {
        "productNumber": "BB958A",
        "productLine": "34",
        "errorCodes": ["iLO_400_MemoryErrors", "POST_1796"],
        "issueType": "Product Non-functional",
        "resolutionCode": "Onsite Repair",
        "priority": ["High", "Critical"],
        "status": "Closed",
        "dateRange": {
            "start": "2024-01-01",
            "end": "2024-12-31"
        }
    }
    """
    where_filter = {"operator": "And", "operands": []}

    # Product number filter (exact match)
    if filters_dict.get("productNumber"):
        where_filter["operands"].append({
            "path": ["productNumber"],
            "operator": "Equal",
            "valueText": filters_dict["productNumber"]
        })

    # Product line filter
    if filters_dict.get("productLine"):
        where_filter["operands"].append({
            "path": ["productLine"],
            "operator": "Equal",
            "valueText": filters_dict["productLine"]
        })

    # Product family filter (partial match)
    if filters_dict.get("productFamily"):
        where_filter["operands"].append({
            "path": ["productFamily"],
            "operator": "Like",
            "valueText": f"*{filters_dict['productFamily']}*"
        })

    # **NEW: Error codes filter** (multi-select OR logic)
    if filters_dict.get("errorCodes"):
        error_code_filters = {
            "operator": "Or",
            "operands": [
                {"path": ["errorCodes"], "operator": "Like", "valueText": f"*{code}*"}
                for code in filters_dict["errorCodes"]
            ]
        }
        where_filter["operands"].append(error_code_filters)

    # **NEW: Issue type filter**
    if filters_dict.get("issueType"):
        where_filter["operands"].append({
            "path": ["issueType"],
            "operator": "Equal",
            "valueText": filters_dict["issueType"]
        })

    # **NEW: Resolution code filter**
    if filters_dict.get("resolutionCode"):
        where_filter["operands"].append({
            "path": ["resolutionCode"],
            "operator": "Equal",
            "valueText": filters_dict["resolutionCode"]
        })

    # **NEW: Root cause filter**
    if filters_dict.get("rootCause"):
        where_filter["operands"].append({
            "path": ["rootCause"],
            "operator": "Like",
            "valueText": f"*{filters_dict['rootCause']}*"
        })

    # Priority filter (multi-select)
    if filters_dict.get("priority"):
        priority_filters = {
            "operator": "Or",
            "operands": [
                {"path": ["priority"], "operator": "Equal", "valueText": p}
                for p in filters_dict["priority"]
            ]
        }
        where_filter["operands"].append(priority_filters)

    # Status filter
    if filters_dict.get("status"):
        where_filter["operands"].append({
            "path": ["status"],
            "operator": "Equal",
            "valueText": filters_dict["status"]
        })

    # Date range filter
    if filters_dict.get("dateRange"):
        where_filter["operands"].append({
            "path": ["createdDate"],
            "operator": "GreaterThanEqual",
            "valueDate": filters_dict["dateRange"]["start"]
        })
        where_filter["operands"].append({
            "path": ["createdDate"],
            "operator": "LessThanEqual",
            "valueDate": filters_dict["dateRange"]["end"]
        })

    # Category filter
    if filters_dict.get("category"):
        where_filter["operands"].append({
            "path": ["category"],
            "operator": "Equal",
            "valueText": filters_dict["category"]
        })

    # **NEW: Case number filter** (for exact case lookup)
    if filters_dict.get("caseNumber"):
        where_filter["operands"].append({
            "path": ["caseNumber"],
            "operator": "Equal",
            "valueText": filters_dict["caseNumber"]
        })

    return where_filter if where_filter["operands"] else None
```

---

## 2.3 Combined Hybrid Search Implementation

### 2.3.1 Unified Search API

```python
def hybrid_search(query_text, filters=None, limit=10, alpha=0.75):
    """
    Hybrid search combining vector similarity + metadata filters

    Args:
        query_text: Natural language search query
        filters: Dictionary of metadata filters
        limit: Number of results to return
        alpha: Weight for vector vs keyword search (0=keyword, 1=vector)

    Returns:
        List of ranked case results
    """
    # Generate query embedding
    query_embedding = generate_embedding(query_text)

    # Build metadata filter
    where_filter = build_metadata_filter(filters) if filters else None

    # Construct Weaviate hybrid query
    query_builder = (
        client.query
        .get("CaseVectorized", [
            "caseNumber",
            "title",
            "description",
            "resolutionSummary",
            "compositeText",
            "product",
            "productFamily",
            "category",
            "status",
            "priority",
            "createdDate",
            "closedDate"
        ])
    )

    # Add hybrid search (vector + BM25 keyword)
    query_builder = query_builder.with_hybrid(
        query=query_text,
        vector=query_embedding,
        alpha=alpha  # 0.75 = 75% vector, 25% keyword
    )

    # Add metadata filters
    if where_filter:
        query_builder = query_builder.with_where(where_filter)

    # Add limit and scoring details
    query_builder = (
        query_builder
        .with_limit(limit)
        .with_additional(["score", "explainScore"])
    )

    # Execute query
    result = query_builder.do()

    return parse_search_results(result)
```

### 2.3.2 Search Result Parsing and Ranking

```python
def parse_search_results(raw_result):
    """
    Parse and enrich Weaviate results
    """
    cases = raw_result.get('data', {}).get('Get', {}).get('CaseVectorized', [])

    enriched_results = []
    for case in cases:
        enriched_results.append({
            "caseNumber": case['caseNumber'],
            "title": case['title'],
            "description": truncate_text(case['description'], 200),
            "resolution": truncate_text(case['resolutionSummary'], 200),
            "product": case['product'],
            "productFamily": case['productFamily'],
            "category": case['category'],
            "priority": case['priority'],
            "status": case['status'],
            "createdDate": case['createdDate'],
            "closedDate": case['closedDate'],
            "relevanceScore": case['_additional']['score'],
            "scoreExplanation": case['_additional'].get('explainScore', ''),
            "matchType": determine_match_type(case)
        })

    return enriched_results

def determine_match_type(case):
    """
    Classify why this result matched (for UI transparency)
    """
    score = case['_additional']['score']

    if score > 0.9:
        return "Exact semantic match"
    elif score > 0.8:
        return "Strong semantic similarity"
    elif score > 0.7:
        return "Moderate similarity"
    else:
        return "Metadata match"
```

---

## 2.4 Hybrid Search Strategies by Use Case

### 2.4.1 Strategy 1: Broad Discovery Search

**Use Case**: Engineer exploring similar issues without specific constraints

```python
# Example: "server fails to boot"
result = hybrid_search(
    query_text="server fails to boot",
    filters=None,  # No filters - broad search
    limit=20,
    alpha=0.9  # 90% semantic, 10% keyword
)
```

**Characteristics**:
- High alpha (vector-heavy)
- No metadata filters
- Larger result set
- Sorted by semantic similarity

---

### 2.4.2 Strategy 2: Product-Specific Troubleshooting

**Use Case**: Engineer working on specific product needs relevant cases

```python
# Example: ProLiant DL380 boot issues
result = hybrid_search(
    query_text="server boot failure memory error",
    filters={
        "productFamily": "ProLiant",
        "status": "Closed",  # Only resolved cases
        "priority": ["High", "Critical"]  # Similar severity
    },
    limit=10,
    alpha=0.75  # Balanced hybrid
)
```

**Characteristics**:
- Balanced alpha
- Product + status filters
- Focus on resolved high-priority cases
- Actionable resolutions

---

### 2.4.3 Strategy 3: Recent Case Trends

**Use Case**: Identify recurring issues in recent timeframe

```python
# Example: Recent network connectivity issues
result = hybrid_search(
    query_text="network connectivity timeout",
    filters={
        "dateRange": {
            "start": "2024-10-01",
            "end": "2024-12-31"
        },
        "category": "Networking"
    },
    limit=50,
    alpha=0.6  # More keyword-focused for specificity
)
```

**Characteristics**:
- Date range filter (last 3 months)
- Category constraint
- Larger result set for trend analysis
- Lower alpha for precise keyword matching

---

### 2.4.4 Strategy 4: Cross-Product Pattern Detection

**Use Case**: Identify similar issues across product families

```python
# Example: Firmware update failures across products
result = hybrid_search(
    query_text="firmware update failed checksum error",
    filters={
        "status": "Closed",
        "category": "Firmware"
    },
    limit=30,
    alpha=0.85  # High semantic to find conceptual similarities
)

# Group results by product family
from collections import defaultdict
by_product = defaultdict(list)
for case in result:
    by_product[case['productFamily']].append(case)
```

**Characteristics**:
- No product filter (cross-product)
- High semantic weight
- Post-processing for pattern analysis

---

## 2.5 Advanced Hybrid Search Features

### 2.5.1 Multi-Stage Search Pipeline

```python
def intelligent_hybrid_search(query_text, user_context):
    """
    Adaptive search that adjusts strategy based on result quality
    """
    # Stage 1: Strict hybrid search
    results_strict = hybrid_search(
        query_text=query_text,
        filters={
            "product": user_context.get("current_product"),
            "priority": ["High", "Critical"]
        },
        limit=5,
        alpha=0.8
    )

    # Check if we have high-quality results
    if results_strict and results_strict[0]['relevanceScore'] > 0.85:
        return results_strict

    # Stage 2: Relaxed product filter (product family only)
    results_relaxed = hybrid_search(
        query_text=query_text,
        filters={
            "productFamily": extract_product_family(user_context.get("current_product"))
        },
        limit=10,
        alpha=0.8
    )

    if results_relaxed and results_relaxed[0]['relevanceScore'] > 0.75:
        return results_relaxed

    # Stage 3: Open search with keyword boost
    results_open = hybrid_search(
        query_text=query_text,
        filters=None,
        limit=20,
        alpha=0.6  # More keyword weight
    )

    return results_open
```

### 2.5.2 Faceted Search for Exploration

```python
def faceted_search(query_text, limit=100):
    """
    Return results + facet counts for UI filtering
    """
    # Get broad result set
    results = hybrid_search(query_text, filters=None, limit=limit, alpha=0.8)

    # Calculate facets
    facets = {
        "products": count_facet(results, "product"),
        "productFamilies": count_facet(results, "productFamily"),
        "categories": count_facet(results, "category"),
        "priorities": count_facet(results, "priority"),
        "statuses": count_facet(results, "status"),
        "dateRanges": calculate_date_distribution(results)
    }

    return {
        "results": results[:10],  # First page
        "totalCount": len(results),
        "facets": facets
    }

def count_facet(results, field):
    """Count occurrences for faceted navigation"""
    from collections import Counter
    counts = Counter([r[field] for r in results if r.get(field)])
    return [{"value": k, "count": v} for k, v in counts.most_common(10)]
```

---

## 2.6 Metadata Enrichment Pipeline

To enable effective hybrid search, we need rich, clean metadata.

### 2.6.1 Product Family Extraction

```python
def extract_product_family(product_string):
    """
    Extract standardized product family from product field

    Examples:
    "ProLiant DL380 Gen10" → "ProLiant"
    "HPE Synergy 480 Gen10" → "Synergy"
    "Aruba 2930F Switch" → "Aruba Switches"
    """
    product_family_map = {
        r"ProLiant.*": "ProLiant",
        r"Synergy.*": "Synergy",
        r"Apollo.*": "Apollo",
        r"Aruba.*Switch.*": "Aruba Switches",
        r"Aruba.*AP.*": "Aruba Access Points",
        r"3PAR.*": "3PAR Storage",
        r"Nimble.*": "Nimble Storage",
        r"SimpliVity.*": "SimpliVity"
    }

    for pattern, family in product_family_map.items():
        if re.search(pattern, product_string, re.IGNORECASE):
            return family

    return "Other"
```

### 2.6.2 Category Hierarchy Normalization

```python
def normalize_category(category_raw):
    """
    Standardize category into hierarchy

    Raw: "HW - Server - Boot Issues"
    Normalized: {
        "level1": "Hardware",
        "level2": "Server",
        "level3": "Boot",
        "fullPath": "Hardware > Server > Boot"
    }
    """
    category_mapping = {
        "HW": "Hardware",
        "SW": "Software",
        "NW": "Networking",
        "FW": "Firmware"
    }

    parts = [p.strip() for p in category_raw.split("-")]

    return {
        "level1": category_mapping.get(parts[0], parts[0]),
        "level2": parts[1] if len(parts) > 1 else None,
        "level3": parts[2] if len(parts) > 2 else None,
        "fullPath": " > ".join([category_mapping.get(parts[0], parts[0])] + parts[1:])
    }
```

### 2.6.3 Derived Metadata Calculation

```python
def calculate_derived_metadata(case):
    """
    Calculate additional metadata for better filtering
    """
    from datetime import datetime

    created = datetime.fromisoformat(case['createdDate'])
    closed = datetime.fromisoformat(case['closedDate']) if case.get('closedDate') else None

    derived = {}

    # Resolution time bucket
    if closed:
        resolution_hours = (closed - created).total_seconds() / 3600
        if resolution_hours < 4:
            derived['resolutionTimeBucket'] = "0-4 hours"
        elif resolution_hours < 24:
            derived['resolutionTimeBucket'] = "4-24 hours"
        elif resolution_hours < 168:  # 7 days
            derived['resolutionTimeBucket'] = "1-7 days"
        else:
            derived['resolutionTimeBucket'] = ">7 days"

        derived['resolutionTimeHours'] = resolution_hours

    # Case age
    age_days = (datetime.now() - created).days
    derived['ageInDays'] = age_days

    # Complexity score (based on description length, # of updates, etc.)
    derived['complexityScore'] = calculate_complexity(case)

    # Quarter/Year for temporal analysis
    derived['quarter'] = f"Q{(created.month-1)//3 + 1} {created.year}"
    derived['year'] = created.year

    return derived
```

---

## 2.7 Search API Endpoint Design

### 2.7.1 RESTful Search Endpoint

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/v1/search', methods=['POST'])
def search_cases():
    """
    Hybrid search endpoint

    Request Body:
    {
        "query": "server boot failure",
        "filters": {
            "product": "ProLiant DL380",
            "priority": ["High", "Critical"],
            "dateRange": {"start": "2024-01-01", "end": "2024-12-31"}
        },
        "limit": 10,
        "alpha": 0.75
    }
    """
    try:
        data = request.get_json()

        # Validate inputs
        query_text = data.get('query', '').strip()
        if not query_text or len(query_text) < 3:
            return jsonify({"error": "Query must be at least 3 characters"}), 400

        filters = data.get('filters', {})
        limit = min(data.get('limit', 10), 50)  # Max 50 results
        alpha = data.get('alpha', 0.75)

        # Execute hybrid search
        results = hybrid_search(
            query_text=query_text,
            filters=filters,
            limit=limit,
            alpha=alpha
        )

        # Log search query for analytics
        log_search_query(
            user_id=request.headers.get('X-User-ID'),
            query=query_text,
            filters=filters,
            result_count=len(results)
        )

        return jsonify({
            "query": query_text,
            "filters": filters,
            "resultCount": len(results),
            "results": results,
            "searchMetadata": {
                "alpha": alpha,
                "executionTimeMs": results.get('executionTime', 0)
            }
        }), 200

    except Exception as e:
        logger.error(f"Search error: {e}")
        return jsonify({"error": "Search failed"}), 500
```

### 2.7.2 GraphQL Alternative (for flexible queries)

```graphql
type Query {
  searchCases(
    query: String!
    filters: CaseFilters
    limit: Int = 10
    alpha: Float = 0.75
  ): SearchResults!
}

type SearchResults {
  totalCount: Int!
  results: [Case!]!
  facets: Facets!
  executionTimeMs: Int!
}

type Case {
  caseNumber: String!
  title: String!
  description: String!
  resolutionSummary: String
  product: String
  productFamily: String
  category: String
  priority: String
  status: String!
  createdDate: DateTime!
  closedDate: DateTime
  relevanceScore: Float!
  matchType: String!
}

input CaseFilters {
  product: String
  productFamily: String
  category: String
  priority: [String!]
  status: String
  dateRange: DateRange
}

input DateRange {
  start: DateTime!
  end: DateTime!
}

type Facets {
  products: [FacetValue!]!
  categories: [FacetValue!]!
  priorities: [FacetValue!]!
  statuses: [FacetValue!]!
}

type FacetValue {
  value: String!
  count: Int!
}
```

---

## Key Takeaways

1. **Balanced Approach**: Use alpha=0.75 as default (75% semantic, 25% keyword)
2. **Filter Strategy**: Apply strict filters for product-specific searches, relax for discovery
3. **Multi-Stage**: Implement fallback strategies when initial search yields poor results
4. **Metadata Quality**: Invest in metadata enrichment for effective filtering
5. **User Context**: Leverage user's current product/context to bias results

---

## References
- Weaviate Hybrid Search Documentation
- BM25 Algorithm Overview
- Cosine Similarity Best Practices
