# Section 7: Early Sample Data Load for API Development and Search Validation

## 7.1 Overview

**Objective**: Enable parallel development and early validation by loading representative sample datasets before the full historical data load.

**Phased Approach**:
- **Phase 1 (Week 2-3)**: 1K cases for dev/test
- **Phase 2 (Week 6)**: 100K cases for GRS validation
- **Phase 3 (Week 9-10)**: Full 1M+ historical load

**Benefits**:
- Frontend developers can build UI against real API
- Search quality can be validated early
- Performance testing at scale before production
- Risk mitigation through incremental rollout

---

## 7.2 Phase 1: Development Sample (1K Cases) - Week 2-3

### 7.2.1 Sample Selection Criteria

```python
def select_dev_sample(df_sfdc_cases, sample_size=1000):
    """
    Select 1K representative cases for development

    Criteria:
    - Diverse product mix (ProLiant, Synergy, Aruba, Storage)
    - Various priority levels (Critical: 10%, High: 30%, Medium: 50%, Low: 10%)
    - Mix of case complexities (simple, moderate, complex)
    - Only closed/resolved cases with good resolutions
    - Recent data (last 3 months)
    - Good quality descriptions (>50 chars)
    """
    import pandas as pd
    from datetime import datetime, timedelta

    # Filter: Closed cases with resolutions from last 3 months
    three_months_ago = datetime.now() - timedelta(days=90)

    df_filtered = df_sfdc_cases[
        (df_sfdc_cases['Status'].isin(['Closed', 'Resolved'])) &
        (df_sfdc_cases['Resolution__c'].notna()) &
        (df_sfdc_cases['Resolution__c'].str.len() > 50) &
        (df_sfdc_cases['Description'].str.len() > 50) &
        (df_sfdc_cases['CreatedDate'] >= three_months_ago.strftime('%Y-%m-%d'))
    ].copy()

    # Add complexity score
    df_filtered['description_length'] = df_filtered['Description'].str.len()
    df_filtered['complexity'] = pd.cut(
        df_filtered['description_length'],
        bins=[0, 200, 800, float('inf')],
        labels=['simple', 'moderate', 'complex']
    )

    # Stratified sampling
    # Target distribution
    product_targets = {
        'ProLiant': 400,
        'Synergy': 200,
        'Aruba': 200,
        'Storage': 100,
        'Other': 100
    }

    priority_targets = {
        'Critical': 100,
        'High': 300,
        'Medium': 500,
        'Low': 100
    }

    samples = []

    # Sample by product family
    for product, target_count in product_targets.items():
        if product == 'Other':
            product_filter = ~df_filtered['Product__c'].str.contains(
                '|'.join(product_targets.keys()),
                case=False,
                na=False
            )
        else:
            product_filter = df_filtered['Product__c'].str.contains(
                product,
                case=False,
                na=False
            )

        product_df = df_filtered[product_filter]

        if len(product_df) > 0:
            # Further stratify by priority and complexity
            sample = product_df.groupby(['Priority', 'complexity'], group_keys=False).apply(
                lambda x: x.sample(min(len(x), target_count // 6))
            ).head(target_count)

            samples.append(sample)

    # Combine all samples
    dev_sample = pd.concat(samples, ignore_index=True).drop_duplicates(subset=['Id'])

    # Ensure we have exactly 1000 (or close to it)
    if len(dev_sample) > sample_size:
        dev_sample = dev_sample.sample(n=sample_size, random_state=42)
    elif len(dev_sample) < sample_size:
        # Fill remaining with random samples
        remaining = sample_size - len(dev_sample)
        additional = df_filtered[~df_filtered['Id'].isin(dev_sample['Id'])].sample(n=remaining, random_state=42)
        dev_sample = pd.concat([dev_sample, additional], ignore_index=True)

    logger.info(f"Dev sample selected: {len(dev_sample)} cases")
    logger.info(f"Product distribution:\n{dev_sample['Product__c'].value_counts().head(10)}")
    logger.info(f"Priority distribution:\n{dev_sample['Priority'].value_counts()}")
    logger.info(f"Complexity distribution:\n{dev_sample['complexity'].value_counts()}")

    return dev_sample
```

