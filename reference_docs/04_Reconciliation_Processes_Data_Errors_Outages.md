# Section 4: Reconciliation Processes for Data Errors and Outages

## 4.1 Overview

**Objective**: Implement robust reconciliation and recovery mechanisms to ensure data consistency and completeness across the entire pipeline (SFDC → Staging → Transformation → Weaviate).

**Key Principles**:
- **Idempotency**: Safe to reprocess same data multiple times
- **Auditability**: Full traceability of all data movements
- **Automated Recovery**: Self-healing where possible
- **Data Integrity**: Maintain consistency across all stages

---

## 4.2 Reconciliation Architecture (Multi-Table Enhanced)

### 4.2.1 Multi-Layer Reconciliation Strategy

**Enhanced for 6 SFDC Tables**:
```
┌─────────────────────────────────────────────────────┐
│           SFDC Source (6 Tables)                    │
│  Case │ Task │ WorkOrder │ CaseComments │ Email    │
└─────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│              Staging Layer                          │
│  udp.case │ udp.task │ udp.workorder │ udp.comment │
└─────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│          Multi-Table JOIN & Transformation          │
│  LEFT JOIN 6 tables → Composite Text (44 fields)   │
└─────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│            PII Removal (Context-Aware)              │
│  Table-specific rules for Email, WorkOrder, etc.   │
└─────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│           Embedding Generation                      │
│  ChatHPE 3,072-dim (with Nomic fallback)          │
└─────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│              Weaviate Load                          │
│  1 vector per case (44 fields searchable)          │
└─────────────────────────────────────────────────────┘
                          │
       ┌──────────────────┴──────────────────┐
       │      Reconciliation DB (PostgreSQL)  │
       │  Tracks: Case + Task + WO + Comment  │
       │  Validates: Join completeness        │
       └─────────────────────────────────────┘
```

**Multi-Table Reconciliation Challenges**:
- **Challenge 1**: Not all Cases have Tasks/WorkOrders/Comments
- **Challenge 2**: Join completeness varies (30-80% depending on table)
- **Challenge 3**: Need to track both Case-level AND table-level reconciliation

**Enhanced Reconciliation Database Schema (Multi-Table)**:
```sql
CREATE TABLE data_lineage (
    record_id VARCHAR(255) PRIMARY KEY,
    case_number VARCHAR(255) NOT NULL,
    source_system VARCHAR(50) NOT NULL,
    source_timestamp TIMESTAMP NOT NULL,
    staging_timestamp TIMESTAMP,
    transformed_timestamp TIMESTAMP,
    weaviate_timestamp TIMESTAMP,
    current_stage VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    error_message TEXT,
    retry_count INT DEFAULT 0,
    checksum VARCHAR(64) NOT NULL,

    -- NEW: Multi-table tracking
    has_tasks BOOLEAN DEFAULT FALSE,
    task_count INT DEFAULT 0,
    has_workorders BOOLEAN DEFAULT FALSE,
    workorder_count INT DEFAULT 0,
    has_comments BOOLEAN DEFAULT FALSE,
    comment_count INT DEFAULT 0,
    has_emails BOOLEAN DEFAULT FALSE,
    email_count INT DEFAULT 0,

    -- NEW: Field counts
    total_fields_populated INT DEFAULT 0,
    issue_fields_populated INT DEFAULT 0,
    resolution_fields_populated INT DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- NEW: Multi-table join tracking
CREATE TABLE multi_table_join_stats (
    join_id UUID PRIMARY KEY,
    case_id VARCHAR(255) NOT NULL,
    case_number VARCHAR(255) NOT NULL,
    execution_timestamp TIMESTAMP NOT NULL,

    -- Join results
    case_found BOOLEAN NOT NULL,
    tasks_joined INT DEFAULT 0,
    workorders_joined INT DEFAULT 0,
    comments_joined INT DEFAULT 0,
    emails_joined INT DEFAULT 0,
    workorder_feeds_joined INT DEFAULT 0,

    -- Composite text stats
    composite_text_length INT,
    was_truncated BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_join_stats_case ON multi_table_join_stats(case_id);
CREATE INDEX idx_join_stats_timestamp ON multi_table_join_stats(execution_timestamp);

CREATE TABLE reconciliation_runs (
    run_id UUID PRIMARY KEY,
    run_type VARCHAR(50) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    status VARCHAR(50) NOT NULL,
    source_count INT,
    staging_count INT,
    transformed_count INT,
    weaviate_count INT,
    discrepancies_found INT,
    records_recovered INT,
    error_details JSONB
);

CREATE TABLE failed_records (
    failure_id UUID PRIMARY KEY,
    record_id VARCHAR(255) NOT NULL,
    stage VARCHAR(50) NOT NULL,
    error_type VARCHAR(100) NOT NULL,
    error_message TEXT NOT NULL,
    payload JSONB,
    failed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    retry_count INT DEFAULT 0,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP
);
```

