#!/usr/bin/env python3
"""
Reset Weaviate Schema for Multi-Table Implementation

This script:
1. Deletes the existing Case collection
2. Creates new schema with 49 properties (44 SFDC + 5 enriched)
3. Supports 6-table architecture (Case + 5 child tables)

Author: KMS Team
Date: 2025-11-19
"""

import sys
import os
import logging

# Add project to path
sys.path.insert(0, '/Users/jjayaraj/workspaces/HPE/KMS')

import weaviate
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
WEAVIATE_URL = os.getenv('WEAVIATE_URL', 'u1ju7icbrtesr1bwaa2q.c0.asia-southeast1.gcp.weaviate.cloud')
WEAVIATE_API_KEY = os.getenv('WEAVIATE_API_KEY', 'bUxrNEI5V3lDVjFEWEYyZF9BUDhnbVFuSGEyNWxjVC9zTmpWd04xTVZTSVlKTFZTM0V3RWluRzdyZXhNPV92MjAw')


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


def delete_existing_schema(client, force=False):
    """Delete existing Case collection"""
    try:
        # Check if Case collection exists
        schema = client.schema.get()
        class_names = [c['class'] for c in schema.get('classes', [])]

        if 'Case' in class_names:
            logger.info("Found existing 'Case' collection")

            # Get current record count
            result = client.query.aggregate('Case').with_meta_count().do()
            count = result['data']['Aggregate']['Case'][0]['meta']['count']
            logger.info(f"  Current records: {count}")

            # Confirm deletion (skip if --force flag)
            if not force:
                confirm = input(f"\n⚠️  Delete 'Case' collection ({count} records)? Type 'yes' to confirm: ")
                if confirm.lower() != 'yes':
                    logger.info("Deletion cancelled")
                    return False
            else:
                logger.warning(f"⚠️  FORCE MODE: Deleting 'Case' collection ({count} records)")

            # Delete collection
            logger.info("Deleting 'Case' collection...")
            client.schema.delete_class('Case')
            logger.info("✓ Collection deleted successfully")
            return True
        else:
            logger.info("No existing 'Case' collection found")
            return True

    except Exception as e:
        logger.error(f"Failed to delete schema: {e}")
        return False


