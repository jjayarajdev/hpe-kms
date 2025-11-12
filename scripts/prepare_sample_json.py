#!/usr/bin/env python3
"""
Prepare Sample JSON Files for KMS 2.6

Converts data/kms_2.6_field_mapping.json into separate JSON files
that simulate SFDC exports for 6 tables: Case, Task, WorkOrder, CaseComments,
WorkOrderFeed, EmailMessage.

This creates realistic sample data for testing the JSON ingestion pipeline.
"""

import json
import os
from pathlib import Path
from datetime import datetime


def main():
    print("=" * 60)
    print("Preparing Sample JSON Files (KMS 2.6 - 6 Tables)")
    print("=" * 60)
    print()

    # Load test data
    test_data_path = Path('data/kms_2.6_field_mapping.json')

    if not test_data_path.exists():
        print(f"ERROR: Test data file not found: {test_data_path}")
        print("Please ensure data/kms_2.6_field_mapping.json exists")
        return 1

    with open(test_data_path, 'r', encoding='utf-8') as f:
        spec = json.load(f)

    print(f"✓ Loaded KMS 2.6 specification")
    print(f"  Total Tables: {spec['kms_2.6_spec']['total_tables']}")
    print(f"  Total Fields: {spec['kms_2.6_spec']['total_fields']}")
    print(f"  Vector Strategy: {spec['kms_2.6_spec']['vector_strategy']}")
    print()

    # Extract sample data
    sample_data = spec.get('sample_data', {})

    if not sample_data:
        print("ERROR: No sample_data found in specification")
        return 1

    print(f"Found {len(sample_data)} test case(s)")
    print()

    # Initialize tables
    cases = []
    tasks = []
    workorders = []
    casecomments = []
    workorderfeeds = []
    emailmessages = []

    # Process each test case
    for test_key, test_case in sample_data.items():
        case_name = test_case.get('name', test_key)
        print(f"Processing: {case_name}")

        # Extract Case record
        if 'Case' in test_case:
            case_record = test_case['Case'].copy()
            cases.append(case_record)
            case_id = case_record.get('Id')
            print(f"  ✓ Case: {case_record.get('CaseNumber')}")

            # Extract Task records
            if 'Task' in test_case:
                for task in test_case['Task']:
                    task_record = task.copy()
                    task_record['CaseId'] = case_id
                    tasks.append(task_record)
                print(f"  ✓ Tasks: {len(test_case['Task'])} records")

            # Extract WorkOrder records
            if 'WorkOrder' in test_case:
                for wo in test_case['WorkOrder']:
                    wo_record = wo.copy()
                    wo_record['CaseId'] = case_id
                    workorders.append(wo_record)
                print(f"  ✓ WorkOrders: {len(test_case['WorkOrder'])} records")

            # Extract CaseComment records
            if 'CaseComments' in test_case:
                for comment in test_case['CaseComments']:
                    comment_record = comment.copy()
                    comment_record['ParentId'] = case_id
                    casecomments.append(comment_record)
                print(f"  ✓ CaseComments: {len(test_case['CaseComments'])} records")

            # Extract WorkOrderFeed records (NEW for KMS 2.6)
            if 'WorkOrderFeed' in test_case:
                for feed in test_case['WorkOrderFeed']:
                    feed_record = feed.copy()
                    feed_record['ParentId'] = case_id
                    workorderfeeds.append(feed_record)
                print(f"  ✓ WorkOrderFeed: {len(test_case['WorkOrderFeed'])} records")

            # Extract EmailMessage records (NEW for KMS 2.6)
            if 'EmailMessage' in test_case:
                for email in test_case['EmailMessage']:
                    email_record = email.copy()
                    email_record['ParentId'] = case_id
                    emailmessages.append(email_record)
                print(f"  ✓ EmailMessages: {len(test_case['EmailMessage'])} records")

        print()

    print("=" * 60)
    print("Summary:")
    print(f"  Total Cases: {len(cases)}")
    print(f"  Total Tasks: {len(tasks)}")
    print(f"  Total WorkOrders: {len(workorders)}")
    print(f"  Total CaseComments: {len(casecomments)}")
    print(f"  Total WorkOrderFeeds: {len(workorderfeeds)} (NEW)")
    print(f"  Total EmailMessages: {len(emailmessages)} (NEW)")
    print("=" * 60)
    print()

    # Create output directory
    output_dir = Path('data/raw/sfdc_exports')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save as separate JSON files (simulating SFDC exports)
    tables = {
        'cases': cases,
        'tasks': tasks,
        'workorders': workorders,
        'casecomments': casecomments,
        'workorderfeeds': workorderfeeds,
        'emailmessages': emailmessages
    }

    print("Writing JSON files...")
    print()

    for table_name, records in tables.items():
        # SFDC export format
        output = {
            'records': records,
            'totalSize': len(records),
            'done': True
        }

        output_file = output_dir / f'{table_name}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        status = "✓" if len(records) > 0 else "⚠"
        print(f"  {status} Created {output_file}")
        print(f"    {len(records)} records")

    print()
    print("=" * 60)
    print("✓ Sample JSON files ready for KMS 2.6!")
    print(f"  Location: {output_dir}/")
    print()
    print("Next steps:")
    print("  1. Review generated JSON files")
    print("  2. Validate: python src/pipeline/jobs/ingestion/json_validator.py")
    print("  3. Test ingestion: python src/pipeline/jobs/ingestion/json_ingester.py")
    print("=" * 60)

    return 0


if __name__ == '__main__':
    exit(main())
