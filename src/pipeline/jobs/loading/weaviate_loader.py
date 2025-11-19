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
import weaviate


class WeaviateLoader:
    """Loads data into Weaviate vector database using single composite vector approach"""

    def __init__(self, weaviate_url: str, auth_config: Dict):
        """
        Initialize Weaviate Loader

        Args:
            weaviate_url: Weaviate instance URL (e.g., "u1ju7icbrtesr1bwaa2q.c0.asia-southeast1.gcp.weaviate.cloud")
            auth_config: Authentication configuration
                - {'api_key': 'your-api-key'} for authenticated access
                - {'anonymous': True} for anonymous access
        """
        self.weaviate_url = weaviate_url
        self.auth_config = auth_config
        self.logger = logging.getLogger(__name__)

        # Batch configuration
        self.batch_size = 100
        self.collection_name = "Case"

        # Initialize Weaviate client
        self.client = self._create_client()

    def _create_client(self):
        """Create and return Weaviate client with proper authentication"""
        try:
            # Ensure URL has proper scheme
            if not self.weaviate_url.startswith('http'):
                url = f"https://{self.weaviate_url}"
            else:
                url = self.weaviate_url

            # Create client with authentication
            if self.auth_config.get('anonymous'):
                self.logger.info(f"Connecting to Weaviate (anonymous): {url}")
                client = weaviate.Client(url=url)
            else:
                api_key = self.auth_config.get('api_key')
                if not api_key:
                    raise ValueError("API key required for authenticated access")

                self.logger.info(f"Connecting to Weaviate (authenticated): {url}")
                auth = weaviate.AuthApiKey(api_key=api_key)
                client = weaviate.Client(
                    url=url,
                    auth_client_secret=auth
                )

            # Test connection
            if client.is_ready():
                self.logger.info("✓ Connected to Weaviate successfully")
            else:
                self.logger.warning("⚠️  Weaviate connection not ready")

            return client

        except Exception as e:
            self.logger.error(f"Failed to create Weaviate client: {e}")
            raise

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

        try:
            # Check if class already exists
            existing_schema = self.client.schema.get()
            class_exists = any(cls['class'] == 'Case' for cls in existing_schema.get('classes', []))

            if class_exists:
                self.logger.info("Schema 'Case' already exists, skipping creation")
            else:
                # Create schema in Weaviate
                self.client.schema.create_class(schema)
                self.logger.info("✓ Weaviate schema created (KMS 2.6 - single composite vector)")

        except Exception as e:
            self.logger.error(f"Failed to create schema: {e}")
            raise

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

            # Create object with single composite vector
            self.client.data_object.create(
                data_object=data_object,
                class_name=self.collection_name,
                vector=composite_vector  # Single vector (KMS 2.6)
            )

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
            cases: List of case dictionaries with composite_vector

        Returns:
            Statistics: {'success': count, 'failed': count}
        """
        stats = {'success': 0, 'failed': 0}

        if not cases:
            self.logger.warning("No cases to load")
            return stats

        self.logger.info(f"Starting batch load of {len(cases)} cases...")

        try:
            # Use Weaviate batch API for optimized loading
            with self.client.batch as batch:
                batch.batch_size = self.batch_size

                for case in cases:
                    try:
                        # Validate composite vector
                        if 'composite_vector' not in case:
                            self.logger.error(f"Case {case.get('caseId')} missing composite_vector")
                            stats['failed'] += 1
                            continue

                        composite_vector = case['composite_vector']

                        if len(composite_vector) != 3072:
                            self.logger.error(f"Case {case.get('caseId')} has invalid vector length: {len(composite_vector)}")
                            stats['failed'] += 1
                            continue

                        # Clean vector: replace NaN/Inf with 0.0
                        import math
                        composite_vector = [0.0 if (math.isnan(v) or math.isinf(v)) else float(v) for v in composite_vector]

                        # Prepare object (remove vector from data_object)
                        data_object = {k: v for k, v in case.items() if k != 'composite_vector'}

                        # Clean data: handle None, NaN, Inf values, type conversions
                        # Date fields MUST be None (not empty string) if not set
                        import math
                        date_fields = {'createdDate', 'closedDate', 'processedDate'}
                        string_fields = {'caseId', 'caseNumber', 'accountId', 'status', 'priority', 'product',
                                       'category', 'errorCodes', 'resolutionCode', 'productType', 'productLine',
                                       'pipelineVersion', 'embeddingModel'}
                        text_fields = {'subject', 'description', 'resolution', 'issuePlainText', 'causePlainText',
                                      'environment', 'resolutionPlainText', 'rootCause', 'compositeText'}
                        int_fields = {'taskCount', 'workOrderCount', 'commentCount', 'workOrderFeedCount', 'emailCount'}

                        for key, value in list(data_object.items()):
                            if value is None:
                                if key not in date_fields:
                                    data_object[key] = ''  # Convert None to '' for non-date fields
                                # else: leave as None for date fields
                            elif key in string_fields or key in text_fields:
                                # Ensure string/text fields are actually strings
                                data_object[key] = str(value) if value is not None else ''
                            elif key in int_fields:
                                # Ensure int fields are actually ints
                                data_object[key] = int(value) if value is not None else 0
                            elif isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                                data_object[key] = 0.0
                            elif isinstance(value, list):
                                # Clean lists that might contain floats
                                data_object[key] = [0.0 if isinstance(v, float) and (math.isnan(v) or math.isinf(v)) else v for v in value]

                        # Add to batch with single composite vector
                        batch.add_data_object(
                            data_object=data_object,
                            class_name=self.collection_name,
                            vector=composite_vector  # Single vector (KMS 2.6)
                        )
                        stats['success'] += 1

                        if stats['success'] % 50 == 0:
                            self.logger.info(f"  Progress: {stats['success']}/{len(cases)} cases added to batch")

                    except Exception as e:
                        stats['failed'] += 1
                        self.logger.error(f"Failed to add case {case.get('caseId')} to batch: {e}")

            self.logger.info(f"✓ Batch load complete: {stats['success']} success, {stats['failed']} failed")

        except Exception as e:
            self.logger.error(f"Batch loading failed: {e}")
            raise

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

        # Weaviate v3 Hybrid Search
        result = (
            self.client.query
            .get(self.collection_name, ["caseId", "caseNumber", "subject", "compositeText"])
            .with_hybrid(
                query=query_text,
                vector=query_vector,
                alpha=alpha  # 0.75 = 75% vector, 25% keyword
            )
            .with_limit(limit)
            .with_additional(["score", "explainScore"])
            .do()
        )

        return result.get('data', {}).get('Get', {}).get(self.collection_name, [])

    def upsert_case(self, case_data: Dict) -> bool:
        """
        Upsert case (insert or update if exists)

        Used for incremental updates (trickle feed: 2,740 cases/day)

        Args:
            case_data: Case dictionary with composite_vector

        Returns:
            True if successful
        """
        try:
            case_id = case_data.get('caseId')
            if not case_id:
                self.logger.error("Case data missing caseId")
                return False

            # Validate composite vector
            if 'composite_vector' not in case_data:
                self.logger.error(f"Case {case_id} missing composite_vector")
                return False

            composite_vector = case_data['composite_vector']
            if len(composite_vector) != 3072:
                self.logger.error(f"Case {case_id} has invalid vector length: {len(composite_vector)}")
                return False

            # Clean vector: replace NaN/Inf with 0.0
            import math
            composite_vector = [0.0 if (math.isnan(v) or math.isinf(v)) else float(v) for v in composite_vector]

            # Prepare object (remove vector from data_object)
            data_object = {k: v for k, v in case_data.items() if k != 'composite_vector'}

            # Clean metadata fields - replace NaN/Inf with None
            for key, value in data_object.items():
                if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                    data_object[key] = None
                elif isinstance(value, list):
                    data_object[key] = [None if isinstance(v, float) and (math.isnan(v) or math.isinf(v)) else v for v in value]

            # Check if case already exists by querying on caseId
            result = (
                self.client.query
                .get(self.collection_name, ["caseId"])
                .with_where({
                    "path": ["caseId"],
                    "operator": "Equal",
                    "valueString": case_id
                })
                .with_limit(1)
                .with_additional(["id"])
                .do()
            )

            existing_objects = result.get('data', {}).get('Get', {}).get(self.collection_name, [])

            if existing_objects and len(existing_objects) > 0:
                # Case exists - UPDATE
                uuid = existing_objects[0]['_additional']['id']

                self.client.data_object.replace(
                    data_object=data_object,
                    class_name=self.collection_name,
                    uuid=uuid,
                    vector=composite_vector
                )
                self.logger.info(f"✓ Updated existing case {case_id} (UUID: {uuid})")
                return True
            else:
                # Case doesn't exist - INSERT
                uuid = self.client.data_object.create(
                    data_object=data_object,
                    class_name=self.collection_name,
                    vector=composite_vector
                )
                self.logger.info(f"✓ Inserted new case {case_id} (UUID: {uuid})")
                return True

        except Exception as e:
            self.logger.error(f"Failed to upsert case {case_data.get('caseId')}: {e}")
            return False

    def upsert_batch(self, cases: List[Dict]) -> Dict[str, int]:
        """
        Upsert batch of cases (insert new, update existing)

        More efficient than individual upserts for bulk operations.

        Args:
            cases: List of case dictionaries with composite_vector

        Returns:
            Statistics: {'inserted': count, 'updated': count, 'failed': count}
        """
        stats = {'inserted': 0, 'updated': 0, 'failed': 0}

        if not cases:
            self.logger.warning("No cases to upsert")
            return stats

        self.logger.info(f"Starting batch upsert of {len(cases)} cases...")

        # Build case_id -> case_data mapping
        case_map = {case.get('caseId'): case for case in cases if case.get('caseId')}

        if not case_map:
            self.logger.error("No valid caseIds found in batch")
            return stats

        # Query for all existing cases in one go
        case_ids = list(case_map.keys())
        self.logger.info(f"Checking for {len(case_ids)} existing cases...")

        try:
            # Query in batches of 100 to avoid query size limits
            existing_map = {}  # caseId -> UUID mapping
            batch_size = 100

            for i in range(0, len(case_ids), batch_size):
                batch_ids = case_ids[i:i+batch_size]

                # Build OR filter for batch
                where_filter = {
                    "operator": "Or",
                    "operands": [
                        {
                            "path": ["caseId"],
                            "operator": "Equal",
                            "valueString": cid
                        }
                        for cid in batch_ids
                    ]
                }

                result = (
                    self.client.query
                    .get(self.collection_name, ["caseId"])
                    .with_where(where_filter)
                    .with_limit(len(batch_ids))
                    .with_additional(["id"])
                    .do()
                )

                existing_objects = result.get('data', {}).get('Get', {}).get(self.collection_name, [])
                for obj in existing_objects:
                    existing_map[obj['caseId']] = obj['_additional']['id']

            self.logger.info(f"Found {len(existing_map)} existing cases, {len(case_ids) - len(existing_map)} new")

            # Now insert new and update existing using batch API
            with self.client.batch as batch:
                batch.batch_size = self.batch_size

                for case_id, case_data in case_map.items():
                    try:
                        # Validate composite vector
                        if 'composite_vector' not in case_data:
                            self.logger.error(f"Case {case_id} missing composite_vector")
                            stats['failed'] += 1
                            continue

                        composite_vector = case_data['composite_vector']
                        if len(composite_vector) != 3072:
                            self.logger.error(f"Case {case_id} invalid vector length: {len(composite_vector)}")
                            stats['failed'] += 1
                            continue

                        # Clean vector
                        import math
                        composite_vector = [0.0 if (math.isnan(v) or math.isinf(v)) else float(v) for v in composite_vector]

                        # Prepare object
                        data_object = {k: v for k, v in case_data.items() if k != 'composite_vector'}

                        # Clean metadata fields - replace NaN/Inf with None
                        for key, value in data_object.items():
                            if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                                data_object[key] = None
                            elif isinstance(value, list):
                                data_object[key] = [None if isinstance(v, float) and (math.isnan(v) or math.isinf(v)) else v for v in value]

                        if case_id in existing_map:
                            # UPDATE existing case
                            uuid = existing_map[case_id]
                            self.client.data_object.replace(
                                data_object=data_object,
                                class_name=self.collection_name,
                                uuid=uuid,
                                vector=composite_vector
                            )
                            stats['updated'] += 1
                        else:
                            # INSERT new case using batch
                            batch.add_data_object(
                                data_object=data_object,
                                class_name=self.collection_name,
                                vector=composite_vector
                            )
                            stats['inserted'] += 1

                        if (stats['inserted'] + stats['updated']) % 50 == 0:
                            self.logger.info(f"  Progress: {stats['inserted']} inserted, {stats['updated']} updated, {stats['failed']} failed")

                    except Exception as e:
                        stats['failed'] += 1
                        self.logger.error(f"Failed to upsert case {case_id}: {e}")

            self.logger.info(f"✓ Batch upsert complete: {stats['inserted']} inserted, {stats['updated']} updated, {stats['failed']} failed")

        except Exception as e:
            self.logger.error(f"Batch upsert failed: {e}")
            raise

        return stats

    def get_collection_stats(self) -> Dict[str, int]:
        """
        Get statistics about loaded data

        Returns:
            Stats dictionary with object count, etc.
        """
        try:
            # Query Weaviate for aggregate count
            result = self.client.query.aggregate(self.collection_name).with_meta_count().do()

            total_cases = result['data']['Aggregate'][self.collection_name][0]['meta']['count']

            stats = {
                'total_cases': total_cases,
                'schema_version': 'KMS 2.6',
                'vector_approach': 'single_composite',
                'embedding_model': 'text-embedding-3-large',
                'dimensions': 3072
            }

            self.logger.info(f"Collection stats: {total_cases} cases")
            return stats

        except Exception as e:
            self.logger.error(f"Failed to retrieve stats: {e}")
            return {
                'total_cases': 0,
                'schema_version': 'KMS 2.6',
                'vector_approach': 'single_composite',
                'embedding_model': 'text-embedding-3-large',
                'dimensions': 3072,
                'error': str(e)
            }

    def delete_case(self, case_id: str) -> bool:
        """
        Delete case from Weaviate

        Args:
            case_id: Salesforce Case ID

        Returns:
            True if successful
        """
        try:
            # Find the case by caseId to get its UUID
            result = (
                self.client.query
                .get(self.collection_name, ["caseId"])
                .with_where({
                    "path": ["caseId"],
                    "operator": "Equal",
                    "valueString": case_id
                })
                .with_limit(1)
                .with_additional(["id"])
                .do()
            )

            existing_objects = result.get('data', {}).get('Get', {}).get(self.collection_name, [])

            if not existing_objects:
                self.logger.warning(f"Case {case_id} not found - cannot delete")
                return False

            # Delete using UUID
            uuid = existing_objects[0]['_additional']['id']
            self.client.data_object.delete(
                uuid=uuid,
                class_name=self.collection_name
            )

            self.logger.info(f"✓ Deleted case {case_id} (UUID: {uuid})")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete case {case_id}: {e}")
            return False

    def get_schema_info(self) -> Dict:
        """
        Get current Weaviate schema information

        Returns:
            Schema information dictionary
        """
        try:
            # Retrieve schema from Weaviate
            schema = self.client.schema.get(self.collection_name)

            # Extract key information
            properties_count = len(schema.get('properties', []))
            vectorizer = schema.get('vectorizer', 'none')
            description = schema.get('description', '')

            schema_info = {
                'class': self.collection_name,
                'description': description,
                'vectorizer': vectorizer,
                'properties_count': properties_count,
                'vector_approach': 'single_composite',
                'embedding_model': 'text-embedding-3-large',
                'dimensions': 3072,
                'tables_included': 6,
                'total_fields': 44,
                'vector_count_per_case': 1,
                'cost_savings': '98%',
                'full_schema': schema
            }

            self.logger.info(f"Schema info retrieved: {properties_count} properties")
            return schema_info

        except Exception as e:
            self.logger.error(f"Failed to retrieve schema: {e}")
            # Return expected schema structure for KMS 2.6 as fallback
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
                'cost_savings': '98%',
                'error': str(e)
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