### 7.2.2 Dev Sample Load Pipeline

```python
def load_dev_sample_to_weaviate():
    """
    Load 1K dev sample through complete pipeline

    Steps:
    1. Extract from staging
    2. PII removal
    3. Text normalization
    4. Embedding generation
    5. Weaviate load
    6. Validation
    """
    logger.info("Starting dev sample load (1K cases)")

    # Step 1: Select sample
    df_staging = load_staging_data()
    dev_sample = select_dev_sample(df_staging, sample_size=1000)

    # Save sample manifest
    dev_sample[['Id', 'CaseNumber', 'Product__c', 'Priority']].to_csv(
        'samples/dev_sample_manifest.csv',
        index=False
    )

    # Step 2: Process through pipeline
    processed_cases = []

    for idx, case in dev_sample.iterrows():
        try:
            # PII removal
            cleaned_case = process_case_with_pii_removal(case)

            # Text preparation
            composite_text = prepare_embedding_text(cleaned_case)

            # Generate embedding
            embedding = generate_embedding(composite_text)

            # Prepare for Weaviate
            processed_cases.append({
                'case_data': cleaned_case,
                'composite_text': composite_text,
                'embedding': embedding
            })

            logger.info(f"Processed {idx+1}/{len(dev_sample)}: {case['CaseNumber']}")

        except Exception as e:
            logger.error(f"Failed to process {case['CaseNumber']}: {e}")

    # Step 3: Load to Weaviate
    load_count = load_batch_to_weaviate(processed_cases)

    logger.info(f"Dev sample load complete: {load_count}/{len(dev_sample)} cases loaded")

    # Step 4: Validation
    validate_dev_sample_load(dev_sample['CaseNumber'].tolist())

    return load_count

def validate_dev_sample_load(case_numbers):
    """
    Validate dev sample was loaded correctly
    """
    client = get_weaviate_client()

    validation_results = {
        'total_expected': len(case_numbers),
        'found_in_weaviate': 0,
        'missing': [],
        'validation_errors': []
    }

    for case_number in case_numbers:
        # Query Weaviate for case
        result = (
            client.query
            .get('CaseVectorized', ['caseNumber', 'title', 'product'])
            .with_where({
                'path': ['caseNumber'],
                'operator': 'Equal',
                'valueText': case_number
            })
            .do()
        )

        cases = result.get('data', {}).get('Get', {}).get('CaseVectorized', [])

        if cases:
            validation_results['found_in_weaviate'] += 1
        else:
            validation_results['missing'].append(case_number)
            logger.warning(f"Case {case_number} not found in Weaviate")

    # Calculate success rate
    success_rate = validation_results['found_in_weaviate'] / validation_results['total_expected']

    logger.info(f"Validation: {success_rate:.1%} success rate ({validation_results['found_in_weaviate']}/{validation_results['total_expected']})")

    if success_rate < 0.95:
        raise Exception(f"Dev sample load validation failed: only {success_rate:.1%} success rate")

    return validation_results
```

### 7.2.3 Mock API for Frontend Development

