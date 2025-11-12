#!/usr/bin/env python3
"""
Prepare Enhanced Sample JSON Files for Testing KMS 2.6

Generates sample JSON files for all 6 SFDC tables using the comprehensive
test datasets from case-fields-mapping.json

Tables:
1. Case (30+ fields with rich examples)
2. Task (3 fields)
3. WorkOrder (3 fields)
4. CaseComments (1 field)
5. WorkOrderFeed (2 fields) - NEW in 2.6
6. EmailMessage (2 fields) - NEW in 2.6

Uses 5 comprehensive test datasets:
1. DIMM Failure Hardware Issue
2. Storage Array Tape Drive Failure
3. HDD Failure with Storage Degradation
4. 3PAR Storage False Alarm
5. Order Processing Query

Output: data/raw/sfdc_exports/*.json
"""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def extract_test_cases(field_mapping_data):
    """Extract test cases from comprehensive case-fields-mapping.json format"""
    test_cases = []

    # Iterate through all test datasets
    for dataset_key in sorted(field_mapping_data.keys()):
        if not dataset_key.startswith('test_dataset_'):
            continue

        dataset_value = field_mapping_data[dataset_key]
        dataset_name = dataset_value.get('dataset_name', dataset_key)
        sources = dataset_value.get('data_mapping', {}).get('sources', [])

        print(f"\nProcessing: {dataset_name}")

        # Build case data by grouping fields by table
        case_data = {
            'name': dataset_name,
            'Case': {},
            'Task': defaultdict(dict),
            'WorkOrder': defaultdict(dict),
            'CaseComments': [],
            'WorkOrderFeed': defaultdict(dict),
            'EmailMessage': defaultdict(dict)
        }

        # Group fields by table
        for source in sources:
            table = source['source_table']
            field = source['source_field']
            example = source.get('comment_example')

            if example is None:
                continue

            if table == 'Case':
                case_data['Case'][field] = example
            elif table == 'Task':
                # Tasks can have multiple records, use index 0 for now
                case_data['Task'][0][field] = example
            elif table == 'WorkOrder':
                case_data['WorkOrder'][0][field] = example
            elif table == 'CaseComments':
                # Comments are individual records
                case_data['CaseComments'].append({field: example})
            elif table == 'WorkOrderFeed':
                case_data['WorkOrderFeed'][0][field] = example
            elif table == 'EmailMessage':
                case_data['EmailMessage'][0][field] = example

        # Convert defaultdicts to lists
        case_data['Task'] = [dict(v) for v in case_data['Task'].values() if v]
        case_data['WorkOrder'] = [dict(v) for v in case_data['WorkOrder'].values() if v]
        case_data['WorkOrderFeed'] = [dict(v) for v in case_data['WorkOrderFeed'].values() if v]
        case_data['EmailMessage'] = [dict(v) for v in case_data['EmailMessage'].values() if v]

        # Print summary
        print(f"  ✓ Case: {case_data['Case'].get('Case Number', 'N/A')} ({len(case_data['Case'])} fields)")
        print(f"  ✓ Tasks: {len(case_data['Task'])} records")
        print(f"  ✓ WorkOrders: {len(case_data['WorkOrder'])} records")
        print(f"  ✓ CaseComments: {len(case_data['CaseComments'])} records")
        print(f"  ✓ WorkOrderFeeds: {len(case_data['WorkOrderFeed'])} records")
        print(f"  ✓ EmailMessages: {len(case_data['EmailMessage'])} records")

        test_cases.append(case_data)

    return test_cases

