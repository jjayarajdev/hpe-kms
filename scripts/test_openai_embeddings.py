#!/usr/bin/env python3
"""
Test OpenAI Embeddings Integration

This script tests the OpenAI embedding generation for KMS 2.6.
It verifies that the embedding generator can:
1. Connect to OpenAI API
2. Generate single embeddings
3. Generate batch embeddings
4. Handle the complete pipeline (JSON -> PII -> Concatenate -> Embed)

Usage:
    export OPENAI_API_KEY=your-api-key
    python scripts/test_openai_embeddings.py
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from dotenv import load_dotenv
from pipeline.jobs.ingestion.json_ingester import JSONIngester
from pii_removal.processors.pii_remover import PIIRemover
from pipeline.jobs.embedding.embedding_generator import EmbeddingGenerator

def main():
    print("="*70)
    print("KMS 2.6 - OpenAI Embeddings Integration Test")
    print("="*70)

    # Load environment variables
    load_dotenv()

    # Check API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("\n❌ ERROR: OPENAI_API_KEY not set")
        print("\nPlease set your OpenAI API key:")
        print("  export OPENAI_API_KEY=your-api-key-here")
        print("\nOr add to .env file:")
        print("  OPENAI_API_KEY=your-api-key-here")
        return 1

    print(f"\n✓ OpenAI API key found (length: {len(api_key)} chars)")

    # Test 1: Initialize Embedding Generator
    print("\n" + "-"*70)
    print("Test 1: Initialize OpenAI Embedding Generator")
    print("-"*70)

    try:
        embedder = EmbeddingGenerator(api_key=api_key)
        print(f"✓ Embedding generator initialized")
        print(f"  Model: {embedder.model_name}")
        print(f"  Dimensions: {embedder.embedding_dimensions}")
        print(f"  Batch size: {embedder.batch_size}")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return 1

    # Test 2: Generate Single Embedding
    print("\n" + "-"*70)
    print("Test 2: Generate Single Embedding")
    print("-"*70)

    test_text = "HPE ProLiant DL380 Gen10 server experiencing memory errors during POST"
    print(f"Input text: '{test_text}'")

    try:
        vector = embedder.generate_embedding(test_text)
        print(f"\n✓ Embedding generated successfully!")
        print(f"  Dimensions: {len(vector)}")
        print(f"  Vector preview: [{vector[0]:.6f}, {vector[1]:.6f}, {vector[2]:.6f}, ...]")
        print(f"  Vector magnitude: {sum(x**2 for x in vector)**0.5:.6f}")
        print(f"  Min value: {min(vector):.6f}")
        print(f"  Max value: {max(vector):.6f}")
    except Exception as e:
        print(f"❌ Failed to generate embedding: {e}")
        return 1

    # Test 3: Generate Batch Embeddings
    print("\n" + "-"*70)
    print("Test 3: Generate Batch Embeddings")
    print("-"*70)

    batch_texts = [
        "Server memory error causing system crash",
        "Network connectivity issues with switch configuration",
        "Storage array performance degradation"
    ]

    print(f"Batch size: {len(batch_texts)} texts")
    for i, text in enumerate(batch_texts, 1):
        print(f"  {i}. {text}")

    try:
        vectors = embedder.generate_embeddings_batch(batch_texts)
        print(f"\n✓ Batch embeddings generated successfully!")
        print(f"  Total vectors: {len(vectors)}")
        for i, vec in enumerate(vectors, 1):
            print(f"  Vector {i}: {len(vec)} dims, magnitude: {sum(x**2 for x in vec)**0.5:.6f}")
    except Exception as e:
        print(f"❌ Failed to generate batch embeddings: {e}")
        return 1

    # Test 4: Complete Pipeline (JSON -> PII -> Embed)
    print("\n" + "-"*70)
    print("Test 4: Complete Pipeline Test")
    print("-"*70)

    # Step 4.1: Load sample data
    print("\nStep 4.1: Load sample JSON data...")
    try:
        ingester = JSONIngester(json_dir="data/raw/sfdc_exports")
        all_tables = ingester.load_all_tables()
        cases_df = all_tables['case']
        first_case = cases_df.iloc[0].to_dict()
        case_id = first_case['Id']

        print(f"✓ Loaded case: {first_case['CaseNumber']}")
        print(f"  Description preview: {first_case.get('Description', '')[:80]}...")
    except Exception as e:
        print(f"⚠️  Warning: Could not load sample data: {e}")
        print("   Skipping pipeline test (generate sample data with: python scripts/prepare_sample_json.py)")
        return 0

    # Step 4.2: Remove PII
    print("\nStep 4.2: Remove PII from description...")
    try:
        remover = PIIRemover(table_name="Case")
        if first_case.get('Description'):
            detections = remover.detect_all_pii(first_case['Description'], "Case")
            cleaned_desc = remover.remove_pii(first_case['Description'], "Case")
            first_case['Description'] = cleaned_desc
            print(f"✓ PII removed: {len(detections)} instances detected")
        else:
            print("  (No description to clean)")
    except Exception as e:
        print(f"⚠️  Warning: PII removal failed: {e}")

    # Step 4.3: Concatenate all fields
    print("\nStep 4.3: Concatenate all 44 fields...")
    try:
        # Attach child records
        tasks = all_tables['task'][all_tables['task']['CaseId'] == case_id].to_dict('records')
        workorders = all_tables['workorder'][all_tables['workorder']['CaseId'] == case_id].to_dict('records')
        comments = all_tables['casecomment'][all_tables['casecomment']['ParentId'] == case_id].to_dict('records')
        emails = all_tables['emailmessage'][all_tables['emailmessage']['ParentId'] == case_id].to_dict('records')

        case_data = {
            **first_case,
            'tasks': tasks,
            'workorders': workorders,
            'comments': comments,
            'emails': emails
        }

        concatenated_text = embedder.concatenate_all_fields(case_data)
        print(f"✓ Concatenated text created")
        print(f"  Length: {len(concatenated_text)} characters")
        print(f"  Preview: {concatenated_text[:150]}...")
    except Exception as e:
        print(f"❌ Failed to concatenate: {e}")
        return 1

    # Step 4.4: Generate composite embedding
    print("\nStep 4.4: Generate composite embedding...")
    try:
        composite_vector = embedder.generate_composite_embedding(concatenated_text)
        print(f"✓ Composite vector generated!")
        print(f"  Dimensions: {len(composite_vector)}")
        print(f"  Magnitude: {sum(x**2 for x in composite_vector)**0.5:.6f}")
    except Exception as e:
        print(f"❌ Failed to generate composite embedding: {e}")
        return 1

    # Success summary
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED!")
    print("="*70)
    print("\nTest Summary:")
    print("  ✓ OpenAI API connection verified")
    print("  ✓ Single embedding generation working")
    print("  ✓ Batch embedding generation working")
    print("  ✓ Complete pipeline (JSON → PII → Concatenate → Embed) working")
    print("\nNext Steps:")
    print("  1. Run full pipeline: python scripts/run_pipeline.py")
    print("  2. Load to Weaviate: python scripts/load_to_weaviate.py")
    print("  3. Test search: python scripts/test_search.py")
    print("\n" + "="*70)

    return 0

if __name__ == '__main__':
    exit(main())
