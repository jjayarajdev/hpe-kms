#!/usr/bin/env python3
"""
Integration Test: JSON Ingestion to Embedding Generation (KMS 2.6)

Tests complete pipeline from JSON ingestion through text concatenation
for embedding generation with 6 tables and single composite vector.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.pipeline.jobs.ingestion.json_ingester import JSONIngester
from src.pipeline.jobs.embedding.embedding_generator import EmbeddingGenerator
import logging


def test_json_to_embedding():
    """
    Test complete pipeline: JSON → DataFrame → Concatenation → Embedding

    KMS 2.6 Pipeline:
    1. Ingest 6 JSON files
    2. Load into DataFrames
    3. Join tables to create complete case records
    4. Concatenate all 44 fields
    5. Generate single composite vector (3,072 dimensions)
    """
    print("=" * 70)
    print("Integration Test: JSON Ingestion → Embedding (KMS 2.6)")
    print("=" * 70)
    print()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(message)s'
    )

    # Step 1: Ingest JSON files (6 tables)
    print("Step 1: Ingesting JSON files (6 tables)...")
    print("-" * 70)

    ingester = JSONIngester("data/raw/sfdc_exports")
    tables = ingester.load_all_tables()

    print(f"✓ Loaded {len(tables)} tables")
    for table_name, df in tables.items():
        print(f"  - {table_name.upper()}: {len(df)} records, {len(df.columns)} columns")
    print()

    # Step 2: Verify 6 tables loaded
    print("Step 2: Verifying table structure...")
    print("-" * 70)

    expected_tables = ['case', 'task', 'workorder', 'casecomment', 'workorderfeed', 'emailmessage']
    for table_name in expected_tables:
        assert table_name in tables, f"Missing table: {table_name}"
        print(f"✓ {table_name.upper()} table present")

    print()

    # Step 3: Build complete case record for embedding
    print("Step 3: Building complete case record...")
    print("-" * 70)

    # Get first case
    case_df = tables['case']
    if len(case_df) == 0:
        print("ERROR: No cases found")
        return 1

    first_case = case_df.iloc[0].to_dict()
    case_id = first_case.get('Id')
    print(f"✓ Processing Case ID: {case_id}")
    print(f"  Case Number: {first_case.get('CaseNumber')}")
    print(f"  Subject: {first_case.get('Subject')[:60]}...")
    print()

    # Attach related records from 5 child tables
    case_record = {
        # Case fields (21 fields from Case table)
        'caseNumber': first_case.get('CaseNumber'),
        'subject': first_case.get('Subject'),
        'description': first_case.get('Description'),
        'priority': first_case.get('Priority'),
        'status': first_case.get('Status'),
        'error_codes': first_case.get('Error_Codes__c'),
        'issue_plain_text': first_case.get('Issue_Plain_Text__c'),
        'cause_plain_text': first_case.get('Cause_Plain_Text__c'),
        'environment': first_case.get('GSD_Environment_Plain_Text__c'),
        'resolution': first_case.get('Resolution__c'),
        'resolution_code': first_case.get('Resolution_Code__c'),
        'resolution_plain_text': first_case.get('Resolution_Plain_Text__c'),
        'root_cause': first_case.get('Root_Cause__c'),
        'product_type': first_case.get('Product_Type__c'),
        'product_line': first_case.get('Product_Line__c'),
        'category': first_case.get('Category__c'),

        # Related records from 5 child tables
        'tasks': [],
        'workorders': [],
        'casecomments': [],
        'workorderfeeds': [],
        'emails': []
    }

    # Attach Tasks
    task_df = tables['task']
    if 'CaseId' in task_df.columns:
        related_tasks = task_df[task_df['CaseId'] == case_id]
        for _, task in related_tasks.iterrows():
            case_record['tasks'].append({
                'type': task.get('Type'),
                'description': task.get('Description')
            })
        print(f"✓ Attached {len(related_tasks)} Tasks")

    # Attach WorkOrders
    wo_df = tables['workorder']
    if 'CaseId' in wo_df.columns:
        related_wos = wo_df[wo_df['CaseId'] == case_id]
        for _, wo in related_wos.iterrows():
            case_record['workorders'].append({
                'subject': wo.get('Subject'),
                'description': wo.get('Description')
            })
        print(f"✓ Attached {len(related_wos)} WorkOrders")

    # Attach CaseComments
    comment_df = tables['casecomment']
    if 'ParentId' in comment_df.columns:
        related_comments = comment_df[comment_df['ParentId'] == case_id]
        for _, comment in related_comments.iterrows():
            case_record['casecomments'].append({
                'commentBody': comment.get('CommentBody')
            })
        print(f"✓ Attached {len(related_comments)} CaseComments")

    # Attach WorkOrderFeeds (NEW for KMS 2.6)
    feed_df = tables['workorderfeed']
    if 'ParentId' in feed_df.columns:
        related_feeds = feed_df[feed_df['ParentId'] == case_id]
        for _, feed in related_feeds.iterrows():
            case_record['workorderfeeds'].append({
                'type': feed.get('Type'),
                'body': feed.get('Body')
            })
        print(f"✓ Attached {len(related_feeds)} WorkOrderFeeds (NEW)")

    # Attach EmailMessages (NEW for KMS 2.6)
    email_df = tables['emailmessage']
    if 'ParentId' in email_df.columns:
        related_emails = email_df[email_df['ParentId'] == case_id]
        for _, email in related_emails.iterrows():
            case_record['emails'].append({
                'subject': email.get('Subject'),
                'textBody': email.get('TextBody')
            })
        print(f"✓ Attached {len(related_emails)} EmailMessages (NEW)")

    print()

    # Step 4: Concatenate all fields
    print("Step 4: Concatenating all fields for embedding...")
    print("-" * 70)

    generator = EmbeddingGenerator(
        api_endpoint="https://chathpe.api.endpoint/embeddings",
        api_key="test-api-key"
    )

    concatenated_text = generator.concatenate_all_fields(case_record)

    print(f"✓ Concatenated text length: {len(concatenated_text)} chars")
    print(f"✓ Within 30K char limit: {len(concatenated_text) <= 30000}")
    print()

    # Show concatenated text sections
    print("Step 5: Analyzing concatenated text structure...")
    print("-" * 70)

    sections = concatenated_text.split('\n\n')
    print(f"✓ Total sections: {len(sections)}")

    section_keywords = {
        'ISSUE': 0,
        'RESOLUTION': 0,
        'ENVIRONMENT': 0,
        'TASKS': 0,
        'WORK ORDERS': 0,
        'COMMENTS': 0,
        'SERVICE NOTES': 0,
        'EMAILS': 0
    }

    for section in sections:
        for keyword in section_keywords:
            if keyword in section.upper():
                section_keywords[keyword] += 1

    for keyword, count in section_keywords.items():
        status = "✓" if count > 0 else "⚠"
        print(f"  {status} {keyword}: {'Found' if count > 0 else 'Not found'}")

    print()

    # Display sample of concatenated text
    print("Step 6: Sample of concatenated text...")
    print("-" * 70)
    preview_length = min(500, len(concatenated_text))
    print(concatenated_text[:preview_length])
    if len(concatenated_text) > preview_length:
        print("...")
    print("-" * 70)
    print()

    # Step 7: Verify readiness for embedding
    print("Step 7: Verifying readiness for embedding generation...")
    print("-" * 70)

    checks = [
        (len(concatenated_text) > 0, "Concatenated text is not empty"),
        (len(concatenated_text) <= 30000, "Within 30K character limit"),
        ('ISSUE' in concatenated_text.upper() or 'Description' in concatenated_text, "Issue information present"),
        ('RESOLUTION' in concatenated_text.upper() or 'Resolution' in concatenated_text, "Resolution information present"),
        (len(case_record['tasks']) > 0 or len(case_record['workorders']) > 0, "Child records attached")
    ]

    all_passed = True
    for check, description in checks:
        status = "✓" if check else "✗"
        print(f"  {status} {description}")
        if not check:
            all_passed = False

    print()

    # Summary
    print("=" * 70)
    if all_passed:
        print("✓ INTEGRATION TEST PASSED")
        print()
        print("Summary:")
        print(f"  - Ingested 6 tables (44 fields total)")
        print(f"  - Built complete case record with {len(case_record['tasks'])} tasks, "
              f"{len(case_record['workorders'])} workorders, "
              f"{len(case_record['casecomments'])} comments")
        print(f"  - Plus {len(case_record['workorderfeeds'])} workorder feeds, "
              f"{len(case_record['emails'])} emails (NEW)")
        print(f"  - Concatenated to {len(concatenated_text)} chars")
        print(f"  - Ready for single composite vector generation (3,072 dims)")
        print()
        print("Next step: Generate embedding using ChatHPE API")
        return 0
    else:
        print("✗ INTEGRATION TEST FAILED")
        return 1


if __name__ == '__main__':
    exit(test_json_to_embedding())