```python
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend development

# Mock search endpoint (uses dev sample)
@app.route('/api/v1/search', methods=['POST'])
def mock_search():
    """
    Mock search API for frontend development

    Uses dev sample (1K cases) in Weaviate
    """
    try:
        data = request.get_json()

        query = data.get('query', '')
        filters = data.get('filters', {})
        limit = min(data.get('limit', 10), 50)

        # Validate query
        if not query or len(query) < 3:
            return jsonify({
                'error': 'Query must be at least 3 characters'
            }), 400

        # Execute search on dev sample
        results = hybrid_search(
            query_text=query,
            filters=filters,
            limit=limit,
            alpha=0.75
        )

        # Add mock metadata for UI development
        response = {
            'query': query,
            'filters': filters,
            'resultCount': len(results),
            'results': results,
            'metadata': {
                'searchTimeMs': 234,  # Mock
                'datasetSize': '1K sample',
                'environment': 'development'
            },
            'facets': generate_facets(results) if len(results) > 0 else {}
        }

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Mock search error: {e}")
        return jsonify({'error': str(e)}), 500

# Mock case detail endpoint
@app.route('/api/v1/cases/<case_number>', methods=['GET'])
def get_case_detail(case_number):
    """
    Get detailed case information
    """
    client = get_weaviate_client()

    result = (
        client.query
        .get('CaseVectorized', [
            'caseNumber', 'title', 'description', 'resolutionSummary',
            'product', 'productFamily', 'category', 'priority', 'status',
            'createdDate', 'closedDate'
        ])
        .with_where({
            'path': ['caseNumber'],
            'operator': 'Equal',
            'valueText': case_number
        })
        .do()
    )

    cases = result.get('data', {}).get('Get', {}).get('CaseVectorized', [])

    if not cases:
        return jsonify({'error': 'Case not found'}), 404

    return jsonify(cases[0]), 200

# Health check endpoint
@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """
    Health check for API
    """
    # Check Weaviate connectivity
    try:
        client = get_weaviate_client()
        client.schema.get('CaseVectorized')
        weaviate_status = 'healthy'
    except:
        weaviate_status = 'unhealthy'

    return jsonify({
        'status': 'healthy' if weaviate_status == 'healthy' else 'degraded',
        'components': {
            'api': 'healthy',
            'weaviate': weaviate_status
        },
        'environment': 'development',
        'datasetSize': '1K sample'
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
```

---

## 7.3 Phase 2: Validation Sample (100K Cases) - Week 6

### 7.3.1 100K Sample Selection

```python
def select_validation_sample(df_sfdc_cases, sample_size=100000):
    """
    Select 100K cases for Week 6 GRS validation

    Criteria:
    - Last 3 months of data (recency)
    - All product families proportionally represented
    - Only closed/resolved cases
    - Balanced priority distribution
    - Mix of simple and complex cases
    """
    from datetime import datetime, timedelta

    three_months_ago = datetime.now() - timedelta(days=90)

    # Filter criteria
    df_filtered = df_sfdc_cases[
        (df_sfdc_cases['CreatedDate'] >= three_months_ago.strftime('%Y-%m-%d')) &
        (df_sfdc_cases['Status'].isin(['Closed', 'Resolved'])) &
        (df_sfdc_cases['Resolution__c'].notna()) &
        (df_sfdc_cases['Description'].str.len() > 30)
    ].copy()

    logger.info(f"Filtered pool: {len(df_filtered)} cases")

    # Proportional sampling by product family
    product_counts = df_filtered['Product__c'].value_counts()

    samples_by_product = []

    for product, count in product_counts.items():
        # Calculate proportional sample size
        proportion = count / len(df_filtered)
        product_sample_size = int(sample_size * proportion)

        # Sample from this product
        product_df = df_filtered[df_filtered['Product__c'] == product]

        if len(product_df) >= product_sample_size:
            sample = product_df.sample(n=product_sample_size, random_state=42)
        else:
            sample = product_df  # Take all if fewer than target

        samples_by_product.append(sample)

        logger.info(f"Product {product}: sampled {len(sample)} cases ({proportion:.1%})")

    # Combine samples
    validation_sample = pd.concat(samples_by_product, ignore_index=True)

    # Adjust to exact target size
    if len(validation_sample) > sample_size:
        validation_sample = validation_sample.sample(n=sample_size, random_state=42)
    elif len(validation_sample) < sample_size:
        # Fill with random additional cases
        remaining = sample_size - len(validation_sample)
        additional = df_filtered[~df_filtered['Id'].isin(validation_sample['Id'])].sample(
            n=remaining,
            random_state=42
        )
        validation_sample = pd.concat([validation_sample, additional], ignore_index=True)

    logger.info(f"Validation sample: {len(validation_sample)} cases")

    # Save manifest
    validation_sample[['Id', 'CaseNumber', 'Product__c', 'Priority', 'CreatedDate']].to_csv(
        'samples/validation_sample_100k_manifest.csv',
        index=False
    )

    return validation_sample
```

### 7.3.2 Performance Testing at 100K Scale

