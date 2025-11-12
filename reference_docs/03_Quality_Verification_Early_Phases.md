# Section 3: Quality Verification of Search Results in Early Phases

## 3.1 Overview

**Objective**: Establish systematic quality verification processes during development phases (Weeks 2-8) to ensure search accuracy meets the >85% precision@5 target before production deployment.

**Verification Phases**:
- **Phase 1 (Week 2-3)**: Schema & API validation with 1K sample cases
- **Phase 2 (Week 6)**: 100K test load with GRS team validation
- **Phase 3 (Week 7-8)**: End-to-end accuracy tuning and regression testing

---

## 3.2 Phase 1: Schema & API Validation (Week 2-3)

### 3.2.1 Sample Data Selection

```python
def select_validation_sample(df_sfdc_cases, sample_size=1000):
    """
    Stratified sampling to ensure diverse representation

    Criteria:
    - Mix of products (ProLiant, Synergy, Aruba, Storage)
    - Mix of priorities (Critical: 20%, High: 30%, Medium: 40%, Low: 10%)
    - Mix of complexity (simple, moderate, complex based on description length)
    - Only closed/resolved cases with resolutions
    - Date range: Last 6 months
    """
    from sklearn.model_selection import train_test_split

    # Filter criteria
    df_filtered = df_sfdc_cases[
        (df_sfdc_cases['Status'].isin(['Closed', 'Resolved'])) &
        (df_sfdc_cases['Resolution__c'].notna()) &
        (df_sfdc_cases['CreatedDate'] >= '2024-06-01') &
        (df_sfdc_cases['Description'].str.len() > 50)
    ].copy()

    # Add complexity score
    df_filtered['complexity'] = df_filtered['Description'].str.len().apply(
        lambda x: 'simple' if x < 200 else ('moderate' if x < 800 else 'complex')
    )

    # Stratified sampling
    sample = df_filtered.groupby(['Product__c', 'Priority', 'complexity'],
                                   group_keys=False).apply(
        lambda x: x.sample(min(len(x), sample_size // 20))
    ).head(sample_size)

    # Log distribution
    logger.info(f"Sample distribution:\n{sample.groupby(['Product__c', 'Priority']).size()}")

    return sample
```

### 3.2.2 Ground Truth Test Query Set

Create a **golden query set** with expected results covering **all 6 data tables and 44 fields**:

```python
GOLDEN_QUERIES = [
    {
        "query_id": "Q001",
        "query_text": "server fails to boot after firmware update",
        "expected_cases": ["5007T000002AbcD", "5007T000002XyzA"],
        "expected_products": ["ProLiant"],
        "expected_categories": ["Hardware", "Firmware"],
        "expected_error_codes": ["POST_1796", "iLO_400_MemoryErrors"],
        "min_precision_at_5": 0.8
    },
    {
        "query_id": "Q002",
        "query_text": "network connectivity timeout ESXi host",
        "expected_cases": ["5007T000003DefG"],
        "expected_products": ["Aruba", "ProLiant"],
        "expected_categories": ["Networking"],
        "min_precision_at_5": 0.8
    },
    {
        "query_id": "Q003",
        "query_text": "disk failure SMART error",
        "expected_cases": ["5007T000004HijK", "5007T000005LmnO"],
        "expected_products": ["ProLiant", "Apollo"],
        "expected_categories": ["Hardware", "Storage"],
        "min_precision_at_5": 0.9
    },
    # NEW: Error code-specific queries
    {
        "query_id": "Q004",
        "query_text": "iLO_400_MemoryErrors",
        "filters": {"errorCodes": ["iLO_400_MemoryErrors"]},
        "expected_products": ["ProLiant"],
        "expected_resolution_codes": ["Onsite Repair", "Part Shipped"],
        "min_precision_at_5": 0.95,  # Higher threshold for exact error code match
        "test_type": "error_code_search"
    },
    # NEW: Multi-table search (Task + WorkOrder)
    {
        "query_id": "Q005",
        "query_text": "replaced DIMM memory module onsite",
        "expected_tables": ["Case", "Task", "WorkOrder"],
        "expected_products": ["ProLiant", "Synergy"],
        "expected_resolution_codes": ["Onsite Repair"],
        "min_precision_at_5": 0.85,
        "test_type": "multi_table_search"
    },
    # NEW: Issue type filtering
    {
        "query_id": "Q006",
        "query_text": "product not working as expected",
        "filters": {"issueType": "Product Non-functional/Not working as Expected"},
        "expected_status": ["Closed"],
        "min_precision_at_5": 0.8,
        "test_type": "issue_type_filter"
    },
    # NEW: Comments/Email search
    {
        "query_id": "Q007",
        "query_text": "customer confirmed resolution successful",
        "expected_tables": ["CaseComments", "EmailMessage"],
        "expected_status": ["Closed"],
        "min_precision_at_5": 0.8,
        "test_type": "comments_email_search"
    },
    # ... 43 more queries covering diverse scenarios
]

def create_golden_query_set():
    """
    Generate 50 diverse test queries from actual case data
    """
    queries = []

    # Select 50 representative resolved cases
    sample_cases = select_representative_cases(n=50)

    for idx, case in enumerate(sample_cases):
        # Extract key phrases from title/description
        query_text = extract_search_query(case['Subject'], case['Description'])

        # Find similar cases (manual review required)
        similar_cases = find_similar_cases_manual(case)

        queries.append({
            "query_id": f"Q{idx+1:03d}",
            "query_text": query_text,
            "source_case": case['CaseNumber'],
            "expected_cases": similar_cases,
            "expected_products": [case['Product__c']],
            "expected_categories": [case['Category__c']],
            "min_precision_at_5": 0.85,
            "created_by": "algoleap_qa_team",
            "review_status": "pending_grs_validation"
        })

    return queries
```

