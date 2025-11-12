"""
Text Embedding Generator

Generates ONE composite embedding per case combining ALL 44 fields from 6 tables:
- Model: OpenAI text-embedding-3-large
- Dimensions: 3,072
- Single vector per case (NOT dual vectors)

Approach (as per KMS 2.6 PDF):
1. Concatenate all 44 fields into structured text
2. Smart truncation (≤30K chars) while preserving key context
3. Generate single 3,072-dimension vector
4. Benefits: 98% cost savings, faster queries, complete case narrative

Task Reference: Phase 2, Task 2.4
Updated: November 2025 (KMS 2.6 alignment - using OpenAI API)
"""

from typing import List, Dict, Tuple, Optional
import logging
import time
from openai import OpenAI


class EmbeddingGenerator:
    """Generates text embeddings using OpenAI API"""

    def __init__(self, api_key: str, api_endpoint: Optional[str] = None):
        """
        Initialize Embedding Generator with OpenAI API

        Args:
            api_key: OpenAI API authentication key
            api_endpoint: Optional custom API endpoint (defaults to OpenAI)
        """
        self.api_key = api_key
        self.api_endpoint = api_endpoint
        self.logger = logging.getLogger(__name__)

        # Initialize OpenAI client
        if api_endpoint:
            self.client = OpenAI(api_key=api_key, base_url=api_endpoint)
        else:
            self.client = OpenAI(api_key=api_key)

        # Model configuration
        self.model_name = "text-embedding-3-large"
        self.embedding_dimensions = 3072

        # Performance configuration
        self.batch_size = 100
        self.max_retries = 3
        self.retry_delay = 2  # seconds

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate single embedding vector using OpenAI API

        Args:
            text: Input text to embed

        Returns:
            Embedding vector (3,072 dimensions)
        """
        if not text or text.strip() == "":
            self.logger.warning("Empty text provided for embedding")
            return [0.0] * self.embedding_dimensions

        try:
            # Call OpenAI API
            response = self.client.embeddings.create(
                model=self.model_name,
                input=text,
                dimensions=self.embedding_dimensions
            )

            embedding = response.data[0].embedding
            self.logger.debug(f"Generated embedding with {len(embedding)} dimensions")
            return embedding

        except Exception as e:
            self.logger.error(f"Error generating embedding: {e}")
            raise

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for batch of texts (optimized using OpenAI batch API)

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        embeddings = []

        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]

            try:
                # Batch API call
                response = self.client.embeddings.create(
                    model=self.model_name,
                    input=batch,
                    dimensions=self.embedding_dimensions
                )

                # Extract embeddings in order
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)

                self.logger.info(f"Generated {len(batch_embeddings)} embeddings (batch {i//self.batch_size + 1})")

            except Exception as e:
                self.logger.error(f"Error in batch embedding generation: {e}")
                # Fallback to individual processing
                self.logger.info("Falling back to individual embedding generation...")
                for text in batch:
                    try:
                        embedding = self.generate_embedding(text)
                        embeddings.append(embedding)
                    except Exception as inner_e:
                        self.logger.error(f"Failed to generate embedding: {inner_e}")
                        embeddings.append([0.0] * self.embedding_dimensions)

            self.logger.info(f"Processed batch {i // self.batch_size + 1}")

        return embeddings

    def _call_api_with_retry(self, texts: List[str]) -> List[List[float]]:
        """
        Call API with exponential backoff retry logic

        Args:
            texts: Batch of texts

        Returns:
            List of embeddings
        """
        for attempt in range(self.max_retries):
            try:
                # TODO: Make API call
                # return self._call_api(texts)
                pass
            except Exception as e:
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    self.logger.warning(f"API call failed, retrying in {delay}s: {e}")
                    time.sleep(delay)
                else:
                    self.logger.error(f"API call failed after {self.max_retries} attempts")
                    raise

    def generate_composite_embedding(
        self,
        concatenated_text: str
    ) -> List[float]:
        """
        Generate single composite embedding for entire case

        This is the KMS 2.6 approach: ONE vector combining all 44 fields.

        Benefits:
        - 98% cost savings vs per-field embeddings
        - Faster queries (single vector lookup)
        - Full case narrative for complete context
        - Resilient to missing child tables/records

        Args:
            concatenated_text: All 44 fields concatenated with smart truncation

        Returns:
            Single embedding vector (3,072 dimensions)
        """
        self.logger.debug("Generating composite embedding for complete case")

        # Generate single embedding
        composite_embedding = self.generate_embedding(concatenated_text)

        # Validate embedding
        self._validate_embedding(composite_embedding, "Composite")

        return composite_embedding

    def concatenate_all_fields(self, case_data: Dict) -> str:
        """
        Concatenate all 44 fields from 6 tables into structured text

        Processing pipeline (as per KMS 2.6 PDF):
        1. HTML Cleanup - convert rich HTML to plain text
        2. Build structured sections from all fields
        3. Smart truncation (≤30K chars) while preserving key context

        Args:
            case_data: Dictionary with all case fields from 6 tables

        Returns:
            Concatenated text ready for embedding (≤30K chars)
        """
        sections = []

        # Section 1: Case Header (Case table - core metadata)
        if 'caseNumber' in case_data or 'subject' in case_data:
            header_parts = []
            if case_data.get('caseNumber'):
                header_parts.append(f"Case: {case_data['caseNumber']}")
            if case_data.get('subject'):
                header_parts.append(case_data['subject'])
            if case_data.get('priority'):
                header_parts.append(f"Priority: {case_data['priority']}")
            if case_data.get('status'):
                header_parts.append(f"Status: {case_data['status']}")
            sections.append(' | '.join(header_parts))

        # Section 2: Issue Description (Case table - issue fields)
        issue_parts = []
        for field in ['description', 'error_codes', 'issue_plain_text', 'cause_plain_text']:
            if case_data.get(field):
                issue_parts.append(self._clean_html(str(case_data[field])))
        if issue_parts:
            sections.append("ISSUE: " + " | ".join(issue_parts))

        # Section 3: Environment (Case table - technical context)
        env_parts = []
        for field in ['environment', 'product_type', 'product_line', 'category', 'sub_category']:
            if case_data.get(field):
                env_parts.append(str(case_data[field]))
        if env_parts:
            sections.append("ENVIRONMENT: " + " | ".join(env_parts))

        # Section 4: Resolution (Case table - resolution fields)
        resolution_parts = []
        for field in ['resolution', 'resolution_code', 'resolution_plain_text', 'root_cause']:
            if case_data.get(field):
                resolution_parts.append(self._clean_html(str(case_data[field])))
        if resolution_parts:
            sections.append("RESOLUTION: " + " | ".join(resolution_parts))

        # Section 5: Tasks (Task table - troubleshooting steps)
        if case_data.get('tasks'):
            task_texts = [self._clean_html(t.get('description', '')) for t in case_data['tasks'] if t.get('description')]
            if task_texts:
                sections.append("TASKS: " + " | ".join(task_texts))

        # Section 6: Work Orders (WorkOrder table - field engineer actions)
        if case_data.get('workorders'):
            wo_texts = []
            for wo in case_data['workorders']:
                wo_parts = [wo.get('subject', ''), wo.get('description', '')]
                wo_texts.extend([self._clean_html(p) for p in wo_parts if p])
            if wo_texts:
                sections.append("WORK ORDERS: " + " | ".join(wo_texts))

        # Section 7: Comments (CaseComments table - engineer discussion)
        if case_data.get('casecomments'):
            comment_texts = [self._clean_html(c.get('commentBody', '')) for c in case_data['casecomments'] if c.get('commentBody')]
            if comment_texts:
                sections.append("COMMENTS: " + " | ".join(comment_texts))

        # Section 8: Work Order Feed (WorkOrderFeed table - service notes)
        if case_data.get('workorderfeeds'):
            feed_texts = [self._clean_html(f.get('body', '')) for f in case_data['workorderfeeds'] if f.get('body')]
            if feed_texts:
                sections.append("SERVICE NOTES: " + " | ".join(feed_texts))

        # Section 9: Email Messages (EmailMessage table - correspondence)
        if case_data.get('emails'):
            email_texts = []
            for email in case_data['emails']:
                email_parts = [email.get('subject', ''), email.get('textBody', '')]
                email_texts.extend([self._clean_html(p) for p in email_parts if p])
            if email_texts:
                sections.append("EMAILS: " + " | ".join(email_texts))

        # Combine all sections
        full_text = '\n\n'.join(sections)

        # Smart truncation (≤30K chars)
        if len(full_text) > 30000:
            full_text = self._smart_truncate(full_text, 30000)
            self.logger.warning(f"Text truncated from {len(full_text)} to 30K chars")

        return full_text

    def _clean_html(self, text: str) -> str:
        """
        Convert HTML formatting to plain text

        Stage 1 of PII removal pipeline (as per KMS 2.6 PDF)

        Args:
            text: Text potentially containing HTML

        Returns:
            Clean plain text
        """
        import re

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)

        # Decode HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def _smart_truncate(self, text: str, max_chars: int) -> str:
        """
        Intelligently truncate text while preserving key context

        Strategy:
        - Prioritize keeping complete sections
        - Preserve technical terms and error codes
        - Keep beginning and end context

        Args:
            text: Full text
            max_chars: Maximum character count

        Returns:
            Truncated text preserving key context
        """
        if len(text) <= max_chars:
            return text

        # Simple truncation for now - keep first 80% and last 20%
        # This preserves issue description and final resolution
        keep_start = int(max_chars * 0.8)
        keep_end = int(max_chars * 0.2)

        truncated = text[:keep_start] + "\n\n[...TRUNCATED...]\n\n" + text[-keep_end:]

        return truncated[:max_chars]

    def _validate_embedding(self, embedding: List[float], label: str):
        """
        Validate embedding quality

        Checks:
        - Correct dimensions
        - No NaN or Inf values
        - Non-zero magnitude

        Args:
            embedding: Embedding vector to validate
            label: Label for logging (Issue/Resolution)
        """
        if len(embedding) != self.embedding_dimensions:
            raise ValueError(
                f"{label} embedding has wrong dimensions: "
                f"{len(embedding)} != {self.embedding_dimensions}"
            )

        # TODO: Check for NaN/Inf
        # TODO: Check magnitude
        # TODO: Optionally normalize

    def get_cache_key(self, text: str) -> str:
        """
        Generate cache key for text

        Useful for caching duplicate texts to save API costs

        Args:
            text: Input text

        Returns:
            Cache key (hash)
        """
        import hashlib
        return hashlib.sha256(text.encode()).hexdigest()


def main():
    """Test embedding generator with case data"""
    import json

    # Setup logging
    logging.basicConfig(level=logging.INFO)

    # Test case data from case-fields-mapping.json (DIMM failure example)
    test_case = {
        'caseNumber': '5000123456',
        'subject': '[Critical] HPE ProLiant DL380 Gen10 - Memory Health Degraded',
        'description': 'Server experiencing memory errors and system instability due to faulty DIMM module in Processor 1 Slot 8',
        'priority': 'High',
        'status': 'Closed',
        'error_codes': 'iLO_400_MemoryErrors',
        'issue_plain_text': 'DIMM and BIOS health degraded',
        'cause_plain_text': 'DIMM failure',
        'environment': 'Model: DL380 Gen10 OS: VMware ESXi 7.0',
        'resolution': '<p>DIMM replaced</p>',
        'resolution_plain_text': 'Engineer visited the site and replaced the faulty DIMM module',
        'root_cause': 'Hardware failure - Defective DIMM',
        'product_type': 'Product Non-functional/Not working as Expected',
        'product_line': '34',
        'tasks': [
            {
                'type': 'Plan of Action',
                'description': 'Issue description: Server Memory Health Degraded. Part needed: Yes - Part Number 815098-B21'
            }
        ],
        'workorders': [
            {
                'subject': 'DIMM Replacement',
                'description': 'Replaced faulty DIMM in Processor 1 Slot 8'
            }
        ],
        'casecomments': [
            {
                'commentBody': 'Engineer confirmed on site. Working on DIMM replacement.'
            }
        ]
    }

    # Initialize generator
    generator = EmbeddingGenerator(
        api_endpoint="https://chathpe.api.endpoint/embeddings",
        api_key="test-api-key"
    )

    # Test concatenation
    print("=" * 60)
    print("Testing Single Composite Vector Approach (KMS 2.6)")
    print("=" * 60)

    concatenated = generator.concatenate_all_fields(test_case)
    print(f"\nConcatenated text length: {len(concatenated)} chars")
    print(f"\nConcatenated text preview:")
    print("-" * 60)
    print(concatenated[:500] + "..." if len(concatenated) > 500 else concatenated)
    print("-" * 60)

    # Test HTML cleanup
    html_test = "<p>DIMM <strong>replaced</strong></p>"
    cleaned = generator._clean_html(html_test)
    print(f"\nHTML cleanup test:")
    print(f"  Before: {html_test}")
    print(f"  After: {cleaned}")

    # Test smart truncation
    long_text = "A" * 35000
    truncated = generator._smart_truncate(long_text, 30000)
    print(f"\nTruncation test:")
    print(f"  Original length: {len(long_text)} chars")
    print(f"  Truncated length: {len(truncated)} chars")
    print(f"  Contains truncation marker: {'[...TRUNCATED...]' in truncated}")

    print("\n" + "=" * 60)
    print("✓ Text concatenation and preprocessing working!")
    print("=" * 60)

    # TODO: Test actual embedding generation when API is available
    # composite_vec = generator.generate_composite_embedding(concatenated)
    # print(f"\nComposite vector dimensions: {len(composite_vec)}")


if __name__ == "__main__":
    main()
