#!/usr/bin/env python3
"""
Test Upsert Logic

This script tests the new upsert functionality to ensure:
1. New cases are inserted
2. Existing cases are updated (not duplicated)
3. No duplicate records are created

Test Scenarios:
- Test 1: Insert a new case (should create new record)
- Test 2: Update existing case (should update, not create duplicate)
- Test 3: Batch upsert with mix of new/existing

Author: KMS Team
Date: 2025-11-19
"""

import sys
import os
import logging
from datetime import datetime

# Add project to path
sys.path.insert(0, '/Users/jjayaraj/workspaces/HPE/KMS')

from src.pipeline.jobs.loading.weaviate_loader import WeaviateLoader

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
WEAVIATE_URL = os.getenv('WEAVIATE_URL', 'u1ju7icbrtesr1bwaa2q.c0.asia-southeast1.gcp.weaviate.cloud')
WEAVIATE_API_KEY = os.getenv('WEAVIATE_API_KEY', 'bUxrNEI5V3lDVjFEWEYyZF9BUDhnbVFuSGEyNWxjVC9zTmpWd04xTVZTSVlKTFZTM0V3RWluRzdyZXhNPV92MjAw')


def create_test_case(case_id, subject, update_num=0):
    """Create a test case object with composite vector"""
    import random

    # Generate dummy composite vector (3,072 dims)
    composite_vector = [random.random() for _ in range(3072)]

    case_data = {
        'caseId': case_id,
        'caseNumber': f'TEST{case_id[-6:]}',
        'accountId': '',
        'subject': subject + (f' - Update {update_num}' if update_num > 0 else ''),
        'description': f'Test case for upsert validation (update {update_num})',
        'status': '',
        'priority': '',
        'product': 'Test Product',
        'category': '',
        'productType': '',
        'productLine': '99',
        'errorCodes': '',
        'resolutionCode': '',
        'createdDate': None,
        'closedDate': None,
        'processedDate': datetime.now().isoformat() + 'Z',
        'issuePlainText': 'Test issue',
        'causePlainText': 'Test cause',
        'environment': 'Test environment',
        'resolution': '<p>Test resolution</p>',
        'resolutionPlainText': 'Test resolution',
        'rootCause': 'Test root cause',
        'taskCount': 0,
        'workOrderCount': 0,
        'commentCount': 0,
        'workOrderFeedCount': 0,
        'emailCount': 0,
        'compositeText': f'Test case {case_id} composite text - Update {update_num}',
        'pipelineVersion': '2.6',
        'embeddingModel': 'text-embedding-3-large',
        'composite_vector': composite_vector
    }

    return case_data


def get_case_count(loader):
    """Get current count of cases in Weaviate"""
    try:
        result = loader.client.query.aggregate(loader.collection_name).with_meta_count().do()
        count = result['data']['Aggregate'][loader.collection_name][0]['meta']['count']
        return count
    except:
        return 0


def verify_no_duplicates(loader, case_id):
    """Verify that caseId appears only once"""
    try:
        result = (
            loader.client.query
            .get(loader.collection_name, ["caseId", "subject"])
            .with_where({
                "path": ["caseId"],
                "operator": "Equal",
                "valueString": case_id
            })
            .with_limit(100)
            .do()
        )

        records = result.get('data', {}).get('Get', {}).get(loader.collection_name, [])
        count = len(records)

        if count == 1:
            logger.info(f"  ✓ Case {case_id} appears exactly once (no duplicates)")
            logger.info(f"    Subject: {records[0]['subject']}")
            return True
        elif count == 0:
            logger.error(f"  ✗ Case {case_id} not found!")
            return False
        else:
            logger.error(f"  ✗ Case {case_id} has {count} duplicates!")
            for i, r in enumerate(records, 1):
                logger.error(f"    {i}. {r['subject']}")
            return False
    except Exception as e:
        logger.error(f"  ✗ Error verifying {case_id}: {e}")
        return False


def test_upsert_single():
    """Test 1: Single upsert - insert then update"""
    logger.info("="*70)
    logger.info("TEST 1: Single Upsert (Insert → Update)")
    logger.info("="*70)

    # Initialize loader
    auth_config = {'api_key': WEAVIATE_API_KEY}
    loader = WeaviateLoader(weaviate_url=WEAVIATE_URL, auth_config=auth_config)

    initial_count = get_case_count(loader)
    logger.info(f"Initial record count: {initial_count}")

    test_case_id = "TEST_UPSERT_001"

    # Step 1: Insert new case
    logger.info(f"\nStep 1: Inserting new case {test_case_id}...")
    case_v1 = create_test_case(test_case_id, "Test Upsert Case - Version 1", update_num=0)
    success = loader.upsert_case(case_v1)

    if not success:
        logger.error("✗ Insert failed!")
        return False

    count_after_insert = get_case_count(loader)
    logger.info(f"Record count after insert: {count_after_insert} (expected: {initial_count + 1})")

    if count_after_insert != initial_count + 1:
        logger.error(f"✗ Count mismatch! Expected {initial_count + 1}, got {count_after_insert}")
        return False

    # Verify no duplicates
    if not verify_no_duplicates(loader, test_case_id):
        return False

    # Step 2: Update existing case
    logger.info(f"\nStep 2: Updating existing case {test_case_id}...")
    case_v2 = create_test_case(test_case_id, "Test Upsert Case - Version 2", update_num=1)
    success = loader.upsert_case(case_v2)

    if not success:
        logger.error("✗ Update failed!")
        return False

    count_after_update = get_case_count(loader)
    logger.info(f"Record count after update: {count_after_update} (expected: {count_after_insert})")

    if count_after_update != count_after_insert:
        logger.error(f"✗ Duplicate created! Expected {count_after_insert}, got {count_after_update}")
        return False

    # Verify no duplicates and updated subject
    if not verify_no_duplicates(loader, test_case_id):
        return False

    logger.info("\n✓✓ TEST 1 PASSED: Upsert works correctly (no duplicates)")
    return True


