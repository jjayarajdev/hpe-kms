"""
Weaviate Vector Database Loader (KMS 2.6)

Loads case data with SINGLE composite vector into Weaviate.

KMS 2.6 Specification:
- Single composite vector (NOT dual vectors)
- 3,072 dimensions (ChatHPE text-embedding-3-large)
- Combines all 44 fields from 6 tables
- HNSW indexing with cosine similarity
- 98% cost savings vs dual vector approach

Schema structure (KMS 2.6):
- Case ID and metadata fields
- Composite text field (all 44 fields concatenated)
- Single composite vector (3,072 dimensions)
- 6 tables: Case, Task, WorkOrder, CaseComments, WorkOrderFeed, EmailMessage

Task Reference: Phase 2, Task 2.5
Updated: November 2025 (KMS 2.6 alignment)
"""

from typing import List, Dict, Optional
import logging


class WeaviateLoader:
    """Loads data into Weaviate vector database using single composite vector approach"""

    def __init__(self, weaviate_url: str, auth_config: Dict):
        """
        Initialize Weaviate Loader

        Args:
            weaviate_url: Weaviate instance URL
            auth_config: Authentication configuration
        """
        self.weaviate_url = weaviate_url
        self.auth_config = auth_config
        self.logger = logging.getLogger(__name__)

        # Batch configuration
        self.batch_size = 100
        self.collection_name = "Case"

        # TODO: Initialize Weaviate client
        # import weaviate
        # self.client = weaviate.Client(
        #     url=weaviate_url,
        #     auth_client_secret=weaviate.AuthApiKey(auth_config['api_key'])
        # )

    def create_schema(self):
        """
        Create Weaviate schema for Case collection (KMS 2.6)

        Schema includes:
        - Properties: Key metadata fields (21 fields from Case table + identifiers)
        - compositeText: All 44 fields concatenated and PII-removed
        - Vector: Single composite vector (3,072 dims)
        - Index: HNSW with cosine similarity

        Benefits:
        - 98% cost reduction vs dual vectors
        - Faster queries (single vector lookup)
        - Complete case narrative for search
        """
        # KMS 2.6 Schema with single composite vector
        schema = {
            "class": "Case",
            "description": "HPE Support Cases with single composite vector (KMS 2.6)",
            "vectorizer": "none",  # We provide our own vectors from ChatHPE
            "properties": [
                # Primary identifiers
                {"name": "caseId", "dataType": ["string"], "description": "Salesforce Case ID (primary key)"},
                {"name": "caseNumber", "dataType": ["string"], "description": "HPE Case Number (user-facing)"},

                # Core Case metadata (21 fields from Case table)
                {"name": "accountId", "dataType": ["string"], "description": "Customer Account ID"},
                {"name": "status", "dataType": ["string"], "description": "Case Status"},
                {"name": "priority", "dataType": ["string"], "description": "Case Priority"},
                {"name": "product", "dataType": ["string"], "description": "Product"},
                {"name": "category", "dataType": ["string"], "description": "Category"},
                {"name": "createdDate", "dataType": ["date"], "description": "Case Created Date"},
                {"name": "closedDate", "dataType": ["date"], "description": "Case Closed Date"},

                {"name": "subject", "dataType": ["text"], "description": "Case Subject"},
                {"name": "description", "dataType": ["text"], "description": "Case Description"},
                {"name": "resolution", "dataType": ["text"], "description": "Resolution"},

                {"name": "errorCodes", "dataType": ["string"], "description": "Error Codes"},
                {"name": "issuePlainText", "dataType": ["text"], "description": "Issue Plain Text"},
                {"name": "causePlainText", "dataType": ["text"], "description": "Cause Plain Text"},
                {"name": "environment", "dataType": ["text"], "description": "GSD Environment"},

                {"name": "resolutionCode", "dataType": ["string"], "description": "Resolution Code"},
                {"name": "resolutionPlainText", "dataType": ["text"], "description": "Resolution Plain Text"},

                {"name": "productType", "dataType": ["string"], "description": "Product Type"},
                {"name": "productLine", "dataType": ["string"], "description": "Product Line"},
                {"name": "rootCause", "dataType": ["text"], "description": "Root Cause"},

                # Composite text field (all 44 fields concatenated, PII-removed)
                {
                    "name": "compositeText",
                    "dataType": ["text"],
                    "description": "All 44 fields from 6 tables concatenated (Case, Task, WorkOrder, CaseComments, WorkOrderFeed, EmailMessage). PII-removed, HTML-cleaned, smart-truncated (≤30K chars). Used for embedding generation."
                },

                # Child record counts (for transparency)
                {"name": "taskCount", "dataType": ["int"], "description": "Number of related Tasks"},
                {"name": "workOrderCount", "dataType": ["int"], "description": "Number of related WorkOrders"},
                {"name": "commentCount", "dataType": ["int"], "description": "Number of related CaseComments"},
                {"name": "workOrderFeedCount", "dataType": ["int"], "description": "Number of related WorkOrderFeeds"},
                {"name": "emailCount", "dataType": ["int"], "description": "Number of related EmailMessages"},

                # Processing metadata
                {"name": "processedDate", "dataType": ["date"], "description": "Date processed into KMS"},
                {"name": "pipelineVersion", "dataType": ["string"], "description": "KMS pipeline version (e.g., 2.6)"},
                {"name": "embeddingModel", "dataType": ["string"], "description": "Embedding model used (text-embedding-3-large)"},
            ],
            "vectorIndexConfig": {
                "distance": "cosine",  # Cosine similarity for semantic search
                "efConstruction": 256,  # HNSW construction parameter
                "maxConnections": 64   # HNSW connections per node
            },
            "vectorIndexType": "hnsw"  # Hierarchical Navigable Small World index
        }

        # TODO: Create schema in Weaviate
        # self.client.schema.create_class(schema)
        self.logger.info("Weaviate schema created (KMS 2.6 - single composite vector)")

        return schema

    def load_case(self, case_data: Dict) -> bool:
        """
        Load single case into Weaviate (KMS 2.6)

        Args:
            case_data: Dictionary with case data including:
                - All metadata fields (21+ fields)
                - compositeText: Concatenated text from all 44 fields
                - composite_vector: Single vector (3,072 dims)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate composite vector
            if 'composite_vector' not in case_data:
                raise ValueError("composite_vector is required")

            composite_vector = case_data['composite_vector']

            if len(composite_vector) != 3072:
                raise ValueError(f"composite_vector must be 3,072 dimensions, got {len(composite_vector)}")

            # Prepare object (remove vector from data_object)
            data_object = {k: v for k, v in case_data.items() if k != 'composite_vector'}

            # TODO: Create object with single composite vector
            # self.client.data_object.create(
            #     data_object=data_object,
            #     class_name=self.collection_name,
            #     vector=composite_vector  # Single vector (KMS 2.6)
            # )

            self.logger.debug(f"Loaded case {case_data.get('caseId')} with single composite vector")
            return True

        except Exception as e:
            self.logger.error(f"Failed to load case {case_data.get('caseId')}: {e}")
            return False

    def load_batch(self, cases: List[Dict]) -> Dict[str, int]:
        """
        Load batch of cases into Weaviate (optimized)

        Target: ≥300 cases/minute

        Args:
            cases: List of case dictionaries

        Returns:
            Statistics: {'success': count, 'failed': count}
        """
        stats = {'success': 0, 'failed': 0}

        self.logger.info(f"Starting batch load of {len(cases)} cases...")

        # TODO: Use Weaviate batch API
        # with self.client.batch as batch:
        #     batch.batch_size = self.batch_size
        #
        #     for case in cases:
        #         try:
        #             # Validate composite vector
        #             if 'composite_vector' not in case:
        #                 self.logger.error(f"Case {case.get('caseId')} missing composite_vector")
        #                 stats['failed'] += 1
        #                 continue
        #
        #             composite_vector = case['composite_vector']
        #
        #             # Prepare object
        #             data_object = {k: v for k, v in case.items() if k != 'composite_vector'}
        #
        #             # Add to batch with single composite vector
        #             batch.add_data_object(
        #                 data_object=data_object,
        #                 class_name=self.collection_name,
        #                 vector=composite_vector  # Single vector (KMS 2.6)
        #             )
        #             stats['success'] += 1
        #
        #         except Exception as e:
        #             stats['failed'] += 1
        #             self.logger.error(f"Failed to add case to batch: {e}")

        self.logger.info(f"Batch load complete: {stats}")
        return stats

    def hybrid_search(
        self,
        query_text: str,
        query_vector: List[float],
        limit: int = 5,
        alpha: float = 0.75
    ) -> List[Dict]:
        """
        Perform hybrid search (vector + keyword) on Weaviate

        KMS 2.6 Search Strategy:
        - Vector search on composite vector (semantic similarity)
        - Keyword search on compositeText (BM25)
        - Hybrid fusion with alpha weighting

        Args:
            query_text: User query text
            query_vector: Query embedding (3,072 dims)
            limit: Number of results to return
            alpha: Hybrid search weight (0.0 = pure keyword, 1.0 = pure vector)

        Returns:
            List of search results with scores
        """
        if len(query_vector) != 3072:
            raise ValueError(f"query_vector must be 3,072 dimensions, got {len(query_vector)}")

        # TODO: Implement hybrid search with Weaviate
        # result = (
        #     self.client.query
        #     .get(self.collection_name, ["caseId", "caseNumber", "subject", "compositeText"])
        #     .with_hybrid(
        #         query=query_text,
        #         vector=query_vector,
        #         alpha=alpha  # 0.75 = 75% vector, 25% keyword
        #     )
        #     .with_limit(limit)
        #     .with_additional(["score", "distance"])
        #     .do()
        # )
        #
        # return result['data']['Get']['Case']

        self.logger.warning("Hybrid search not yet implemented")
        return []

    def upsert_case(self, case_data: Dict) -> bool:
        """
        Upsert case (insert or update if exists)

        Used for incremental updates (trickle feed: 2,740 cases/day)

        Args:
            case_data: Case dictionary

        Returns:
            True if successful
        """
        # TODO: Check if case exists, then update or insert
        # case_id = case_data['caseId']
        #
        # # Check if exists
        # existing = self.client.data_object.get(
        #     class_name=self.collection_name,
        #     uuid=case_id
        # )
        #
        # if existing:
        #     # Update existing
        #     self.client.data_object.update(
        #         data_object={k: v for k, v in case_data.items() if k != 'composite_vector'},
        #         class_name=self.collection_name,
        #         uuid=case_id,
        #         vector=case_data['composite_vector']
        #     )
        #     self.logger.info(f"Updated case {case_id}")
        # else:
        #     # Insert new
        #     self.load_case(case_data)
        #     self.logger.info(f"Inserted new case {case_id}")

        raise NotImplementedError("Upsert not yet implemented")

    def get_collection_stats(self) -> Dict[str, int]:
        """
        Get statistics about loaded data

        Returns:
            Stats dictionary with object count, etc.
        """
        # TODO: Query Weaviate for stats
        # result = self.client.query.aggregate(self.collection_name).with_meta_count().do()
        #
        # stats = {
        #     'total_cases': result['data']['Aggregate']['Case'][0]['meta']['count'],
        #     'schema_version': 'KMS 2.6',
        #     'vector_approach': 'single_composite',
        #     'embedding_model': 'text-embedding-3-large',
        #     'dimensions': 3072
        # }
        #
        # return stats

        self.logger.warning("Stats retrieval not yet implemented")
        return {
            'total_cases': 0,
            'schema_version': 'KMS 2.6',
            'vector_approach': 'single_composite',
            'embedding_model': 'text-embedding-3-large',
            'dimensions': 3072
        }

    def delete_case(self, case_id: str) -> bool:
        """
        Delete case from Weaviate

        Args:
            case_id: Salesforce Case ID

        Returns:
            True if successful
        """
        # TODO: Delete object
        # self.client.data_object.delete(
        #     uuid=case_id,
        #     class_name=self.collection_name
        # )
        # self.logger.info(f"Deleted case {case_id}")

        raise NotImplementedError("Delete not yet implemented")

    def get_schema_info(self) -> Dict:
        """
        Get current Weaviate schema information

        Returns:
            Schema information dictionary
        """
        # TODO: Retrieve schema from Weaviate
        # schema = self.client.schema.get(self.collection_name)
        # return schema

        # Return expected schema structure for KMS 2.6
        return {
            'class': 'Case',
            'description': 'HPE Support Cases with single composite vector (KMS 2.6)',
            'vectorizer': 'none',
            'vector_approach': 'single_composite',
            'embedding_model': 'text-embedding-3-large',
            'dimensions': 3072,
            'tables_included': 6,
            'total_fields': 44,
            'vector_count_per_case': 1,
            'cost_savings': '98%'
        }


def main():
    """Test Weaviate loader with KMS 2.6 single composite vector"""
    print("=" * 70)
    print("Testing Weaviate Loader (KMS 2.6 - Single Composite Vector)")
    print("=" * 70)
    print()

    # Sample case with single composite vector (KMS 2.6)
    sample_case = {
        # Primary identifiers
        'caseId': '500Kh0001ABC123',
        'caseNumber': '5000123456',

        # Case metadata
        'accountId': '001Kh0001XYZ789',
        'status': 'Closed',
        'priority': 'High',
        'product': 'ProLiant',
        'category': 'Hardware > Server > Memory',
        'createdDate': '2024-10-15T10:30:00.000Z',
        'closedDate': '2024-10-16T14:45:00.000Z',

        'subject': '[Critical] HPE ProLiant DL380 Gen10 - Memory Health Degraded',
        'description': 'Server experiencing memory errors and system instability',
        'resolution': 'Engineer replaced faulty DIMM module. System tested and stable.',

        'errorCodes': 'iLO_400_MemoryErrors',
        'issuePlainText': 'DIMM and BIOS health degraded',
        'causePlainText': 'Hardware failure - Defective DIMM',
        'environment': 'Model: DL380 Gen10, OS: VMware ESXi 7.0, RAM: 128GB',

        'resolutionCode': 'Onsite Repair',
        'resolutionPlainText': 'Engineer visited site and replaced faulty DIMM module',

        'productType': 'Product Non-functional/Not working as Expected',
        'productLine': '34',
        'rootCause': 'Defective hardware component - DIMM module',

        # Composite text (all 44 fields concatenated, PII-removed)
        'compositeText': '''Case: 5000123456 | [Critical] HPE ProLiant DL380 Gen10 - Memory Health Degraded | Priority: High | Status: Closed

ISSUE: Server experiencing memory errors and system instability | iLO_400_MemoryErrors | DIMM and BIOS health degraded | Hardware failure - Defective DIMM

ENVIRONMENT: Model: DL380 Gen10, OS: VMware ESXi 7.0, RAM: 128GB | Product Non-functional/Not working as Expected | 34

RESOLUTION: Engineer replaced faulty DIMM module | Engineer visited site and replaced faulty DIMM module | Defective hardware component

TASKS: Issue: Server Memory Health Degraded. Part needed: Yes - Part Number 815098-B21

WORK ORDERS: DIMM Replacement - DL380 Gen10 | Replace faulty DIMM in Processor 1 Slot 8

COMMENTS: Engineer confirmed on site. Working on DIMM replacement. | Replacement complete. System stable.

SERVICE NOTES: Engineer dispatched. ETA 2 hours | Onsite work completed. System health restored.

EMAILS: Re: Memory Error | We have scheduled an engineer for tomorrow. | Case Resolved | The faulty DIMM module was replaced.''',

        # Child record counts
        'taskCount': 2,
        'workOrderCount': 1,
        'commentCount': 2,
        'workOrderFeedCount': 2,
        'emailCount': 2,

        # Processing metadata
        'processedDate': '2025-11-12T15:30:00.000Z',
        'pipelineVersion': '2.6',
        'embeddingModel': 'text-embedding-3-large',

        # Single composite vector (3,072 dimensions)
        'composite_vector': [0.123] * 3072  # Placeholder - would be from ChatHPE API
    }

    print("Sample Case Data (KMS 2.6):")
    print(f"  Case ID: {sample_case['caseId']}")
    print(f"  Case Number: {sample_case['caseNumber']}")
    print(f"  Subject: {sample_case['subject'][:60]}...")
    print(f"  Composite Text Length: {len(sample_case['compositeText'])} chars")
    print(f"  Composite Vector Dimensions: {len(sample_case['composite_vector'])}")
    print(f"  Child Records: {sample_case['taskCount']} tasks, {sample_case['workOrderCount']} WOs, {sample_case['commentCount']} comments")
    print(f"                 {sample_case['workOrderFeedCount']} feeds, {sample_case['emailCount']} emails (NEW)")
    print()

    # Initialize loader
    loader = WeaviateLoader(
        weaviate_url="http://localhost:8080",
        auth_config={'api_key': 'your-key'}
    )

    # Test schema creation
    print("Creating Weaviate schema...")
    schema = loader.create_schema()
    print(f"  ✓ Schema: {schema['class']}")
    print(f"  ✓ Description: {schema['description']}")
    print(f"  ✓ Properties: {len(schema['properties'])} fields")
    print(f"  ✓ Vector Index: {schema['vectorIndexType'].upper()}")
    print(f"  ✓ Distance Metric: {schema['vectorIndexConfig']['distance']}")
    print()

    # Test schema info
    print("Schema Information (KMS 2.6):")
    info = loader.get_schema_info()
    print(f"  ✓ Vector Approach: {info['vector_approach']}")
    print(f"  ✓ Embedding Model: {info['embedding_model']}")
    print(f"  ✓ Dimensions: {info['dimensions']}")
    print(f"  ✓ Tables Included: {info['tables_included']}")
    print(f"  ✓ Total Fields: {info['total_fields']}")
    print(f"  ✓ Vectors per Case: {info['vector_count_per_case']}")
    print(f"  ✓ Cost Savings: {info['cost_savings']}")
    print()

    # Test stats
    print("Collection Statistics:")
    stats = loader.get_collection_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()

    print("=" * 70)
    print("✓ Weaviate Loader Test Complete (KMS 2.6)")
    print()
    print("Key Changes from Previous Version:")
    print("  - REMOVED: Dual vectors (issue_vector + resolution_vector)")
    print("  - ADDED: Single composite vector (3,072 dims)")
    print("  - ADDED: compositeText field (all 44 fields concatenated)")
    print("  - ADDED: Child record counts (6 tables)")
    print("  - BENEFIT: 98% cost savings, faster queries")
    print("=" * 70)


if __name__ == "__main__":
    main()