def create_new_schema(client):
    """Create new schema with 49 properties"""
    logger.info("\nCreating new schema with 49 properties...")

    # Define schema for KMS 2.6 - Multi-Table Architecture
    schema = {
        'class': 'Case',
        'description': 'HPE Support Cases with single composite vector (KMS 2.6 - Multi-Table)',
        'vectorizer': 'none',  # We provide vectors manually
        'properties': [
            # ===================================================================
            # CASE TABLE (21 fields)
            # ===================================================================
            {'name': 'caseId', 'dataType': ['text'], 'description': 'Salesforce Case ID (primary key)'},
            {'name': 'caseNumber', 'dataType': ['text'], 'description': 'Case display number'},
            {'name': 'accountId', 'dataType': ['text'], 'description': 'Customer account ID'},
            {'name': 'subject', 'dataType': ['text'], 'description': 'Case subject/title'},
            {'name': 'description', 'dataType': ['text'], 'description': 'Issue description'},
            {'name': 'status', 'dataType': ['text'], 'description': 'Case status (New, In Progress, Closed)'},
            {'name': 'priority', 'dataType': ['text'], 'description': 'Priority level (High, Medium, Low)'},
            {'name': 'product', 'dataType': ['text'], 'description': 'Product name'},
            {'name': 'category', 'dataType': ['text'], 'description': 'Issue category'},
            {'name': 'productType', 'dataType': ['text'], 'description': 'Product type'},
            {'name': 'productLine', 'dataType': ['text'], 'description': 'Product line (e.g., 99)'},
            {'name': 'errorCodes', 'dataType': ['text'], 'description': 'Error codes'},
            {'name': 'resolutionCode', 'dataType': ['text'], 'description': 'Resolution code'},
            {'name': 'createdDate', 'dataType': ['date'], 'description': 'Case creation timestamp'},
            {'name': 'closedDate', 'dataType': ['date'], 'description': 'Case closure timestamp'},
            {'name': 'processedDate', 'dataType': ['date'], 'description': 'Pipeline processing timestamp'},
            {'name': 'issuePlainText', 'dataType': ['text'], 'description': 'Issue details (plain text)'},
            {'name': 'causePlainText', 'dataType': ['text'], 'description': 'Root cause (plain text)'},
            {'name': 'environment', 'dataType': ['text'], 'description': 'System environment'},
            {'name': 'resolution', 'dataType': ['text'], 'description': 'Resolution (HTML)'},
            {'name': 'resolutionPlainText', 'dataType': ['text'], 'description': 'Resolution (plain text)'},

            # ===================================================================
            # TASK TABLE (2 fields - aggregated)
            # ===================================================================
            {'name': 'taskCount', 'dataType': ['int'], 'description': 'Number of tasks'},
            {'name': 'taskDescription', 'dataType': ['text'], 'description': 'Troubleshooting steps (concatenated)'},

            # ===================================================================
            # WORK ORDER TABLE (3 fields - aggregated)
            # ===================================================================
            {'name': 'workOrderCount', 'dataType': ['int'], 'description': 'Number of work orders'},
            {'name': 'workOrderDescription', 'dataType': ['text'], 'description': 'Field engineer notes (concatenated)'},
            {'name': 'workOrderParts', 'dataType': ['text'], 'description': 'Parts replaced (concatenated)'},

            # ===================================================================
            # CASE COMMENTS TABLE (1 field - aggregated)
            # ===================================================================
            {'name': 'commentCount', 'dataType': ['int'], 'description': 'Number of comments'},
            {'name': 'caseComments', 'dataType': ['text'], 'description': 'Engineer comments (concatenated)'},

            # ===================================================================
            # WORK ORDER FEED TABLE (2 fields - aggregated)
            # ===================================================================
            {'name': 'workOrderFeedCount', 'dataType': ['int'], 'description': 'Number of feed entries'},
            {'name': 'workOrderFeed', 'dataType': ['text'], 'description': 'Service updates (concatenated)'},

            # ===================================================================
            # EMAIL MESSAGE TABLE (2 fields - aggregated)
            # ===================================================================
            {'name': 'emailCount', 'dataType': ['int'], 'description': 'Number of emails'},
            {'name': 'emailMessages', 'dataType': ['text'], 'description': 'Email thread (concatenated)'},

            # ===================================================================
            # ENRICHED METADATA (5 calculated fields)
            # ===================================================================
            {'name': 'productFamily', 'dataType': ['text'], 'description': 'Product family (ProLiant, Synergy, etc.)'},
            {'name': 'categoryHierarchy', 'dataType': ['text'], 'description': 'Normalized category hierarchy'},
            {'name': 'resolutionTime', 'dataType': ['text'], 'description': 'Resolution time bucket (0-4h, 4-24h, 1-7d, >7d)'},
            {'name': 'quarter', 'dataType': ['text'], 'description': 'Quarter and year (e.g., Q3 2024)'},
            {'name': 'ageInDays', 'dataType': ['int'], 'description': 'Case age in days'},

            # ===================================================================
            # PIPELINE METADATA (3 fields)
            # ===================================================================
            {'name': 'compositeText', 'dataType': ['text'], 'description': 'Concatenated text from all 6 tables'},
            {'name': 'pipelineVersion', 'dataType': ['text'], 'description': 'KMS pipeline version (2.6)'},
            {'name': 'embeddingModel', 'dataType': ['text'], 'description': 'Embedding model used'},
        ]
    }

    try:
        client.schema.create_class(schema)
        logger.info("✓ Schema created successfully")
        logger.info(f"  Total properties: {len(schema['properties'])}")
        logger.info(f"  - Case fields: 21")
        logger.info(f"  - Task fields: 2")
        logger.info(f"  - WorkOrder fields: 3")
        logger.info(f"  - CaseComments fields: 2")
        logger.info(f"  - WorkOrderFeed fields: 2")
        logger.info(f"  - EmailMessage fields: 2")
        logger.info(f"  - Enriched metadata: 5")
        logger.info(f"  - Pipeline metadata: 3")
        logger.info(f"  = Total: {21+2+3+2+2+2+5+3} properties")
        return True

    except Exception as e:
        logger.error(f"Failed to create schema: {e}")
        return False