```python
def run_performance_tests_100k():
    """
    Performance testing with 100K dataset

    Tests:
    - Query latency (p50, p95, p99)
    - Throughput (concurrent requests)
    - Index size and memory usage
    - Filter performance
    """
    test_results = {
        'query_latency': {},
        'throughput': {},
        'resource_usage': {}
    }

    # Test 1: Query latency with various query types
    logger.info("Test 1: Query Latency")

    test_queries = [
        "server boot failure",
        "network connectivity timeout",
        "disk failure SMART error",
        "firmware update failed",
        "memory error POST code"
    ]

    latencies = []
    for query in test_queries:
        start = time.time()
        results = hybrid_search(query, filters=None, limit=10, alpha=0.75)
        latency = time.time() - start
        latencies.append(latency)

        logger.info(f"Query: '{query}' → {latency:.3f}s, {len(results)} results")

    test_results['query_latency'] = {
        'p50': np.percentile(latencies, 50),
        'p95': np.percentile(latencies, 95),
        'p99': np.percentile(latencies, 99),
        'mean': np.mean(latencies)
    }

    # Test 2: Concurrent query throughput
    logger.info("Test 2: Concurrent Throughput")

    from concurrent.futures import ThreadPoolExecutor, as_completed

    def run_search_query(query_id):
        query = test_queries[query_id % len(test_queries)]
        start = time.time()
        hybrid_search(query, filters=None, limit=5, alpha=0.75)
        return time.time() - start

    # Simulate 50 concurrent users
    concurrent_users = 50
    queries_per_user = 10

    with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
        futures = [
            executor.submit(run_search_query, i)
            for i in range(concurrent_users * queries_per_user)
        ]

        latencies_concurrent = [f.result() for f in as_completed(futures)]

    test_results['throughput'] = {
        'concurrent_users': concurrent_users,
        'total_queries': len(latencies_concurrent),
        'mean_latency': np.mean(latencies_concurrent),
        'p95_latency': np.percentile(latencies_concurrent, 95),
        'queries_per_second': len(latencies_concurrent) / sum(latencies_concurrent)
    }

    # Test 3: Filter performance
    logger.info("Test 3: Filter Performance")

    filter_tests = [
        {'product': 'ProLiant DL380'},
        {'priority': ['High', 'Critical']},
        {'productFamily': 'ProLiant', 'status': 'Closed'},
        {'dateRange': {'start': '2024-10-01', 'end': '2024-12-31'}}
    ]

    filter_latencies = []
    for filters in filter_tests:
        start = time.time()
        results = hybrid_search("server issue", filters=filters, limit=10, alpha=0.75)
        latency = time.time() - start
        filter_latencies.append(latency)

        logger.info(f"Filters: {filters} → {latency:.3f}s, {len(results)} results")

    test_results['filter_performance'] = {
        'mean_latency': np.mean(filter_latencies),
        'max_latency': max(filter_latencies)
    }

    # Test 4: Resource usage
    logger.info("Test 4: Resource Usage")

    client = get_weaviate_client()

    # Get Weaviate metrics
    # (This depends on Weaviate version and available metrics endpoint)

    test_results['resource_usage'] = {
        'weaviate_objects': get_weaviate_count(),
        'index_size_mb': get_weaviate_index_size_mb(),
        'memory_usage_mb': get_weaviate_memory_usage_mb()
    }

    # Generate report
    generate_performance_report(test_results)

    return test_results

def generate_performance_report(test_results):
    """
    Generate performance test report
    """
    report = f"""
# Performance Test Report - 100K Dataset
**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Dataset Size**: 100,000 cases

## Query Latency

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| p50 | {test_results['query_latency']['p50']:.3f}s | <0.5s | {'✓ PASS' if test_results['query_latency']['p50'] < 0.5 else '✗ FAIL'} |
| p95 | {test_results['query_latency']['p95']:.3f}s | <1.0s | {'✓ PASS' if test_results['query_latency']['p95'] < 1.0 else '✗ FAIL'} |
| p99 | {test_results['query_latency']['p99']:.3f}s | <2.0s | {'✓ PASS' if test_results['query_latency']['p99'] < 2.0 else '✗ FAIL'} |
| Mean | {test_results['query_latency']['mean']:.3f}s | <0.75s | {'✓ PASS' if test_results['query_latency']['mean'] < 0.75 else '✗ FAIL'} |

## Concurrent Throughput

- **Concurrent Users**: {test_results['throughput']['concurrent_users']}
- **Total Queries**: {test_results['throughput']['total_queries']}
- **Mean Latency**: {test_results['throughput']['mean_latency']:.3f}s
- **p95 Latency**: {test_results['throughput']['p95_latency']:.3f}s
- **Queries/Second**: {test_results['throughput']['queries_per_second']:.1f}

## Filter Performance

- **Mean Latency**: {test_results['filter_performance']['mean_latency']:.3f}s
- **Max Latency**: {test_results['filter_performance']['max_latency']:.3f}s

## Resource Usage

- **Weaviate Objects**: {test_results['resource_usage']['weaviate_objects']:,}
- **Index Size**: {test_results['resource_usage']['index_size_mb']:.1f} MB
- **Memory Usage**: {test_results['resource_usage']['memory_usage_mb']:.1f} MB

---
**Conclusion**: {'All performance targets met ✓' if all([
    test_results['query_latency']['p95'] < 1.0,
    test_results['throughput']['p95_latency'] < 2.0
]) else 'Performance tuning required ⚠'}
"""

    with open(f'reports/performance_test_100k_{datetime.now().strftime("%Y%m%d")}.md', 'w') as f:
        f.write(report)

    logger.info("Performance report saved")

    return report
```