---

## 4.3 Idempotent Pipeline Design

### 4.3.1 Checksum-Based Deduplication

```python
import hashlib
import json

def calculate_record_checksum(record):
    """
    Generate deterministic checksum for case record

    Uses: caseId + createdDate + lastModifiedDate
    Ensures same input always produces same checksum
    """
    # Extract key fields for checksum
    key_fields = {
        'Id': record.get('Id'),
        'CaseNumber': record.get('CaseNumber'),
        'CreatedDate': record.get('CreatedDate'),
        'LastModifiedDate': record.get('LastModifiedDate'),
        'Subject': record.get('Subject'),
        'Description': record.get('Description'),
        'Resolution__c': record.get('Resolution__c')
    }

    # Sort keys for consistency
    canonical_json = json.dumps(key_fields, sort_keys=True)

    # Generate SHA256 hash
    checksum = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()

    return checksum

def is_record_processed(record_id, checksum):
    """
    Check if record with this checksum already processed
    """
    query = """
        SELECT checksum, current_stage, status
        FROM data_lineage
        WHERE record_id = %s
    """

    result = db.execute(query, (record_id,))

    if not result:
        return False  # Never seen before

    existing_checksum = result[0]['checksum']

    if existing_checksum == checksum:
        # Same version already processed
        if result[0]['status'] == 'completed':
            logger.info(f"Record {record_id} already processed (checksum match)")
            return True
        else:
            # Incomplete processing, allow retry
            return False
    else:
        # Different version, needs reprocessing
        logger.info(f"Record {record_id} has new version (checksum changed)")
        return False
```

### 4.3.2 Idempotent Airflow DAG

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'algoleap',
    'depends_on_past': False,
    'start_date': datetime(2024, 11, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=4)
}

dag = DAG(
    'case_vector_pipeline_idempotent',
    default_args=default_args,
    description='Idempotent case vectorization pipeline',
    schedule_interval='0 */6 * * *',  # Every 6 hours
    catchup=False,
    max_active_runs=1
)

def extract_from_staging(**context):
    """
    Extract new/updated cases from staging with idempotency checks
    """
    execution_date = context['execution_date']
    run_id = context['run_id']

    # Get last successful run timestamp
    last_run_ts = get_last_successful_run_timestamp()

    # Extract cases modified since last run
    query = f"""
        SELECT *
        FROM staging.sfdc_cases
        WHERE LastModifiedDate > '{last_run_ts}'
    """

    df_new_cases = pd.read_sql(query, staging_conn)

    logger.info(f"Extracted {len(df_new_cases)} cases since {last_run_ts}")

    # Filter out already-processed cases (checksum match)
    df_to_process = []
    for idx, row in df_new_cases.iterrows():
        record_id = row['Id']
        checksum = calculate_record_checksum(row)

        if not is_record_processed(record_id, checksum):
            df_to_process.append(row)

            # Track in lineage
            upsert_lineage_record(
                record_id=record_id,
                case_number=row['CaseNumber'],
                source_system='SFDC',
                source_timestamp=row['LastModifiedDate'],
                current_stage='extracted',
                status='in_progress',
                checksum=checksum
            )

    df_final = pd.DataFrame(df_to_process)
    logger.info(f"After dedup: {len(df_final)} cases to process")

    # Save to processing queue
    df_final.to_parquet(f'/tmp/processing_queue_{run_id}.parquet')

    return len(df_final)