def test_upsert_batch():
    """Test 2: Batch upsert - mix of new and existing"""
    logger.info("\n" + "="*70)
    logger.info("TEST 2: Batch Upsert (New + Existing)")
    logger.info("="*70)

    # Initialize loader
    auth_config = {'api_key': WEAVIATE_API_KEY}
    loader = WeaviateLoader(weaviate_url=WEAVIATE_URL, auth_config=auth_config)

    initial_count = get_case_count(loader)
    logger.info(f"Initial record count: {initial_count}")

    # Create batch with 2 new cases + 1 existing (from Test 1)
    cases = [
        create_test_case("TEST_UPSERT_002", "Test Batch Case 2", update_num=0),
        create_test_case("TEST_UPSERT_003", "Test Batch Case 3", update_num=0),
        create_test_case("TEST_UPSERT_001", "Test Upsert Case - Batch Update", update_num=2),  # Existing
    ]

    logger.info(f"\nUpserting batch of {len(cases)} cases (2 new, 1 update)...")
    stats = loader.upsert_batch(cases)

    logger.info(f"\nBatch results:")
    logger.info(f"  Inserted: {stats['inserted']}")
    logger.info(f"  Updated: {stats['updated']}")
    logger.info(f"  Failed: {stats['failed']}")

    # Verify counts
    final_count = get_case_count(loader)
    expected_count = initial_count + 2  # 2 new cases

    logger.info(f"\nFinal record count: {final_count} (expected: {expected_count})")

    if final_count != expected_count:
        logger.error(f"✗ Count mismatch! Expected {expected_count}, got {final_count}")
        return False

    # Verify no duplicates for each case
    logger.info("\nVerifying no duplicates...")
    all_good = True
    for case in cases:
        if not verify_no_duplicates(loader, case['caseId']):
            all_good = False

    if not all_good:
        return False

    # Check stats
    if stats['inserted'] != 2:
        logger.error(f"✗ Expected 2 inserts, got {stats['inserted']}")
        return False

    if stats['updated'] != 1:
        logger.error(f"✗ Expected 1 update, got {stats['updated']}")
        return False

    if stats['failed'] != 0:
        logger.error(f"✗ Expected 0 failures, got {stats['failed']}")
        return False

    logger.info("\n✓✓ TEST 2 PASSED: Batch upsert works correctly")
    return True


def cleanup_test_cases():
    """Clean up test cases"""
    logger.info("\n" + "="*70)
    logger.info("CLEANUP: Removing test cases")
    logger.info("="*70)

    auth_config = {'api_key': WEAVIATE_API_KEY}
    loader = WeaviateLoader(weaviate_url=WEAVIATE_URL, auth_config=auth_config)

    test_case_ids = ["TEST_UPSERT_001", "TEST_UPSERT_002", "TEST_UPSERT_003"]

    for case_id in test_case_ids:
        try:
            # Find all instances (should be only 1 each)
            result = (
                loader.client.query
                .get(loader.collection_name, ["caseId"])
                .with_where({
                    "path": ["caseId"],
                    "operator": "Equal",
                    "valueString": case_id
                })
                .with_additional(["id"])
                .do()
            )

            records = result.get('data', {}).get('Get', {}).get(loader.collection_name, [])

            for record in records:
                uuid = record['_additional']['id']
                loader.client.data_object.delete(uuid=uuid, class_name=loader.collection_name)
                logger.info(f"  ✓ Deleted {case_id}")

        except Exception as e:
            logger.warning(f"  Failed to delete {case_id}: {e}")

    logger.info("✓ Cleanup complete")


def main():
    """Main test execution"""
    logger.info("="*70)
    logger.info("UPSERT LOGIC TEST SUITE")
    logger.info("="*70)

    all_passed = True

    # Test 1: Single upsert
    if not test_upsert_single():
        logger.error("\n✗✗ TEST 1 FAILED")
        all_passed = False

    # Test 2: Batch upsert
    if not test_upsert_batch():
        logger.error("\n✗✗ TEST 2 FAILED")
        all_passed = False

    # Cleanup
    cleanup_test_cases()

    # Final summary
    logger.info("\n" + "="*70)
    if all_passed:
        logger.info("✓✓✓ ALL TESTS PASSED!")
        logger.info("Upsert logic is working correctly - no duplicates created")
    else:
        logger.error("✗✗✗ SOME TESTS FAILED!")
        logger.error("Review logs above for details")
    logger.info("="*70)

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