def main():
    print("="*70)
    print("Preparing Enhanced Sample JSON Files (KMS 2.6 - 6 Tables)")
    print("Using comprehensive test datasets from case-fields-mapping.json")
    print("="*70)

    # Load comprehensive field mapping with 5 test datasets
    field_mapping_file = Path("data/case-fields-mapping.json")

    if not field_mapping_file.exists():
        print(f"\n❌ Error: Field mapping file not found: {field_mapping_file}")
        print("\nExpected location: data/case-fields-mapping.json")
        return 1

    with open(field_mapping_file, 'r', encoding='utf-8') as f:
        field_mapping = json.load(f)

    # Extract test cases
    test_cases = extract_test_cases(field_mapping)

    if not test_cases:
        print("\n❌ Error: No test cases extracted")
        return 1

    print(f"\n{'='*70}")
    print(f"Extracted {len(test_cases)} test cases")
    print(f"{'='*70}")

    # Initialize tables for all cases
    all_cases = []
    all_tasks = []
    all_workorders = []
    all_casecomments = []
    all_workorderfeeds = []
    all_emailmessages = []

    # Process each test case
    for idx, test_case in enumerate(test_cases, 1):
        case_record = test_case['Case'].copy()
        case_id = case_record.get('Id', f"500Kh{idx:010d}")

        # Ensure Id and CaseNumber exist
        if 'Id' not in case_record:
            case_record['Id'] = case_id
        if 'Case Number' not in case_record:
            case_record['Case Number'] = f"5000{100000 + idx}"

        all_cases.append(case_record)

        # Add Tasks
        for task in test_case.get('Task', []):
            task_record = task.copy()
            task_record['CaseId'] = case_id
            task_record['Id'] = f"00T{idx}{len(all_tasks):06d}"
            all_tasks.append(task_record)

        # Add WorkOrders
        for wo in test_case.get('WorkOrder', []):
            wo_record = wo.copy()
            wo_record['CaseId'] = case_id
            wo_record['Id'] = f"0WO{idx}{len(all_workorders):06d}"
            all_workorders.append(wo_record)

        # Add CaseComments
        for comment in test_case.get('CaseComments', []):
            comment_record = comment.copy()
            comment_record['ParentId'] = case_id
            comment_record['Id'] = f"00a{idx}{len(all_casecomments):06d}"
            all_casecomments.append(comment_record)

        # Add WorkOrderFeeds
        for feed in test_case.get('WorkOrderFeed', []):
            feed_record = feed.copy()
            # WorkOrderFeed links to WorkOrder, not Case
            if all_workorders:
                feed_record['ParentId'] = all_workorders[-1]['Id']
            else:
                feed_record['ParentId'] = case_id
            feed_record['Id'] = f"0D5{idx}{len(all_workorderfeeds):06d}"
            all_workorderfeeds.append(feed_record)

        # Add EmailMessages
        for email in test_case.get('EmailMessage', []):
            email_record = email.copy()
            email_record['ParentId'] = case_id
            email_record['Id'] = f"02s{idx}{len(all_emailmessages):06d}"
            all_emailmessages.append(email_record)

    # Summary
    print(f"\n{'='*70}")
    print("Summary:")
    print(f"  Total Cases: {len(all_cases)}")
    print(f"  Total Tasks: {len(all_tasks)}")
    print(f"  Total WorkOrders: {len(all_workorders)}")
    print(f"  Total CaseComments: {len(all_casecomments)}")
    print(f"  Total WorkOrderFeeds: {len(all_workorderfeeds)} (NEW)")
    print(f"  Total EmailMessages: {len(all_emailmessages)} (NEW)")
    print(f"  Total Records: {len(all_cases) + len(all_tasks) + len(all_workorders) + len(all_casecomments) + len(all_workorderfeeds) + len(all_emailmessages)}")
    print(f"{'='*70}")

    # Create output directory
    output_dir = Path('data/raw/sfdc_exports')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save as separate JSON files (simulating SFDC exports)
    tables = {
        'cases': all_cases,
        'tasks': all_tasks,
        'workorders': all_workorders,
        'casecomments': all_casecomments,
        'workorderfeeds': all_workorderfeeds,
        'emailmessages': all_emailmessages
    }

    print("\nWriting JSON files...")
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
    print("="*70)
    print("✅ Enhanced sample JSON files ready for KMS 2.6!")
    print(f"  Location: {output_dir}/")
    print()
    print("Test Datasets Included:")
    for idx, test_case in enumerate(test_cases, 1):
        print(f"  {idx}. {test_case['name']}")
    print()
    print("Next steps:")
    print("  1. Review generated JSON files")
    print("  2. Run tests: python -m pytest tests/integration/ -v")
    print("  3. Test ingestion: python scripts/ingest_sfdc_json.py")
    print("  4. Test OpenAI embeddings: python scripts/test_openai_embeddings.py")
    print("="*70)

    return 0


if __name__ == '__main__':
    exit(main())