### 3.2.3 Automated Quality Checks (Enhanced for Multi-Table Data)

```python
def run_schema_validation_tests():
    """
    Week 2-3: Basic quality checks on 1K sample
    ENHANCED: Validates all 6 tables and 44 fields
    """
    test_results = {
        "passed": [],
        "failed": [],
        "warnings": []
    }

    # Test 1: Embedding generation success rate
    print("Test 1: Embedding Generation")
    embedding_success_rate = test_embedding_generation()
    if embedding_success_rate >= 0.99:
        test_results["passed"].append(f"Embedding success: {embedding_success_rate:.2%}")
    else:
        test_results["failed"].append(f"Embedding success too low: {embedding_success_rate:.2%}")

    # Test 2: PII removal verification (ALL 6 TABLES)
    print("Test 2: PII Removal (Multi-Table)")
    pii_results = test_pii_removal_all_tables()
    if pii_results["total_leaks"] == 0:
        test_results["passed"].append("No PII detected in processed data (all tables)")
    else:
        test_results["failed"].append(
            f"PII detected: Case={pii_results['case']}, Task={pii_results['task']}, "
            f"WorkOrder={pii_results['workorder']}, Comments={pii_results['comments']}, "
            f"Email={pii_results['email']}"
        )

    # Test 3: Multi-table join completeness
    print("Test 3: Multi-Table Data Completeness")
    join_stats = test_multi_table_joins()
    test_results["passed"].append(
        f"Table coverage: Case=100%, Task={join_stats['task_coverage']:.1%}, "
        f"WorkOrder={join_stats['workorder_coverage']:.1%}, "
        f"Comments={join_stats['comments_coverage']:.1%}"
    )
    if join_stats['task_coverage'] < 0.3:
        test_results["warnings"].append("Low Task table coverage - expected for some cases")

    # Test 4: Field-level validation
    print("Test 4: Field-Level Validation (44 fields)")
    field_validation = test_field_completeness()
    critical_fields = ['subject', 'description', 'casenumber', 'product_number']
    for field in critical_fields:
        if field_validation[field] >= 0.95:
            test_results["passed"].append(f"Field '{field}': {field_validation[field]:.1%} populated")
        else:
            test_results["failed"].append(f"Field '{field}': Only {field_validation[field]:.1%} populated")

    # Test 5: Error code field validation
    print("Test 5: Error Code Field Validation")
    error_code_stats = test_error_code_fields()
    test_results["passed"].append(
        f"Error codes present in {error_code_stats['percentage']:.1%} of cases"
    )
    test_results["passed"].append(
        f"Unique error codes found: {error_code_stats['unique_count']}"
    )

    # Test 6: Weaviate load success
    print("Test 6: Weaviate Load")
    load_success_rate = test_weaviate_load()
    if load_success_rate >= 0.99:
        test_results["passed"].append(f"Load success: {load_success_rate:.2%}")
    else:
        test_results["failed"].append(f"Load success too low: {load_success_rate:.2%}")

    # Test 7: Basic search functionality
    print("Test 7: Search API")
    search_response_time = test_search_api()
    if search_response_time < 1.0:
        test_results["passed"].append(f"Search latency: {search_response_time:.3f}s")
    else:
        test_results["warnings"].append(f"Search latency high: {search_response_time:.3f}s")

    # Test 5: Golden query precision (subset)
    print("Test 5: Golden Query Precision (10 queries)")
    precision_scores = test_golden_queries(GOLDEN_QUERIES[:10])
    avg_precision = sum(precision_scores) / len(precision_scores)
    if avg_precision >= 0.75:  # Lower threshold for early phase
        test_results["passed"].append(f"Avg precision@5: {avg_precision:.2%}")
    else:
        test_results["failed"].append(f"Avg precision@5 too low: {avg_precision:.2%}")

    # Generate report
    print("\n" + "="*60)
    print("SCHEMA VALIDATION TEST RESULTS")
    print("="*60)
    print(f"✓ Passed: {len(test_results['passed'])}")
    print(f"✗ Failed: {len(test_results['failed'])}")
    print(f"⚠ Warnings: {len(test_results['warnings'])}")
    print("\nDetails:")
    for result in test_results['passed']:
        print(f"  ✓ {result}")
    for result in test_results['failed']:
        print(f"  ✗ {result}")
    for result in test_results['warnings']:
        print(f"  ⚠ {result}")

    return test_results

def test_embedding_generation():
    """Test embedding generation on sample"""
    sample_texts = load_sample_composite_texts(n=100)

    success_count = 0
    for text in sample_texts:
        try:
            embedding = generate_embedding(text)
            if len(embedding) == 3072:  # Correct dimension
                success_count += 1
        except Exception as e:
            logger.error(f"Embedding failed: {e}")

    return success_count / len(sample_texts)

def test_pii_removal():
    """Test PII detection in processed data"""
    sample_cases = load_processed_cases(n=100)

    pii_patterns = [
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        r'(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # Phone
        r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'  # IP address
    ]

    pii_leak_count = 0
    for case in sample_cases:
        composite_text = case.get('compositeText', '')
        for pattern in pii_patterns:
            if re.search(pattern, composite_text):
                pii_leak_count += 1
                logger.warning(f"PII detected in case {case['caseNumber']}")
                break

    return pii_leak_count

def test_golden_queries(queries):
    """Test precision on golden query set"""
    precision_scores = []

    for query_obj in queries:
        results = hybrid_search(
            query_text=query_obj['query_text'],
            filters=None,
            limit=5,
            alpha=0.8
        )

        # Calculate precision@5
        returned_cases = [r['caseNumber'] for r in results]
        expected_cases = set(query_obj['expected_cases'])

        relevant_in_top5 = len(set(returned_cases) & expected_cases)
        precision_at_5 = relevant_in_top5 / 5

        precision_scores.append(precision_at_5)

        logger.info(f"Query {query_obj['query_id']}: P@5 = {precision_at_5:.2f}")

    return precision_scores
```

