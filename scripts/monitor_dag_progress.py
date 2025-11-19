#!/usr/bin/env python3
"""
Monitor DAG Progress and Weaviate Case Count

Monitors the KMS 2.6 pipeline progress by checking:
1. Weaviate case count
2. Unique caseIds
3. Duplication status

Author: KMS Team
Date: 2025-11-19
"""

import sys
import os
import time

# Add project to path
sys.path.insert(0, '/Users/jjayaraj/workspaces/HPE/KMS')

from src.pipeline.jobs.loading.weaviate_loader import WeaviateLoader
from collections import Counter

# Configuration
WEAVIATE_URL = os.getenv('WEAVIATE_URL', 'u1ju7icbrtesr1bwaa2q.c0.asia-southeast1.gcp.weaviate.cloud')
WEAVIATE_API_KEY = os.getenv('WEAVIATE_API_KEY', 'bUxrNEI5V3lDVjFEWEYyZF9BUDhnbVFuSGEyNWxjVC9zTmpWd04xTVZTSVlKTFZTM0V3RWluRzdyZXhNPV92MjAw')


def get_case_stats(loader):
    """Get detailed case statistics"""
    try:
        # Get total count
        stats = loader.get_collection_stats()
        total_cases = stats['total_cases']

        # Get all caseIds to check for duplicates
        result = (
            loader.client.query
            .get(loader.collection_name, ["caseId"])
            .with_limit(1000)
            .do()
        )

        records = result.get('data', {}).get('Get', {}).get(loader.collection_name, [])
        case_ids = [r['caseId'] for r in records]

        # Count duplicates
        case_counter = Counter(case_ids)
        unique_cases = len(case_counter)
        duplicates = sum(1 for count in case_counter.values() if count > 1)

        return {
            'total': total_cases,
            'unique': unique_cases,
            'duplicates': duplicates,
            'max_duplication': max(case_counter.values()) if case_counter else 0
        }

    except Exception as e:
        print(f"Error getting stats: {e}")
        return None


def main():
    """Monitor progress continuously"""
    print("="*70)
    print("KMS 2.6 PIPELINE PROGRESS MONITOR")
    print("="*70)
    print("Monitoring Weaviate case count and upsert behavior...")
    print("Press Ctrl+C to stop")
    print("="*70)

    # Initialize loader
    auth_config = {'api_key': WEAVIATE_API_KEY}
    loader = WeaviateLoader(weaviate_url=WEAVIATE_URL, auth_config=auth_config)

    iteration = 0
    last_total = 0

    try:
        while True:
            iteration += 1

            # Get stats
            stats = get_case_stats(loader)

            if stats:
                # Calculate change
                delta = stats['total'] - last_total
                delta_str = f"(+{delta})" if delta > 0 else ""

                # Print status
                timestamp = time.strftime("%H:%M:%S")
                print(f"\n[{timestamp}] Update #{iteration}")
                print(f"  Total Records:    {stats['total']} {delta_str}")
                print(f"  Unique Cases:     {stats['unique']}")
                print(f"  Duplicates:       {stats['duplicates']}")
                print(f"  Max Duplication:  {stats['max_duplication']}x")

                # Check upsert effectiveness
                if stats['total'] == stats['unique']:
                    print(f"  Status: ✅ No duplicates (upsert working correctly)")
                else:
                    duplication_rate = (stats['total'] - stats['unique']) / stats['total'] * 100
                    print(f"  Status: ⚠️  {duplication_rate:.1f}% duplication")

                last_total = stats['total']

            # Wait before next check
            time.sleep(5)

    except KeyboardInterrupt:
        print("\n\n" + "="*70)
        print("Monitoring stopped")
        print("="*70)

        # Final stats
        final_stats = get_case_stats(loader)
        if final_stats:
            print("\nFinal Statistics:")
            print(f"  Total Records:    {final_stats['total']}")
            print(f"  Unique Cases:     {final_stats['unique']}")
            print(f"  Duplicates:       {final_stats['duplicates']}")
            print(f"  Max Duplication:  {final_stats['max_duplication']}x")

            if final_stats['total'] == final_stats['unique']:
                print("\n✅✅✅ UPSERT WORKING PERFECTLY - NO DUPLICATES!")
            else:
                print(f"\n⚠️  Found {final_stats['duplicates']} duplicate caseIds")


if __name__ == '__main__':
    main()