def pii_removal(**context):
    """
    PII removal with error handling and tracking
    """
    run_id = context['run_id']

    df_cases = pd.read_parquet(f'/tmp/processing_queue_{run_id}.parquet')

    processed_records = []
    failed_records = []

    for idx, row in df_cases.iterrows():
        try:
            # Remove PII
            cleaned_record = remove_pii_from_record(row)

            processed_records.append(cleaned_record)

            # Update lineage
            update_lineage_stage(
                record_id=row['Id'],
                current_stage='pii_removed',
                status='in_progress'
            )

        except Exception as e:
            logger.error(f"PII removal failed for {row['Id']}: {e}")

            failed_records.append({
                'record_id': row['Id'],
                'stage': 'pii_removal',
                'error_type': type(e).__name__,
                'error_message': str(e),
                'payload': row.to_dict()
            })

            # Track failure
            log_failed_record(
                record_id=row['Id'],
                stage='pii_removal',
                error_type=type(e).__name__,
                error_message=str(e),
                payload=row.to_dict()
            )

    # Save processed and failed separately
    pd.DataFrame(processed_records).to_parquet(f'/tmp/pii_cleaned_{run_id}.parquet')

    logger.info(f"PII removal: {len(processed_records)} success, {len(failed_records)} failed")

    if len(failed_records) > len(df_cases) * 0.05:  # >5% failure rate
        raise Exception(f"PII removal failure rate too high: {len(failed_records)}/{len(df_cases)}")

def generate_embeddings(**context):
    """
    Generate embeddings with retry and fallback logic
    """
    run_id = context['run_id']

    df_cases = pd.read_parquet(f'/tmp/pii_cleaned_{run_id}.parquet')

    # Prepare composite texts
    composite_texts = [prepare_embedding_text(row) for _, row in df_cases.iterrows()]

    # Batch embedding generation with retry
    embeddings = []
    for i in range(0, len(composite_texts), 100):  # Batch size 100
        batch = composite_texts[i:i+100]
        batch_ids = df_cases.iloc[i:i+100]['Id'].tolist()

        retry_count = 0
        max_retries = 3

        while retry_count < max_retries:
            try:
                # Try ChatHPE embeddings
                batch_embeddings = generate_embedding_batch(batch, model='chathpe')
                embeddings.extend(batch_embeddings)

                # Update lineage for successful records
                for record_id in batch_ids:
                    update_lineage_stage(
                        record_id=record_id,
                        current_stage='embedding_generated',
                        status='in_progress'
                    )

                break  # Success, exit retry loop

            except Exception as e:
                retry_count += 1
                logger.warning(f"Embedding batch {i//100} failed (attempt {retry_count}): {e}")

                if retry_count >= max_retries:
                    # Fallback to Nomic
                    logger.info(f"Falling back to Nomic embeddings for batch {i//100}")
                    try:
                        batch_embeddings = generate_embedding_batch(batch, model='nomic')
                        embeddings.extend(batch_embeddings)

                        # Update lineage
                        for record_id in batch_ids:
                            update_lineage_stage(
                                record_id=record_id,
                                current_stage='embedding_generated',
                                status='in_progress',
                                metadata={'embedding_model': 'nomic_fallback'}
                            )

                    except Exception as fallback_error:
                        logger.error(f"Fallback embedding also failed: {fallback_error}")

                        # Log failures
                        for record_id in batch_ids:
                            log_failed_record(
                                record_id=record_id,
                                stage='embedding_generation',
                                error_type='EmbeddingFailure',
                                error_message=str(fallback_error)
                            )

                        # Skip this batch
                        embeddings.extend([None] * len(batch))
                else:
                    # Exponential backoff
                    time.sleep(2 ** retry_count)

    # Add embeddings to dataframe
    df_cases['embedding'] = embeddings

    # Filter out failed embeddings
    df_success = df_cases[df_cases['embedding'].notna()]

    df_success.to_parquet(f'/tmp/with_embeddings_{run_id}.parquet')

    logger.info(f"Embeddings: {len(df_success)} success, {len(df_cases) - len(df_success)} failed")