---

## 3.3 Phase 2: GRS Team Validation (Week 6)

### 3.3.1 100K Test Load Preparation

```python
def prepare_100k_test_load():
    """
    Select 100K cases for Week 6 validation

    Criteria:
    - Last 3 months of data (recency)
    - All product families represented
    - Only closed/resolved cases
    - Balanced priority distribution
    """
    df_100k = df_sfdc_cases[
        (df_sfdc_cases['CreatedDate'] >= '2024-07-01') &
        (df_sfdc_cases['Status'].isin(['Closed', 'Resolved'])) &
        (df_sfdc_cases['Resolution__c'].notna())
    ].copy()

    # Stratified sampling
    sample_100k = df_100k.groupby('Product__c', group_keys=False).apply(
        lambda x: x.sample(min(len(x), 100000 // df_100k['Product__c'].nunique()))
    ).head(100000)

    logger.info(f"100K test load prepared: {len(sample_100k)} cases")
    logger.info(f"Product distribution:\n{sample_100k['Product__c'].value_counts()}")

    return sample_100k
```

### 3.3.2 GRS Team Validation Framework

**Human-in-the-Loop Evaluation**:

```python
def create_grs_validation_interface():
    """
    Create evaluation interface for GRS engineers

    UI Components:
    - Search box with filters
    - Results display (top 10)
    - Relevance rating (1-5 stars per result)
    - Comments box for feedback
    """

    validation_tasks = {
        "task_id": "GRS_VAL_001",
        "assigned_to": "grs_team",
        "total_queries": 50,
        "queries": generate_validation_queries(n=50),
        "instructions": """
        For each query:
        1. Execute the search
        2. Rate top 5 results for relevance (1-5 stars)
        3. Mark if result would help resolve the issue
        4. Provide comments on result quality

        Rating Scale:
        5 ★ - Exact match, would definitely use
        4 ★ - Highly relevant, very helpful
        3 ★ - Somewhat relevant, might be useful
        2 ★ - Marginally relevant, limited usefulness
        1 ★ - Not relevant, would not use
        """,
        "deadline": "2024-Week6-Friday",
        "completion_status": "pending"
    }

    return validation_tasks

def generate_validation_queries(n=50):
    """
    Generate realistic validation queries based on actual case titles
    """
    # Get diverse case titles from different products/categories
    sample_cases = select_diverse_cases(n=n)

    queries = []
    for idx, case in enumerate(sample_cases):
        # Simplify case title to simulate user query
        query_text = simplify_to_user_query(case['Subject'])

        queries.append({
            "query_number": idx + 1,
            "query_text": query_text,
            "source_case": case['CaseNumber'],
            "product_context": case['Product__c'],
            "expected_resolution_type": case['Category__c'],
            "evaluator_ratings": [],  # To be filled by GRS team
            "evaluator_comments": ""
        })

    return queries

def simplify_to_user_query(case_title):
    """
    Convert formal case title to natural user query

    Example:
    "ProLiant DL380 Gen10 - POST Error Code 1796"
    → "server post error 1796"
    """
    # Remove product model details
    simplified = re.sub(r'(Gen\d+|DL\d+|ML\d+|BL\d+)', '', case_title)
    # Remove special characters
    simplified = re.sub(r'[^\w\s]', ' ', simplified)
    # Lowercase and trim
    simplified = ' '.join(simplified.lower().split())

    return simplified
```