---

## 7.4 Phase 3: Full Historical Load (1M+ Cases) - Week 9-10

### 7.4.1 Incremental Load Strategy

```python
def load_full_historical_data():
    """
    Load full 1-year historical data (~1M+ cases)

    Strategy:
    - Load in daily batches (2740 cases/day average)
    - Monitor performance and errors
    - Pause/resume capability
    - Progress tracking
    """
    logger.info("Starting full historical data load")

    # Get date range (1 year)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    # Load in daily batches
    current_date = start_date

    while current_date <= end_date:
        batch_start = current_date
        batch_end = current_date + timedelta(days=1)

        logger.info(f"Loading batch: {batch_start.strftime('%Y-%m-%d')} to {batch_end.strftime('%Y-%m-%d')}")

        try:
            # Get cases for this date range
            batch_cases = get_cases_by_date_range(batch_start, batch_end)

            if len(batch_cases) > 0:
                # Process batch through pipeline
                process_and_load_batch(batch_cases)

                logger.info(f"Batch complete: {len(batch_cases)} cases processed")
            else:
                logger.info(f"No cases for {batch_start.strftime('%Y-%m-%d')}")

        except Exception as e:
            logger.error(f"Batch failed for {batch_start.strftime('%Y-%m-%d')}: {e}")

            # Retry logic
            # ... (implement retry with exponential backoff)

        # Move to next day
        current_date += timedelta(days=1)

        # Progress tracking
        progress = (current_date - start_date) / (end_date - start_date)
        logger.info(f"Overall progress: {progress:.1%}")

    logger.info("Full historical load complete")

def get_cases_by_date_range(start_date, end_date):
    """
    Get cases from staging for date range
    """
    query = f"""
        SELECT *
        FROM staging.sfdc_cases
        WHERE CreatedDate >= '{start_date.strftime('%Y-%m-%d')}'
        AND CreatedDate < '{end_date.strftime('%Y-%m-%d')}'
    """

    df_cases = pd.read_sql(query, staging_conn)

    return df_cases
```

---

## Summary: Sample Data Load Strategy

| Phase | Week | Size | Purpose | Success Criteria |
|-------|------|------|---------|------------------|
| **Dev Sample** | 2-3 | 1K | API development, schema validation | >99% load success, API functional |
| **Validation Sample** | 6 | 100K | GRS validation, performance testing | >85% precision@5, <1s p95 latency |
| **Full Historical** | 9-10 | 1M+ | Production deployment | >95% load success, all metrics met |

---

## References
- Stratified Sampling Techniques
- Performance Testing Best Practices
- Progressive Enhancement Deployment