def load_to_weaviate(**context):
    """
    Load to Weaviate with upsert logic
    """
    run_id = context['run_id']

    df_cases = pd.read_parquet(f'/tmp/with_embeddings_{run_id}.parquet')

    client = get_weaviate_client()

    success_count = 0
    failure_count = 0

    with client.batch(
        batch_size=100,
        dynamic=True,
        timeout_retries=3,
        callback=lambda results: handle_batch_results(results)
    ) as batch:

        for idx, row in df_cases.iterrows():
            try:
                # Upsert logic: check if exists, then update or create
                existing = check_if_exists_in_weaviate(row['CaseNumber'])

                properties = prepare_weaviate_properties(row)

                if existing:
                    # Update existing
                    client.data_object.update(
                        uuid=existing['id'],
                        class_name='CaseVectorized',
                        data_object=properties,
                        vector=row['embedding']
                    )
                else:
                    # Create new
                    batch.add_data_object(
                        data_object=properties,
                        class_name='CaseVectorized',
                        vector=row['embedding']
                    )

                # Update lineage
                update_lineage_stage(
                    record_id=row['Id'],
                    current_stage='weaviate_loaded',
                    status='completed',
                    weaviate_timestamp=datetime.now()
                )

                success_count += 1

            except Exception as e:
                logger.error(f"Weaviate load failed for {row['Id']}: {e}")

                log_failed_record(
                    record_id=row['Id'],
                    stage='weaviate_load',
                    error_type=type(e).__name__,
                    error_message=str(e)
                )

                failure_count += 1

    logger.info(f"Weaviate load: {success_count} success, {failure_count} failed")

    return success_count

# Define DAG tasks
extract_task = PythonOperator(
    task_id='extract_from_staging',
    python_callable=extract_from_staging,
    dag=dag
)

pii_task = PythonOperator(
    task_id='pii_removal',
    python_callable=pii_removal,
    dag=dag
)

embedding_task = PythonOperator(
    task_id='generate_embeddings',
    python_callable=generate_embeddings,
    dag=dag
)

load_task = PythonOperator(
    task_id='load_to_weaviate',
    python_callable=load_to_weaviate,
    dag=dag
)

reconcile_task = PythonOperator(
    task_id='reconciliation_check',
    python_callable=run_reconciliation_check,
    dag=dag
)