### 3.3.3 Precision and Recall Metrics

```python
def calculate_precision_recall_metrics(evaluation_results):
    """
    Calculate search quality metrics from GRS evaluation

    Metrics:
    - Precision@K (K=1,3,5,10)
    - Mean Average Precision (MAP)
    - Normalized Discounted Cumulative Gain (NDCG@5)
    - Mean Reciprocal Rank (MRR)
    """
    metrics = {
        "precision_at_1": [],
        "precision_at_3": [],
        "precision_at_5": [],
        "precision_at_10": [],
        "ndcg_at_5": [],
        "mrr": []
    }

    for query_eval in evaluation_results:
        ratings = query_eval['evaluator_ratings']  # List of 1-5 star ratings

        # Convert ratings to binary relevance (≥4 stars = relevant)
        binary_relevance = [1 if r >= 4 else 0 for r in ratings]

        # Precision@K
        metrics['precision_at_1'].append(binary_relevance[0] if len(binary_relevance) > 0 else 0)
        metrics['precision_at_3'].append(sum(binary_relevance[:3]) / 3 if len(binary_relevance) >= 3 else 0)
        metrics['precision_at_5'].append(sum(binary_relevance[:5]) / 5 if len(binary_relevance) >= 5 else 0)
        metrics['precision_at_10'].append(sum(binary_relevance[:10]) / 10 if len(binary_relevance) >= 10 else 0)

        # NDCG@5 (uses graded relevance 1-5)
        ndcg_5 = calculate_ndcg(ratings[:5], k=5)
        metrics['ndcg_at_5'].append(ndcg_5)

        # MRR (position of first relevant result)
        first_relevant_pos = next((i+1 for i, rel in enumerate(binary_relevance) if rel == 1), 0)
        mrr = 1 / first_relevant_pos if first_relevant_pos > 0 else 0
        metrics['mrr'].append(mrr)

    # Calculate averages
    avg_metrics = {
        "avg_precision_at_1": np.mean(metrics['precision_at_1']),
        "avg_precision_at_3": np.mean(metrics['precision_at_3']),
        "avg_precision_at_5": np.mean(metrics['precision_at_5']),
        "avg_precision_at_10": np.mean(metrics['precision_at_10']),
        "avg_ndcg_at_5": np.mean(metrics['ndcg_at_5']),
        "avg_mrr": np.mean(metrics['mrr']),
        "total_queries": len(evaluation_results)
    }

    return avg_metrics

def calculate_ndcg(ratings, k=5):
    """
    Normalized Discounted Cumulative Gain

    Formula: NDCG@k = DCG@k / IDCG@k
    where DCG = Σ (2^rel_i - 1) / log2(i + 1)
    """
    def dcg(relevances, k):
        return sum([
            (2**rel - 1) / np.log2(i + 2)  # i+2 because i is 0-indexed
            for i, rel in enumerate(relevances[:k])
        ])

    # Actual DCG
    dcg_actual = dcg(ratings, k)

    # Ideal DCG (sorted by relevance)
    dcg_ideal = dcg(sorted(ratings, reverse=True), k)

    return dcg_actual / dcg_ideal if dcg_ideal > 0 else 0
```