def verify_schema(client):
    """Verify the new schema was created correctly"""
    try:
        schema = client.schema.get('Case')
        properties = schema.get('properties', [])

        logger.info("\n" + "="*70)
        logger.info("Schema Verification")
        logger.info("="*70)
        logger.info(f"Class: {schema['class']}")
        logger.info(f"Description: {schema['description']}")
        logger.info(f"Vectorizer: {schema['vectorizer']}")
        logger.info(f"Properties: {len(properties)}")

        # Group properties by category
        categories = {
            'Case Core': [p for p in properties if p['name'] in ['caseId', 'caseNumber', 'accountId', 'subject', 'description', 'status', 'priority', 'product', 'category', 'productType', 'productLine', 'errorCodes', 'resolutionCode', 'createdDate', 'closedDate', 'processedDate', 'issuePlainText', 'causePlainText', 'environment', 'resolution', 'resolutionPlainText']],
            'Task': [p for p in properties if 'task' in p['name'].lower()],
            'WorkOrder': [p for p in properties if 'workorder' in p['name'].lower()],
            'Comments': [p for p in properties if 'comment' in p['name'].lower()],
            'Email': [p for p in properties if 'email' in p['name'].lower()],
            'Enriched': [p for p in properties if p['name'] in ['productFamily', 'categoryHierarchy', 'resolutionTime', 'quarter', 'ageInDays']],
            'Pipeline': [p for p in properties if p['name'] in ['compositeText', 'pipelineVersion', 'embeddingModel']]
        }

        for category, props in categories.items():
            logger.info(f"\n{category}: {len(props)} fields")
            for prop in props:
                logger.info(f"  - {prop['name']}: {prop['dataType']}")

        logger.info("\n✓✓ Schema verification complete")
        return True

    except Exception as e:
        logger.error(f"Schema verification failed: {e}")
        return False


def main():
    """Main execution"""
    # Check for --force flag
    force = '--force' in sys.argv

    logger.info("="*70)
    logger.info("WEAVIATE SCHEMA RESET - MULTI-TABLE ARCHITECTURE")
    logger.info("="*70)
    logger.info("This will:")
    logger.info("  1. Delete existing 'Case' collection")
    logger.info("  2. Create new schema with 49 properties")
    logger.info("  3. Support 6-table architecture (Case + 5 child tables)")
    if force:
        logger.warning("  MODE: FORCE (no confirmation prompts)")
    logger.info("="*70)

    # Connect to Weaviate
    client = connect_to_weaviate()
    if not client:
        logger.error("Cannot proceed without Weaviate connection")
        sys.exit(1)

    # Delete existing schema
    if not delete_existing_schema(client, force=force):
        logger.error("Schema deletion failed")
        sys.exit(1)

    # Create new schema
    if not create_new_schema(client):
        logger.error("Schema creation failed")
        sys.exit(1)

    # Verify schema
    if not verify_schema(client):
        logger.error("Schema verification failed")
        sys.exit(1)

    logger.info("\n" + "="*70)
    logger.info("✓✓✓ SCHEMA RESET COMPLETE!")
    logger.info("="*70)
    logger.info("Next steps:")
    logger.info("  1. Prepare test data with all 6 tables")
    logger.info("  2. Run DAG: kms_2_6_daily_pipeline")
    logger.info("  3. Verify data loads correctly with new schema")
    logger.info("="*70)


if __name__ == '__main__':
    main()
