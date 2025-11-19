#!/usr/bin/env python3
"""
Cleanup Duplicate Records in Weaviate

This script removes duplicate case records, keeping only the latest version of each case.

Current Issue:
- 1,569 total records for 5 unique cases (~314x duplication)
- Caused by multiple DAG runs without upsert logic

Strategy:
1. Fetch all records
2. Group by caseId
3. Keep most recent (highest processedDate) for each case
4. Delete duplicates

Author: KMS Team
Date: 2025-11-19
"""

import weaviate
import os
import sys
from datetime import datetime
from collections import defaultdict
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
WEAVIATE_URL = os.getenv('WEAVIATE_URL', 'u1ju7icbrtesr1bwaa2q.c0.asia-southeast1.gcp.weaviate.cloud')
WEAVIATE_API_KEY = os.getenv('WEAVIATE_API_KEY', 'bUxrNEI5V3lDVjFEWEYyZF9BUDhnbVFuSGEyNWxjVC9zTmpWd04xTVZTSVlKTFZTM0V3RWluRzdyZXhNPV92MjAw')
COLLECTION_NAME = "Case"

def connect_to_weaviate():
    """Connect to Weaviate Cloud instance"""
    try:
        if not WEAVIATE_URL.startswith('http'):
            url = f"https://{WEAVIATE_URL}"
        else:
            url = WEAVIATE_URL

        logger.info(f"Connecting to Weaviate: {url}")
        auth = weaviate.AuthApiKey(api_key=WEAVIATE_API_KEY)
        client = weaviate.Client(url=url, auth_client_secret=auth)

        if client.is_ready():
            logger.info("✓ Connected successfully")
            return client
        else:
            logger.error("✗ Weaviate not ready")
            return None
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        return None


def fetch_all_records(client):
    """Fetch all Case records"""
    logger.info("Fetching all Case records...")

    all_records = []
    offset = 0
    batch_size = 100

    while True:
        try:
            result = (
                client.query
                .get(COLLECTION_NAME, ["caseId", "caseNumber", "processedDate", "subject"])
                .with_additional(["id"])
                .with_limit(batch_size)
                .with_offset(offset)
                .do()
            )

            records = result.get('data', {}).get('Get', {}).get(COLLECTION_NAME, [])

            if not records:
                break

            all_records.extend(records)
            offset += batch_size

            if offset % 500 == 0:
                logger.info(f"  Fetched {offset} records...")

        except Exception as e:
            logger.error(f"Error fetching at offset {offset}: {e}")
            break

    logger.info(f"✓ Fetched {len(all_records)} total records")
    return all_records


def identify_duplicates(records):
    """
    Identify duplicates and determine which to keep

    Returns:
        dict: {
            'keep': list of UUIDs to keep,
            'delete': list of UUIDs to delete
        }
    """
    logger.info("Analyzing duplicates...")

    # Group by caseId
    case_groups = defaultdict(list)
    for record in records:
        case_id = record.get('caseId')
        if case_id:
            case_groups[case_id].append(record)

    logger.info(f"Found {len(case_groups)} unique cases")

    keep_uuids = []
    delete_uuids = []
    stats = {
        'unique_cases': len(case_groups),
        'total_records': len(records),
        'duplicates_found': 0
    }

    for case_id, group in case_groups.items():
        if len(group) == 1:
            # No duplicates
            keep_uuids.append(group[0]['_additional']['id'])
        else:
            # Duplicates found
            stats['duplicates_found'] += len(group) - 1

            # Sort by processedDate (most recent first)
            # If no processedDate, use UUID as tiebreaker for deterministic results
            sorted_group = sorted(
                group,
                key=lambda x: (
                    x.get('processedDate') or '1970-01-01T00:00:00Z',
                    x['_additional']['id']
                ),
                reverse=True
            )

            # Keep the most recent
            keep_record = sorted_group[0]
            delete_records = sorted_group[1:]

            keep_uuids.append(keep_record['_additional']['id'])
            delete_uuids.extend([r['_additional']['id'] for r in delete_records])

            logger.info(f"  Case {case_id}: {len(group)} copies → keeping 1, deleting {len(delete_records)}")

    logger.info(f"\nSummary:")
    logger.info(f"  Total records: {stats['total_records']}")
    logger.info(f"  Unique cases: {stats['unique_cases']}")
    logger.info(f"  Duplicates to delete: {len(delete_uuids)}")
    logger.info(f"  Records to keep: {len(keep_uuids)}")

    return {'keep': keep_uuids, 'delete': delete_uuids}


def delete_duplicates(client, delete_uuids, dry_run=True):
    """
    Delete duplicate records

    Args:
        client: Weaviate client
        delete_uuids: List of UUIDs to delete
        dry_run: If True, don't actually delete (default: True)
    """
    if dry_run:
        logger.warning(f"\n🔍 DRY RUN MODE - Would delete {len(delete_uuids)} records")
        logger.info("To actually delete, run with --no-dry-run flag")
        return {'deleted': 0, 'failed': 0}

    logger.warning(f"\n⚠️  DELETING {len(delete_uuids)} duplicate records...")
    confirm = input("Are you sure? Type 'yes' to continue: ")

    if confirm.lower() != 'yes':
        logger.info("Deletion cancelled")
        return {'deleted': 0, 'failed': 0}

    stats = {'deleted': 0, 'failed': 0}

    for i, uuid in enumerate(delete_uuids, 1):
        try:
            client.data_object.delete(
                uuid=uuid,
                class_name=COLLECTION_NAME
            )
            stats['deleted'] += 1

            if stats['deleted'] % 100 == 0:
                logger.info(f"  Deleted {stats['deleted']}/{len(delete_uuids)} records...")

        except Exception as e:
            stats['failed'] += 1
            logger.error(f"Failed to delete {uuid}: {e}")

    logger.info(f"\n✓ Deletion complete:")
    logger.info(f"  Deleted: {stats['deleted']}")
    logger.info(f"  Failed: {stats['failed']}")

    return stats


def main():
    """Main execution"""
    logger.info("="*70)
    logger.info("Weaviate Duplicate Cleanup Script")
    logger.info("="*70)

    # Check for dry-run flag
    dry_run = '--no-dry-run' not in sys.argv

    # Connect
    client = connect_to_weaviate()
    if not client:
        logger.error("Cannot proceed without Weaviate connection")
        sys.exit(1)

    # Fetch all records
    records = fetch_all_records(client)
    if not records:
        logger.info("No records found")
        sys.exit(0)

    # Identify duplicates
    analysis = identify_duplicates(records)

    # Delete duplicates
    delete_stats = delete_duplicates(client, analysis['delete'], dry_run=dry_run)

    # Final verification
    if not dry_run and delete_stats['deleted'] > 0:
        logger.info("\n" + "="*70)
        logger.info("Verification - fetching updated counts...")

        result = client.query.aggregate(COLLECTION_NAME).with_meta_count().do()
        final_count = result['data']['Aggregate'][COLLECTION_NAME][0]['meta']['count']

        logger.info(f"✓ Final record count: {final_count}")
        logger.info(f"✓ Expected: {len(analysis['keep'])}")

        if final_count == len(analysis['keep']):
            logger.info("✓✓ Success! Counts match.")
        else:
            logger.warning(f"⚠️  Count mismatch: {final_count} vs {len(analysis['keep'])} expected")

    logger.info("="*70)
    logger.info("Cleanup complete")
    logger.info("="*70)


if __name__ == '__main__':
    main()