### 3.3.4 Validation Report Generation

```python
def generate_grs_validation_report(evaluation_results):
    """
    Generate comprehensive validation report for Week 6 checkpoint
    """
    metrics = calculate_precision_recall_metrics(evaluation_results)

    report = f"""
# GRS Team Validation Report - Week 6
**Date**: {datetime.now().strftime('%Y-%m-%d')}
**Test Load**: 100,000 cases
**Queries Evaluated**: {metrics['total_queries']}
**Evaluators**: GRS Team (5 engineers)

## Overall Metrics

| Metric | Score | Target | Status |
|--------|-------|--------|--------|
| Precision@1 | {metrics['avg_precision_at_1']:.2%} | >70% | {'✓ PASS' if metrics['avg_precision_at_1'] >= 0.70 else '✗ FAIL'} |
| Precision@3 | {metrics['avg_precision_at_3']:.2%} | >80% | {'✓ PASS' if metrics['avg_precision_at_3'] >= 0.80 else '✗ FAIL'} |
| **Precision@5** | **{metrics['avg_precision_at_5']:.2%}** | **>85%** | {'✓ PASS' if metrics['avg_precision_at_5'] >= 0.85 else '✗ FAIL'} |
| Precision@10 | {metrics['avg_precision_at_10']:.2%} | >75% | {'✓ PASS' if metrics['avg_precision_at_10'] >= 0.75 else '✗ FAIL'} |
| NDCG@5 | {metrics['avg_ndcg_at_5']:.2%} | >0.85 | {'✓ PASS' if metrics['avg_ndcg_at_5'] >= 0.85 else '✗ FAIL'} |
| MRR | {metrics['avg_mrr']:.2%} | >0.80 | {'✓ PASS' if metrics['avg_mrr'] >= 0.80 else '✗ FAIL'} |

## Breakdown by Product Family

{generate_product_breakdown(evaluation_results)}

## Breakdown by Query Complexity

{generate_complexity_breakdown(evaluation_results)}

## Key Findings

{generate_key_findings(evaluation_results)}

## Recommended Actions

{generate_recommendations(metrics)}

## Sample Queries with Low Scores

{generate_low_score_examples(evaluation_results)}

---
**Report Generated**: {datetime.now().isoformat()}
**Next Steps**: Address identified gaps, retest in Week 7
"""

    # Save report
    with open(f'reports/grs_validation_week6_{datetime.now().strftime("%Y%m%d")}.md', 'w') as f:
        f.write(report)

    return report

def generate_recommendations(metrics):
    """
    Generate actionable recommendations based on metrics
    """
    recommendations = []

    if metrics['avg_precision_at_5'] < 0.85:
        recommendations.append("""
        **CRITICAL**: Precision@5 below target
        - Review embedding model parameters
        - Tune HNSW index settings (ef, efConstruction)
        - Consider query expansion techniques
        - Analyze failed queries for patterns
        """)

    if metrics['avg_precision_at_1'] < 0.70:
        recommendations.append("""
        **HIGH**: Low first-result precision
        - Implement query understanding/classification
        - Boost exact keyword matches
        - Add spell correction
        - Review product/category metadata quality
        """)

    if metrics['avg_mrr'] < 0.80:
        recommendations.append("""
        **MEDIUM**: Relevant results not appearing early enough
        - Adjust hybrid search alpha parameter
        - Implement learning-to-rank (LTR) model
        - Personalize results based on user context
        """)

    return "\n".join(recommendations) if recommendations else "✓ All metrics within acceptable ranges"
```

