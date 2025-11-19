#!/usr/bin/env python3
"""
Test Delete and Stats Methods

Tests the newly implemented methods:
1. get_collection_stats() - Get collection statistics
2. delete_case() - Delete case by caseId
3. get_schema_info() - Get schema information

Author: KMS Team
Date: 2025-11-19
"""

import sys
import os
import logging

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


def test_get_collection_stats():
    """Test 1: Get collection statistics"""
    logger.info("="*70)
    logger.info("TEST 1: Get Collection Stats")
    logger.info("="*70)

    # Initialize loader
    auth_config = {'api_key': WEAVIATE_API_KEY}
    loader = WeaviateLoader(weaviate_url=WEAVIATE_URL, auth_config=auth_config)

    # Get stats
    stats = loader.get_collection_stats()

    logger.info(f"\nCollection Stats:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")

    # Verify
    if 'total_cases' in stats and isinstance(stats['total_cases'], int):
        logger.info("\n✓✓ TEST 1 PASSED: Stats retrieval working")
        return True
    else:
        logger.error("\n✗✗ TEST 1 FAILED: Invalid stats format")
        return False


def test_get_schema_info():
    """Test 2: Get schema information"""
    logger.info("\n" + "="*70)
    logger.info("TEST 2: Get Schema Info")
    logger.info("="*70)

    # Initialize loader
    auth_config = {'api_key': WEAVIATE_API_KEY}
    loader = WeaviateLoader(weaviate_url=WEAVIATE_URL, auth_config=auth_config)

    # Get schema
    schema_info = loader.get_schema_info()

    logger.info(f"\nSchema Info:")
    for key, value in schema_info.items():
        if key != 'full_schema':  # Skip full schema (too verbose)
            logger.info(f"  {key}: {value}")

    # Verify
    if 'class' in schema_info and schema_info['class'] == 'Case':
        logger.info("\n✓✓ TEST 2 PASSED: Schema retrieval working")
        return True
    else:
        logger.error("\n✗✗ TEST 2 FAILED: Invalid schema format")
        return False


def test_delete_case():
    """Test 3: Delete case (optional - only if test cases exist)"""
    logger.info("\n" + "="*70)
    logger.info("TEST 3: Delete Case (Optional)")
    logger.info("="*70)

    # Initialize loader
    auth_config = {'api_key': WEAVIATE_API_KEY}
    loader = WeaviateLoader(weaviate_url=WEAVIATE_URL, auth_config=auth_config)

    # Try to delete a non-existent case (should return False gracefully)
    fake_case_id = "NONEXISTENT_CASE_12345"
    result = loader.delete_case(fake_case_id)

    if result == False:
        logger.info(f"\n✓✓ TEST 3 PASSED: Delete handles non-existent case correctly")
        return True
    else:
        logger.warning(f"\n⚠️  TEST 3: Unexpected result (expected False for non-existent case)")
        return False


def main():
    """Main test execution"""
    logger.info("="*70)
    logger.info("DELETE & STATS METHODS TEST SUITE")
    logger.info("="*70)

    all_passed = True

    # Test 1: Get collection stats
    if not test_get_collection_stats():
        all_passed = False

    # Test 2: Get schema info
    if not test_get_schema_info():
        all_passed = False

    # Test 3: Delete case
    if not test_delete_case():
        all_passed = False

    # Final summary
    logger.info("\n" + "="*70)
    if all_passed:
        logger.info("✓✓✓ ALL TESTS PASSED!")
        logger.info("All new methods (get_collection_stats, delete_case, get_schema_info) are working correctly")
    else:
        logger.error("✗✗✗ SOME TESTS FAILED!")
        logger.error("Review logs above for details")
    logger.info("="*70)

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