# Task dependencies
extract_task >> pii_task >> embedding_task >> load_task >> reconcile_task
```

---

## 4.4 Reconciliation Jobs

### 4.4.1 Daily Reconciliation Job

```python
def run_reconciliation_check(**context):
    """
    Comprehensive reconciliation check across all stages
    ENHANCED: Multi-table join validation

    Compares record counts at each stage and identifies gaps
    Validates multi-table join completeness
    """
    run_id = str(uuid.uuid4())
    start_time = datetime.now()

    logger.info(f"Starting multi-table reconciliation run {run_id}")

    # Step 1: Count records at each stage
    counts = {}

    # Source count (SFDC via staging) - PRIMARY TABLE
    counts['source_cases'] = get_staging_count('case')

    # NEW: Secondary table counts
    counts['source_tasks'] = get_staging_count('task')
    counts['source_workorders'] = get_staging_count('workorder')
    counts['source_comments'] = get_staging_count('casecomment')
    counts['source_emails'] = get_staging_count('emailmessage')

    # Lineage tracked records
    counts['lineage_tracked'] = get_lineage_count_by_stage('extracted')
    counts['pii_removed'] = get_lineage_count_by_stage('pii_removed')
    counts['embedding_generated'] = get_lineage_count_by_stage('embedding_generated')
    counts['weaviate_loaded'] = get_lineage_count_by_stage('weaviate_loaded', status='completed')

    # Actual Weaviate count
    counts['weaviate_actual'] = get_weaviate_count()

    # NEW: Multi-table join statistics
    join_stats = get_multi_table_join_statistics()
    counts['cases_with_tasks'] = join_stats['cases_with_tasks']
    counts['cases_with_workorders'] = join_stats['cases_with_workorders']
    counts['cases_with_comments'] = join_stats['cases_with_comments']
    counts['cases_with_emails'] = join_stats['cases_with_emails']

    logger.info(f"Reconciliation counts: {counts}")
    logger.info(f"Multi-table join stats: {join_stats}")

    # Step 2: Identify discrepancies
    discrepancies = []

    # Check 1: Staging → Lineage tracking
    if counts['source'] != counts['lineage_tracked']:
        gap = counts['source'] - counts['lineage_tracked']
        discrepancies.append({
            'type': 'staging_to_lineage_gap',
            'expected': counts['source'],
            'actual': counts['lineage_tracked'],
            'gap': gap,
            'severity': 'high' if gap > 100 else 'medium'
        })

    # Check 2: Pipeline attrition
    expected_completion_rate = 0.95  # 95% of records should complete
    actual_completion_rate = counts['weaviate_loaded'] / counts['lineage_tracked'] if counts['lineage_tracked'] > 0 else 0

    if actual_completion_rate < expected_completion_rate:
        discrepancies.append({
            'type': 'pipeline_attrition',
            'expected_rate': expected_completion_rate,
            'actual_rate': actual_completion_rate,
            'records_lost': counts['lineage_tracked'] - counts['weaviate_loaded'],
            'severity': 'high'
        })

    # Check 3: Weaviate lineage vs actual
    if counts['weaviate_loaded'] != counts['weaviate_actual']:
        gap = counts['weaviate_loaded'] - counts['weaviate_actual']
        discrepancies.append({
            'type': 'weaviate_lineage_mismatch',
            'lineage_count': counts['weaviate_loaded'],
            'actual_count': counts['weaviate_actual'],
            'gap': gap,
            'severity': 'critical' if abs(gap) > 1000 else 'medium'
        })

    # Step 3: Find missing records
    missing_records = find_missing_records()

    # Step 4: Attempt auto-recovery
    recovery_results = attempt_auto_recovery(missing_records)

    # Step 5: Save reconciliation run
    end_time = datetime.now()

    save_reconciliation_run({
        'run_id': run_id,
        'run_type': 'daily',
        'start_time': start_time,
        'end_time': end_time,
        'status': 'completed',
        'source_count': counts['source'],
        'staging_count': counts['lineage_tracked'],
        'transformed_count': counts['embedding_generated'],
        'weaviate_count': counts['weaviate_actual'],
        'discrepancies_found': len(discrepancies),
        'records_recovered': recovery_results['recovered_count'],
        'error_details': {
            'discrepancies': discrepancies,
            'recovery_results': recovery_results
        }
    })

    # Step 6: Alert if critical issues
    critical_discrepancies = [d for d in discrepancies if d['severity'] == 'critical']
    if critical_discrepancies:
        send_alert(
            severity='critical',
            subject='Critical Data Reconciliation Issues',
            message=f"Found {len(critical_discrepancies)} critical discrepancies in reconciliation run {run_id}",
            details=critical_discrepancies
        )

    return {
        'run_id': run_id,
        'discrepancies': len(discrepancies),
        'recovered': recovery_results['recovered_count']
    }

def find_missing_records():
    """
    Identify records that didn't complete pipeline
    """
    query = """
        SELECT record_id, case_number, current_stage, status, error_message
        FROM data_lineage
        WHERE status != 'completed'
        AND created_at < NOW() - INTERVAL '24 hours'
        ORDER BY created_at DESC
    """

    missing = db.execute(query)

    logger.info(f"Found {len(missing)} incomplete records")

    return missing

