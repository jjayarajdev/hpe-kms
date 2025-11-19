#!/usr/bin/env python3
"""
Direct Weaviate Loader - Bypasses Airflow
Loads 10 test cases directly to Weaviate Cloud
"""

import os
import sys
import json
import math
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline.jobs.ingestion.json_ingester import JSONIngester
from src.pipeline.jobs.embedding.embedding_generator import EmbeddingGenerator
from src.pipeline.jobs.loading.weaviate_loader import WeaviateLoader
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def clean_vector(vector):
    """Clean vector by replacing NaN/Inf with 0.0"""
    return [0.0 if (math.isnan(v) or math.isinf(v)) else float(v) for v in vector]

def main():
    print("=" * 70)
    print("Direct Weaviate Loader - Loading 10 Cases")
    print("=" * 70)
    print()

    # Get credentials
    openai_api_key = os.getenv("OPENAI_API_KEY")
    weaviate_url = os.getenv("WEAVIATE_URL")
    weaviate_api_key = os.getenv("WEAVIATE_API_KEY")

    if not openai_api_key:
        print("❌ OPENAI_API_KEY not found in .env")
        return 1

    if not weaviate_url:
        print("❌ WEAVIATE_URL not found in .env")
        return 1

    print(f"✓ OpenAI API Key: {openai_api_key[:20]}...")
    print(f"✓ Weaviate URL: {weaviate_url}")
    print(f"✓ Weaviate API Key: {'Set' if weaviate_api_key else 'Not set'}")
    print()

    # Step 1: Load JSON data
    print("Step 1: Loading JSON data...")
    json_dir = "data/raw/sfdc_exports"
    ingester = JSONIngester(json_dir=json_dir)
    all_tables = ingester.load_all_tables()
    cases_df = all_tables['case']

    # Limit to 10 cases (or 5 if that's all we have)
    num_cases = min(10, len(cases_df))
    cases_df = cases_df.head(num_cases)
    print(f"✓ Loaded {num_cases} cases")
    print()

    # Step 2: Generate embeddings
    print("Step 2: Generating embeddings...")
    embedder = EmbeddingGenerator(api_key=openai_api_key)

    embedded_cases = []
    for idx, case in cases_df.iterrows():
        case_id = case['Id']
        print(f"  Processing case {idx + 1}/{num_cases}: {case_id}")

        # Build complete case
        case_data = {
            **case.to_dict(),
            'tasks': all_tables['task'][all_tables['task']['CaseId'] == case_id].to_dict('records'),
            'workorders': all_tables['workorder'][all_tables['workorder']['CaseId'] == case_id].to_dict('records'),
            'comments': all_tables['casecomment'][all_tables['casecomment']['ParentId'] == case_id].to_dict('records'),
            'emails': all_tables['emailmessage'][all_tables['emailmessage']['ParentId'] == case_id].to_dict('records')
        }

        # Get composite text
        composite_text = embedder.concatenate_all_fields(case_data)

        # Generate embedding
        try:
            composite_vector = embedder.generate_embeddings_batch([composite_text])[0]

            # Clean vector
            composite_vector = clean_vector(composite_vector)

            # Prepare case (dates must be None if empty, not empty string)
            case_to_load = {
                'caseId': case_id,
                'caseNumber': case_data.get('Case Number') or '',
                'accountId': case_data.get('AccountId') or '',
                'status': case_data.get('Status') or '',
                'priority': case_data.get('Priority') or '',
                'product': case_data.get('Product__c') or '',
                'category': case_data.get('Category__c') or '',
                'createdDate': case_data.get('CreatedDate') or None,  # Must be None, not ''
                'closedDate': case_data.get('ClosedDate') or None,    # Must be None, not ''
                'subject': case_data.get('Subject') or '',
                'description': case_data.get('Description') or '',
                'resolution': case_data.get('Resolution__c') or '',
                'errorCodes': case_data.get('Error_Codes__c') or '',
                'issuePlainText': case_data.get('Issue_Plain_Text__c') or '',
                'causePlainText': case_data.get('Cause_Plain_Text__c') or '',
                'environment': case_data.get('GSD_Environment_Plain_Text__c') or '',
                'resolutionCode': case_data.get('Resolution_Code__c') or '',
                'resolutionPlainText': case_data.get('Resolution_Plain_Text__c') or '',
                'productType': case_data.get('Product_Type__c') or '',
                'productLine': case_data.get('Product_Line__c') or '',
                'rootCause': case_data.get('Root_Cause__c') or '',
                'compositeText': composite_text,
                'taskCount': len(case_data['tasks']),
                'workOrderCount': len(case_data['workorders']),
                'commentCount': len(case_data['comments']),
                'workOrderFeedCount': 0,
                'emailCount': len(case_data['emails']),
                'processedDate': datetime.now(timezone.utc).isoformat(),
                'pipelineVersion': '2.6',
                'embeddingModel': 'text-embedding-3-large',
                'composite_vector': composite_vector
            }

            embedded_cases.append(case_to_load)
            print(f"    ✓ Embedded (vector length: {len(composite_vector)})")

        except Exception as e:
            print(f"    ✗ Failed: {e}")
            continue

    print(f"✓ Generated {len(embedded_cases)} embeddings")
    print()

    # Step 3: Load to Weaviate
    print("Step 3: Loading to Weaviate Cloud...")
    auth_config = {'api_key': weaviate_api_key} if weaviate_api_key else {'anonymous': True}
    loader = WeaviateLoader(weaviate_url=weaviate_url, auth_config=auth_config)

    # Create schema
    loader.create_schema()
    print("✓ Schema created/verified")

    # Load batch
    print(f"Loading {len(embedded_cases)} cases...")
    stats = loader.load_batch(embedded_cases)

    print()
    print("=" * 70)
    print("Results:")
    print(f"  ✓ Successfully loaded: {stats['success']} cases")
    print(f"  ✗ Failed: {stats['failed']} cases")
    print("=" * 70)
    print()

    print("Check your Weaviate Cloud dashboard - you should see the 'Case' collection!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