---

## 3.4 Phase 3: Accuracy Tuning & Regression Testing (Week 7-8)

### 3.4.1 Hyperparameter Tuning

```python
def tune_search_parameters():
    """
    Systematic tuning of hybrid search parameters

    Parameters to tune:
    - alpha (vector vs keyword weight)
    - HNSW ef (search quality vs speed)
    - Similarity threshold
    - Result ranking formula
    """
    from sklearn.model_selection import GridSearchCV

    # Parameter grid
    param_grid = {
        'alpha': [0.6, 0.7, 0.75, 0.8, 0.85, 0.9],
        'ef': [100, 200, 300, 400],
        'certainty_threshold': [0.65, 0.70, 0.75, 0.80]
    }

    # Load golden query set
    golden_queries = load_golden_queries()

    best_score = 0
    best_params = {}

    results = []

    for alpha in param_grid['alpha']:
        for ef in param_grid['ef']:
            for threshold in param_grid['certainty_threshold']:
                # Update Weaviate config
                update_hnsw_config(ef=ef)

                # Run evaluation
                precision_scores = []
                for query_obj in golden_queries:
                    results_query = hybrid_search(
                        query_text=query_obj['query_text'],
                        filters=None,
                        limit=5,
                        alpha=alpha
                    )

                    # Filter by certainty threshold
                    results_filtered = [
                        r for r in results_query
                        if r['relevanceScore'] >= threshold
                    ]

                    # Calculate precision@5
                    precision = calculate_precision_at_k(
                        results_filtered,
                        query_obj['expected_cases'],
                        k=5
                    )
                    precision_scores.append(precision)

                avg_precision = np.mean(precision_scores)

                results.append({
                    'alpha': alpha,
                    'ef': ef,
                    'threshold': threshold,
                    'precision_at_5': avg_precision
                })

                if avg_precision > best_score:
                    best_score = avg_precision
                    best_params = {
                        'alpha': alpha,
                        'ef': ef,
                        'threshold': threshold
                    }

                logger.info(f"Params: alpha={alpha}, ef={ef}, threshold={threshold} → P@5={avg_precision:.3f}")

    # Save tuning results
    df_results = pd.DataFrame(results)
    df_results.to_csv('tuning_results_week7.csv', index=False)

    logger.info(f"Best parameters: {best_params} with P@5={best_score:.3f}")

    return best_params, df_results
```

### 3.4.2 Continuous Regression Testing