def attempt_auto_recovery(missing_records):
    """
    Attempt to automatically recover missing records
    """
    recovery_results = {
        'attempted': len(missing_records),
        'recovered_count': 0,
        'failed_count': 0,
        'details': []
    }

    for record in missing_records:
        record_id = record['record_id']
        current_stage = record['current_stage']

        logger.info(f"Attempting recovery for {record_id} stuck at {current_stage}")

        try:
            # Retrieve original record from staging
            original_record = get_record_from_staging(record_id)

            if not original_record:
                logger.warning(f"Record {record_id} not found in staging, cannot recover")
                recovery_results['failed_count'] += 1
                continue

            # Reprocess from failed stage
            if current_stage in ['extracted', 'pii_removed']:
                # Restart from PII removal
                cleaned_record = remove_pii_from_record(original_record)
                composite_text = prepare_embedding_text(cleaned_record)
                embedding = generate_embedding(composite_text)

                # Load to Weaviate
                load_record_to_weaviate(cleaned_record, embedding)

                # Update lineage
                update_lineage_stage(
                    record_id=record_id,
                    current_stage='weaviate_loaded',
                    status='completed',
                    weaviate_timestamp=datetime.now()
                )

                recovery_results['recovered_count'] += 1
                logger.info(f"Successfully recovered {record_id}")

            elif current_stage == 'embedding_generated':
                # Just need to load to Weaviate
                # Retrieve from intermediate storage
                record_with_embedding = get_record_from_intermediate_storage(record_id)

                load_record_to_weaviate(
                    record_with_embedding['data'],
                    record_with_embedding['embedding']
                )

                update_lineage_stage(
                    record_id=record_id,
                    current_stage='weaviate_loaded',
                    status='completed',
                    weaviate_timestamp=datetime.now()
                )

                recovery_results['recovered_count'] += 1
                logger.info(f"Successfully recovered {record_id}")

        except Exception as e:
            logger.error(f"Recovery failed for {record_id}: {e}")
            recovery_results['failed_count'] += 1

            recovery_results['details'].append({
                'record_id': record_id,
                'status': 'failed',
                'error': str(e)
            })

    return recovery_results

def get_multi_table_join_statistics():
    """
    NEW: Get statistics on multi-table join coverage
    """
    query = """
        SELECT
            COUNT(DISTINCT case_id) as total_cases,
            SUM(CASE WHEN has_tasks THEN 1 ELSE 0 END) as cases_with_tasks,
            SUM(CASE WHEN has_workorders THEN 1 ELSE 0 END) as cases_with_workorders,
            SUM(CASE WHEN has_comments THEN 1 ELSE 0 END) as cases_with_comments,
            SUM(CASE WHEN has_emails THEN 1 ELSE 0 END) as cases_with_emails,
            AVG(task_count) as avg_tasks_per_case,
            AVG(workorder_count) as avg_workorders_per_case,
            AVG(comment_count) as avg_comments_per_case,
            AVG(total_fields_populated) as avg_fields_populated
        FROM data_lineage
        WHERE status = 'completed'
    """

    result = db.execute(query)[0]

    stats = {
        'total_cases': result['total_cases'],
        'cases_with_tasks': result['cases_with_tasks'],
        'cases_with_workorders': result['cases_with_workorders'],
        'cases_with_comments': result['cases_with_comments'],
        'cases_with_emails': result['cases_with_emails'],
        'task_coverage': result['cases_with_tasks'] / result['total_cases'] if result['total_cases'] > 0 else 0,
        'workorder_coverage': result['cases_with_workorders'] / result['total_cases'] if result['total_cases'] > 0 else 0,
        'comment_coverage': result['cases_with_comments'] / result['total_cases'] if result['total_cases'] > 0 else 0,
        'email_coverage': result['cases_with_emails'] / result['total_cases'] if result['total_cases'] > 0 else 0,
        'avg_tasks_per_case': result['avg_tasks_per_case'],
        'avg_workorders_per_case': result['avg_workorders_per_case'],
        'avg_comments_per_case': result['avg_comments_per_case'],
        'avg_fields_populated': result['avg_fields_populated']
    }

    logger.info(
        f"Multi-table coverage: Tasks={stats['task_coverage']:.1%}, "
        f"WorkOrders={stats['workorder_coverage']:.1%}, "
        f"Comments={stats['comment_coverage']:.1%}, "
        f"Emails={stats['email_coverage']:.1%}"
    )

    return stats
```

### 4.4.2 Weekly Deep Reconciliation

```python
def weekly_deep_reconciliation():
    """
    Comprehensive weekly reconciliation with sampling validation

    - Validates data integrity across all stages
    - Samples records for content verification
    - Checks for data corruption
    """
    run_id = str(uuid.uuid4())
    logger.info(f"Starting weekly deep reconciliation {run_id}")

    issues = []

    # 1. Record count reconciliation (same as daily)
    count_issues = run_reconciliation_check()
    if count_issues['discrepancies'] > 0:
        issues.append({
            'type': 'count_discrepancy',
            'details': count_issues
        })

    # 2. Content integrity sampling
    # Sample 1000 random records and verify content matches across stages
    sample_records = get_random_sample_records(n=1000)

    content_issues = 0
    for record in sample_records:
        # Get from each stage
        staging_version = get_record_from_staging(record['record_id'])
        weaviate_version = get_record_from_weaviate(record['case_number'])

        # Verify key fields match
        if not verify_content_integrity(staging_version, weaviate_version):
            content_issues += 1
            logger.warning(f"Content mismatch for {record['record_id']}")

    if content_issues > 10:  # >1% corruption rate
        issues.append({
            'type': 'content_corruption',
            'sample_size': len(sample_records),
            'corrupted_count': content_issues,
            'corruption_rate': content_issues / len(sample_records)
        })

    # 3. Embedding quality check
    # Verify embeddings have correct dimensions
    embedding_issues = verify_embedding_dimensions()
    if embedding_issues > 0:
        issues.append({
            'type': 'embedding_dimension_error',
            'count': embedding_issues
        })

    # 4. PII leakage check
    # Sample and scan for PII
    pii_leaks = scan_for_pii_leaks(sample_size=500)
    if pii_leaks > 0:
        issues.append({
            'type': 'pii_leakage',
            'leak_count': pii_leaks,
            'severity': 'critical'
        })

    # Generate comprehensive report
    generate_weekly_reconciliation_report(run_id, issues)

    return issues

def verify_content_integrity(staging_record, weaviate_record):
    """
    Verify content hasn't been corrupted during pipeline
    """
    if not staging_record or not weaviate_record:
        return False

    # Check key fields
    fields_to_check = ['CaseNumber', 'Product__c', 'Priority', 'Status']

    for field in fields_to_check:
        staging_value = staging_record.get(field)
        weaviate_value = weaviate_record.get(field.lower())  # Weaviate uses lowercase

        if staging_value != weaviate_value:
            logger.warning(f"Field mismatch on {field}: staging={staging_value}, weaviate={weaviate_value}")
            return False

    # Check PII removal (should not contain emails)
    if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', weaviate_record.get('compositeText', '')):
        logger.error(f"PII detected in Weaviate record {weaviate_record['caseNumber']}")
        return False

    return True
```

---

## 4.5 Outage Recovery Procedures

### 4.5.1 ChatHPE API Outage Recovery

```python
def handle_chathpe_outage():
    """
    Automatic recovery from ChatHPE API outage

    1. Detect outage via circuit breaker
    2. Switch to Nomic embeddings
    3. Queue failed records for reprocessing when ChatHPE recovers
    """
    logger.warning("ChatHPE API outage detected, activating recovery protocol")

    # 1. Mark outage start
    outage_start = datetime.now()
    set_service_status('chathpe', 'down', outage_start)

    # 2. Switch to fallback
    set_embedding_provider('nomic')

    # 3. Continue processing with Nomic
    logger.info("Switched to Nomic embeddings, pipeline continues")

    # 4. Monitor for ChatHPE recovery
    while True:
        time.sleep(60)  # Check every minute

        if check_chathpe_health():
            logger.info("ChatHPE API recovered")
            outage_end = datetime.now()
            set_service_status('chathpe', 'up', outage_end)

            # 5. Optionally reprocess records with ChatHPE
            if should_reprocess_with_chathpe():
                reprocess_nomic_records_with_chathpe(outage_start, outage_end)

            # 6. Switch back to ChatHPE
            set_embedding_provider('chathpe')

            break