```python
def setup_regression_test_suite():
    """
    Automated regression testing for ongoing quality assurance
    """

    regression_suite = {
        "name": "Vector Search Regression Suite",
        "version": "1.0",
        "tests": [
            {
                "test_id": "RT001",
                "name": "Golden Query Precision",
                "description": "Verify precision@5 on 50 golden queries",
                "target": ">=0.85",
                "frequency": "daily",
                "function": test_golden_query_precision
            },
            {
                "test_id": "RT002",
                "name": "Product-Specific Accuracy",
                "description": "Verify accuracy for each product family",
                "target": ">=0.80 for each product",
                "frequency": "weekly",
                "function": test_product_specific_accuracy
            },
            {
                "test_id": "RT003",
                "name": "Query Latency",
                "description": "Verify search response time",
                "target": "<1s p95",
                "frequency": "daily",
                "function": test_query_latency
            },
            {
                "test_id": "RT004",
                "name": "No Degradation",
                "description": "Compare with baseline from previous week",
                "target": "No >5% degradation",
                "frequency": "weekly",
                "function": test_no_degradation
            },
            {
                "test_id": "RT005",
                "name": "PII Leakage",
                "description": "Scan results for PII",
                "target": "0 PII detections",
                "frequency": "daily",
                "function": test_pii_in_results
            }
        ]
    }

    return regression_suite

def run_regression_tests(test_suite):
    """
    Execute regression test suite and generate report
    """
    results = []

    for test in test_suite['tests']:
        logger.info(f"Running {test['test_id']}: {test['name']}")

        try:
            test_result = test['function']()

            results.append({
                "test_id": test['test_id'],
                "name": test['name'],
                "status": "PASS" if test_result['passed'] else "FAIL",
                "actual_value": test_result['value'],
                "target": test['target'],
                "timestamp": datetime.now().isoformat(),
                "details": test_result.get('details', '')
            })

        except Exception as e:
            results.append({
                "test_id": test['test_id'],
                "name": test['name'],
                "status": "ERROR",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    # Generate report
    report = generate_regression_report(results)

    # Send alerts if any failures
    failures = [r for r in results if r['status'] in ['FAIL', 'ERROR']]
    if failures:
        send_alert_to_team(failures)

    return results
```

### 3.4.3 A/B Testing Framework

```python
def setup_ab_test(variant_a_config, variant_b_config, traffic_split=0.5):
    """
    A/B test different search configurations

    Example:
    - Variant A: alpha=0.75, ef=200
    - Variant B: alpha=0.85, ef=300
    """

    ab_test = {
        "test_id": f"AB_TEST_{datetime.now().strftime('%Y%m%d')}",
        "start_date": datetime.now(),
        "duration_days": 7,
        "traffic_split": traffic_split,
        "variants": {
            "A": {
                "name": "Baseline",
                "config": variant_a_config,
                "metrics": {"queries": 0, "precision_scores": [], "latencies": []}
            },
            "B": {
                "name": "Experimental",
                "config": variant_b_config,
                "metrics": {"queries": 0, "precision_scores": [], "latencies": []}
            }
        }
    }

    return ab_test

def route_search_request(query, ab_test):
    """
    Route search request to A or B variant
    """
    import random

    # Random assignment based on traffic split
    variant = "A" if random.random() < ab_test['traffic_split'] else "B"

    # Execute search with variant config
    config = ab_test['variants'][variant]['config']
    start_time = time.time()

    results = hybrid_search(
        query_text=query['text'],
        filters=query.get('filters'),
        limit=10,
        alpha=config['alpha']
    )

    latency = time.time() - start_time

    # Track metrics
    ab_test['variants'][variant]['metrics']['queries'] += 1
    ab_test['variants'][variant]['metrics']['latencies'].append(latency)

    # Log for analysis
    log_ab_test_event(ab_test['test_id'], variant, query, results, latency)

    return results

def analyze_ab_test_results(ab_test):
    """
    Statistical analysis of A/B test results
    """
    from scipy import stats

    variant_a = ab_test['variants']['A']['metrics']
    variant_b = ab_test['variants']['B']['metrics']

    # T-test for latency
    t_stat_latency, p_value_latency = stats.ttest_ind(
        variant_a['latencies'],
        variant_b['latencies']
    )

    # T-test for precision (if available)
    if variant_a['precision_scores'] and variant_b['precision_scores']:
        t_stat_precision, p_value_precision = stats.ttest_ind(
            variant_a['precision_scores'],
            variant_b['precision_scores']
        )
    else:
        t_stat_precision, p_value_precision = None, None

    analysis = {
        "variant_a_queries": variant_a['queries'],
        "variant_b_queries": variant_b['queries'],
        "variant_a_avg_latency": np.mean(variant_a['latencies']),
        "variant_b_avg_latency": np.mean(variant_b['latencies']),
        "latency_improvement": (
            (np.mean(variant_a['latencies']) - np.mean(variant_b['latencies'])) /
            np.mean(variant_a['latencies'])
        ),
        "latency_p_value": p_value_latency,
        "latency_significant": p_value_latency < 0.05,
        "precision_improvement": (
            (np.mean(variant_b['precision_scores']) - np.mean(variant_a['precision_scores'])) /
            np.mean(variant_a['precision_scores'])
        ) if variant_a['precision_scores'] else None,
        "precision_p_value": p_value_precision,
        "precision_significant": p_value_precision < 0.05 if p_value_precision else None,
        "recommendation": None
    }

    # Generate recommendation
    if analysis['latency_significant'] and analysis['latency_improvement'] > 0.1:
        analysis['recommendation'] = f"✓ Variant B shows {analysis['latency_improvement']:.1%} latency improvement (statistically significant). Recommend rollout."
    elif analysis['precision_significant'] and analysis['precision_improvement'] > 0.05:
        analysis['recommendation'] = f"✓ Variant B shows {analysis['precision_improvement']:.1%} precision improvement (statistically significant). Recommend rollout."
    else:
        analysis['recommendation'] = "No significant improvement detected. Keep Variant A (baseline)."

    return analysis
```