def reprocess_nomic_records_with_chathpe(start_time, end_time):
    """
    Reprocess records that used Nomic fallback with ChatHPE
    """
    query = """
        SELECT record_id
        FROM data_lineage
        WHERE embedding_generated_timestamp BETWEEN %s AND %s
        AND metadata->>'embedding_model' = 'nomic_fallback'
    """

    records_to_reprocess = db.execute(query, (start_time, end_time))

    logger.info(f"Reprocessing {len(records_to_reprocess)} records with ChatHPE")

    for record in records_to_reprocess:
        try:
            # Get record
            original = get_record_from_staging(record['record_id'])

            # Generate new embedding with ChatHPE
            composite_text = prepare_embedding_text(original)
            chathpe_embedding = generate_embedding(composite_text, model='chathpe')

            # Update in Weaviate
            update_weaviate_embedding(record['record_id'], chathpe_embedding)

            # Update lineage
            update_lineage_metadata(
                record_id=record['record_id'],
                metadata={'embedding_model': 'chathpe_reprocessed'}
            )

        except Exception as e:
            logger.error(f"Reprocessing failed for {record['record_id']}: {e}")
```

### 4.5.2 Weaviate Cluster Outage Recovery

```python
def handle_weaviate_outage():
    """
    Recovery from Weaviate cluster outage

    1. Detect outage
    2. Queue records for later loading
    3. When cluster recovers, bulk load queued records
    """
    logger.error("Weaviate cluster outage detected")

    outage_start = datetime.now()
    set_service_status('weaviate', 'down', outage_start)

    # Create queue for pending loads
    pending_queue = []

    # Continue pipeline, but store records instead of loading
    while not check_weaviate_health():
        # Process records but queue for loading
        logger.info("Weaviate down, queueing records for later load")

        # Save to persistent queue (e.g., S3, file system)
        save_to_pending_queue(pending_queue)

        time.sleep(60)  # Check every minute

    # Weaviate recovered
    logger.info("Weaviate cluster recovered, loading queued records")

    outage_end = datetime.now()
    set_service_status('weaviate', 'up', outage_end)

    # Bulk load queued records
    load_queued_records_to_weaviate(pending_queue)
```

---

## 4.6 Monitoring and Alerting

### 4.6.1 Reconciliation Alerts

```python
def setup_reconciliation_alerts():
    """
    Configure alerting rules for reconciliation issues
    """
    alert_rules = [
        {
            'name': 'HighPipelineAttrition',
            'condition': 'pipeline_completion_rate < 0.95',
            'severity': 'high',
            'notification_channels': ['slack', 'pagerduty'],
            'message': 'Pipeline completion rate below 95%'
        },
        {
            'name': 'CriticalRecordGap',
            'condition': 'record_gap > 1000',
            'severity': 'critical',
            'notification_channels': ['slack', 'pagerduty', 'email'],
            'message': 'Large gap detected between stages'
        },
        {
            'name': 'PIILeakageDetected',
            'condition': 'pii_leak_count > 0',
            'severity': 'critical',
            'notification_channels': ['slack', 'pagerduty', 'email', 'security_team'],
            'message': 'PII detected in processed data'
        },
        {
            'name': 'ContentCorruption',
            'condition': 'content_corruption_rate > 0.01',
            'severity': 'high',
            'notification_channels': ['slack', 'email'],
            'message': 'Data corruption detected in sampling'
        }
    ]

    return alert_rules
```

---

## Summary: Reconciliation Best Practices

1. **Idempotency First**: Design every step to be safely re-runnable
2. **Track Everything**: Maintain comprehensive lineage for all records
3. **Automate Recovery**: Build self-healing mechanisms for common failures
4. **Monitor Continuously**: Daily reconciliation checks, weekly deep dives
5. **Alert Proactively**: Detect and notify on anomalies before they become critical
6. **Document Failures**: Capture detailed error information for root cause analysis

---

## References
- Apache Airflow Best Practices
- Data Pipeline Idempotency Patterns
- Distributed Systems Reconciliation Strategies