---

## 3.5 Quality Metrics Dashboard

### 3.5.1 Real-Time Quality Monitoring

```python
def create_quality_metrics_dashboard():
    """
    Grafana dashboard configuration for quality metrics
    """

    dashboard_config = {
        "title": "Vector Search Quality Metrics",
        "panels": [
            {
                "title": "Precision@5 (Daily)",
                "type": "graph",
                "datasource": "Prometheus",
                "targets": [
                    {
                        "expr": "avg(search_precision_at_5)",
                        "legendFormat": "Precision@5"
                    }
                ],
                "thresholds": [
                    {"value": 0.85, "color": "green"},
                    {"value": 0.80, "color": "yellow"},
                    {"value": 0.0, "color": "red"}
                ]
            },
            {
                "title": "Query Latency (p95)",
                "type": "graph",
                "datasource": "Prometheus",
                "targets": [
                    {
                        "expr": "histogram_quantile(0.95, search_latency_seconds)",
                        "legendFormat": "p95 Latency"
                    }
                ],
                "thresholds": [
                    {"value": 1.0, "color": "green"},
                    {"value": 2.0, "color": "yellow"},
                    {"value": 5.0, "color": "red"}
                ]
            },
            {
                "title": "Search Success Rate",
                "type": "stat",
                "datasource": "Prometheus",
                "targets": [
                    {
                        "expr": "sum(rate(search_requests_total{status='success'}[5m])) / sum(rate(search_requests_total[5m]))"
                    }
                ]
            },
            {
                "title": "Zero Results Rate",
                "type": "graph",
                "datasource": "Prometheus",
                "targets": [
                    {
                        "expr": "sum(rate(search_requests_total{result_count='0'}[5m])) / sum(rate(search_requests_total[5m]))"
                    }
                ],
                "alert": {
                    "condition": "value > 0.10",
                    "message": "Zero results rate exceeds 10%"
                }
            },
            {
                "title": "Precision by Product Family",
                "type": "heatmap",
                "datasource": "Prometheus",
                "targets": [
                    {
                        "expr": "avg(search_precision_at_5) by (product_family)"
                    }
                ]
            }
        ]
    }

    return dashboard_config
```

---

## Summary: Quality Verification Checklist

### Week 2-3 (Phase 1)
- [ ] 1K sample cases loaded
- [ ] Golden query set created (50 queries)
- [ ] Embedding generation >99% success
- [ ] Zero PII leaks detected
- [ ] Search API latency <1s
- [ ] Precision@5 >75% (baseline)

### Week 6 (Phase 2)
- [ ] 100K cases loaded successfully
- [ ] GRS team validation completed (50 queries)
- [ ] Precision@5 >85% achieved
- [ ] NDCG@5 >0.85
- [ ] MRR >0.80
- [ ] Validation report published

### Week 7-8 (Phase 3)
- [ ] Hyperparameter tuning completed
- [ ] Regression test suite implemented
- [ ] A/B testing framework deployed
- [ ] Quality metrics dashboard live
- [ ] Production-ready criteria met

---

## References
- Information Retrieval Evaluation Metrics
- NDCG Calculation Methods
- A/B Testing Statistical Significance
- Human Evaluation Best Practices
