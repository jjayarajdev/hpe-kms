# Section 1: Text Field Embedding Strategy

## 1.1 Multiple Text Fields Handling Across 6 SFDC Tables

**Challenge**: How to effectively embed and store multiple text fields from **6 different SFDC tables** (Case, Task, WorkOrder, CaseComments, WorkOrderFeed, EmailMessage) with **44 total fields** for optimal semantic search.

**Approach: Multi-Table Concatenated Text with Structured Weighting**

---

## 1.1.1 Data Source Tables and Field Mapping

### Table 1: Case (Primary - 21 fields)

**Issue Fields (13 fields)**:
| Field | UDP Column | Purpose | Example |
|-------|-----------|---------|---------|
| Subject | subject | Case title | "[AW] Server boot failure - DIMM errors" |
| Description | description | Detailed issue | "ProLiant DL380 showing POST error 1796" |
| Cause_Plain_Text__c | cause_plain_text | Root cause analysis | "DIMM failure", "HDD failure" |
| Issue_Plain_Text__c | issue_plain_text | Technical issue details | "Adapter 2 - HPE SN1200E 16Gb 2p FC HBA Status Degraded" |
| GSD_Environment_Plain_Text__c | gsd_environment_plain_text | Environment details | "Model: DL360 Gen9 OS: Windows" |
| Error_Codes__c | error_codes | Technical error codes | "218004", "iLO_400_MemoryErrors", "FTO-4D" |
| Issue_Type__c | issue_type | Categorization | "Product Non-functional", "Help me/How to" |
| Close_Comments__c | close_comments | Closing remarks | "Order created", "Record Merged Successfully" |
| CaseNumber | casenumber | Pan HPE case number | "5xxxxxxxxx" |
| Id | id | SFDC identifier | SFDC GUID |
| ParentId | parentid | Parent case link | SFDC GUID (if child case) |
| Product_Number__c | product_number | Product SKU | "BB958A", "867055-B21" |
| Product_Line__c | product_line | Product line code | "34", "3S", "TI" |

**Resolution Fields (8 fields)**:
| Field | UDP Column | Purpose | Example |
|-------|-----------|---------|---------|
| Case_Resolution_Summary__c | case_resolution_summary | Summary of fix | Clean text summary |
| Resolution__c | resolution | Detailed resolution | "<p>DIMM replaced</p>" (HTML) |
| Resolution_Plain_Text__c | resolution_plain_text | Clean resolution text | "Engineer visited site and replaced DIMM" |
| Resolution_Code__c | resolution_code | Resolution category | "Onsite Repair", "Part Shipped", "Electronic Case AutoClose" |
| Root_Cause__c | root_cause | Root cause category | "CARE - Booking error", "OM Fallout - RB6" |
| Product_Series__c | product_series | Product series ID | "1008995294", "5335825" |
| Product_Hierarchy__c | product_hierarchy | Product hierarchy ID | SFDC Product Hierarchy GUID |

### Table 2: Task (2 fields - filtered by Type)

**Filter Criteria**: `Type IN ('Plan of Action', 'Trouble Shooting')`

| Field | UDP Column | Purpose | Example |
|-------|-----------|---------|---------|
| Description | description | Troubleshooting steps | "Informed customer we will check with extended diagnostics team" |
| Subject | subject | Task type/title | "Plan of Action", "Troubleshooting", "Next follow up" |

### Table 3: WorkOrder (3 fields)

| Field | UDP Column | Purpose | Example |
|-------|-----------|---------|---------|
| Closing_Summary__c | closing_summary | Field engineer summary | "Happycall/HW;YES;CSC;YES;YES;disk replacement" |
| Onsite_Action__c | onsite_action | Actions performed onsite | "Check case log, contact customer, collect log" |
| Problem_Description__c | problem_description | Problem details | "Fault - Faulty RAM in Processor 2 Slot 12" |

### Table 4: CaseComments (1 field)

| Field | UDP Column | Purpose | Example |
|-------|-----------|---------|---------|
| CommentBody | commentbody | Engineer comments | "The quote NQ09405645 is now Orderable and ready to work" |

### Table 5: WorkOrderFeed (FeedItem) (2 fields)

| Field | UDP Column | Purpose | Example |
|-------|-----------|---------|---------|
| Title | - | Feed item title | Mostly null, "urldefense.com", "support.hpe.com" |
| Body | - | Feed update body | "Partner Notes20251009, CE: Zaid..." |

### Table 6: EmailMessage (2 fields)

| Field | UDP Column | Purpose | Example |
|-------|-----------|---------|---------|
| Subject | In progress | Email subject | "RE: HPE Support Case 5392877906 [ ref:!00Dd00bUlK... ]" |
| TextBody | In progress | Email body text | "Dear Customer, Thank you for choosing HPE..." |

---

## 1.1.2 Enhanced Text Concatenation Strategy

We create a **composite semantic representation** by joining fields from all 6 tables with structured delimiters:

```python
# Multi-Table Concatenation Template
def build_composite_text(case_data, tasks, workorders, comments, emails):
    """
    Build composite text from all 6 SFDC tables
    Total: 44 fields combined
    """

    composite_parts = []

    # SECTION 1: CASE IDENTIFICATION
    composite_parts.append(f"CASE NUMBER: {case_data.get('casenumber', 'N/A')}")
    composite_parts.append(f"CASE ID: {case_data.get('id', 'N/A')}")

    # SECTION 2: ISSUE DETAILS (13 fields from Case table)
    composite_parts.append(f"\n=== ISSUE ===")
    composite_parts.append(f"SUBJECT: {case_data.get('subject', '')}")
    composite_parts.append(f"DESCRIPTION: {case_data.get('description', '')}")

    if case_data.get('cause_plain_text'):
        composite_parts.append(f"CAUSE: {case_data['cause_plain_text']}")

    if case_data.get('issue_plain_text'):
        composite_parts.append(f"ISSUE DETAILS: {case_data['issue_plain_text']}")

    if case_data.get('error_codes'):
        composite_parts.append(f"ERROR CODES: {case_data['error_codes']}")

    if case_data.get('gsd_environment_plain_text'):
        composite_parts.append(f"ENVIRONMENT: {case_data['gsd_environment_plain_text']}")

    if case_data.get('issue_type'):
        composite_parts.append(f"ISSUE TYPE: {case_data['issue_type']}")

    # SECTION 3: TROUBLESHOOTING (Tasks table - Plan of Action)
    if tasks:
        composite_parts.append(f"\n=== TROUBLESHOOTING STEPS ===")
        for idx, task in enumerate(tasks, 1):
            if task.get('subject'):
                composite_parts.append(f"\nTASK {idx} - {task['subject']}:")
            if task.get('description'):
                composite_parts.append(f"{task['description']}")

    # SECTION 4: FIELD ENGINEER ACTIONS (WorkOrder table)
    if workorders:
        composite_parts.append(f"\n=== WORK ORDERS ===")
        for idx, wo in enumerate(workorders, 1):
            composite_parts.append(f"\nWORK ORDER {idx}:")
            if wo.get('problem_description'):
                composite_parts.append(f"Problem: {wo['problem_description']}")
            if wo.get('onsite_action'):
                composite_parts.append(f"Onsite Action: {wo['onsite_action']}")
            if wo.get('closing_summary'):
                composite_parts.append(f"Closing Summary: {wo['closing_summary']}")

    # SECTION 5: ENGINEER COMMENTS (CaseComments table)
    if comments:
        composite_parts.append(f"\n=== ENGINEER COMMENTS ===")
        for idx, comment in enumerate(comments, 1):
            if comment.get('commentbody'):
                composite_parts.append(f"Comment {idx}: {comment['commentbody']}")

    # SECTION 6: EMAIL COMMUNICATIONS (EmailMessage table)
    if emails:
        composite_parts.append(f"\n=== EMAIL COMMUNICATIONS ===")
        for idx, email in enumerate(emails[:3], 1):  # Limit to 3 most relevant emails
            if email.get('subject'):
                composite_parts.append(f"\nEmail {idx} Subject: {email['subject']}")
            if email.get('textbody'):
                # Truncate long emails
                email_body = email['textbody'][:500] + "..." if len(email['textbody']) > 500 else email['textbody']
                composite_parts.append(f"Email Body: {email_body}")

    # SECTION 7: RESOLUTION (8 fields from Case table)
    composite_parts.append(f"\n=== RESOLUTION ===")

    if case_data.get('case_resolution_summary'):
        composite_parts.append(f"RESOLUTION SUMMARY: {case_data['case_resolution_summary']}")

    if case_data.get('resolution_plain_text'):
        composite_parts.append(f"RESOLUTION: {case_data['resolution_plain_text']}")

    if case_data.get('resolution_code'):
        composite_parts.append(f"RESOLUTION CODE: {case_data['resolution_code']}")

    if case_data.get('root_cause'):
        composite_parts.append(f"ROOT CAUSE: {case_data['root_cause']}")

    if case_data.get('close_comments'):
        composite_parts.append(f"CLOSE COMMENTS: {case_data['close_comments']}")

    # SECTION 8: METADATA (12 fields)
    composite_parts.append(f"\n=== METADATA ===")
    composite_parts.append(f"PRODUCT NUMBER: {case_data.get('product_number', '')}")
    composite_parts.append(f"PRODUCT LINE: {case_data.get('product_line', '')}")
    composite_parts.append(f"ISSUE TYPE: {case_data.get('issue_type', '')}")

    # Join all parts
    composite_text = "\n".join([part for part in composite_parts if part])

    # Truncate if exceeds ChatHPE token limit (8,192 tokens ≈ 32,000 chars)
    # Keep most important sections: Issue + Resolution
    if len(composite_text) > 30000:
        composite_text = composite_text[:30000] + "\n\n[... TRUNCATED DUE TO LENGTH ...]"

    return composite_text
```

**Rationale**:
- **Complete context**: Single embedding captures holistic case semantics across all data sources
- **Maintains flow**: Issue → Troubleshooting → Actions → Resolution narrative
- **Token efficient**: ChatHPE text-embedding-3-large supports 8,192 tokens (~32,000 chars)
- **Cost efficient**: 1 vector vs 44 vectors per case (98% cost savings)
- **Simpler queries**: One vector search instead of multiple table joins at query time
- **Handles missing data**: Works even if Task/WorkOrder/Comments tables are empty

### 1.1.3 Pre-processing Pipeline

**Step 1: HTML Tag Removal** (Many resolution fields contain HTML)
```python
def remove_html_tags(text):
    """
    Remove HTML tags from resolution fields
    Example: "<p>DIMM replaced</p>" → "DIMM replaced"
    """
    import re
    from html import unescape

    if not text:
        return ""

    # Unescape HTML entities (&nbsp;, &lt;, etc.)
    text = unescape(text)

    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text
```

**Step 2: PII Removal (Multi-Stage)**
```python
def remove_pii(text, field_name=""):
    """
    Multi-stage PII removal for all 6 table sources
    Critical for: CaseComments, EmailMessage, WorkOrder descriptions
    """
    import re
    import spacy

    if not text:
        return text

    nlp = spacy.load("en_core_web_lg")

    # Stage 1: Email patterns (critical for EmailMessage table)
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                  '[EMAIL_REDACTED]', text)

    # Stage 2: Phone patterns (international)
    text = re.sub(r'(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
                  '[PHONE_REDACTED]', text)

    # Stage 3: IP addresses (but preserve error codes like "218004")
    # Only match valid IP ranges (0-255)
    text = re.sub(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
                  '[IP_REDACTED]', text)

    # Stage 4: Serial numbers that might be personal device IDs
    # Be careful: some are product serial numbers (preserve those)
    # Only redact if in WorkOrder/Comments context
    if field_name in ['onsite_action', 'problem_description', 'commentbody']:
        # Redact patterns like "SN: XYZ123456"
        text = re.sub(r'\bSN:?\s*[A-Z0-9]{8,}\b', '[SERIAL_REDACTED]', text, flags=re.IGNORECASE)

    # Stage 5: Customer site addresses (in WorkOrder descriptions)
    if field_name in ['onsite_action', 'problem_description']:
        # Patterns like "123 Main Street", "Customer Site: XYZ"
        text = re.sub(r'\b\d+\s+[A-Z][a-z]+\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)\b',
                      '[ADDRESS_REDACTED]', text, flags=re.IGNORECASE)

    # Stage 6: Named Entity Recognition for person names
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            # Avoid false positives with product names
            if not any(product in ent.text for product in ['HPE', 'ProLiant', 'Aruba', 'Synergy']):
                text = text.replace(ent.text, '[NAME_REDACTED]')

    # Stage 7: Email signatures (common in EmailMessage.TextBody)
    # Pattern: "Best regards,\nJohn Doe\nHPE Support"
    text = re.sub(r'(Best regards|Regards|Sincerely|Thanks),?\s*\n[A-Z][a-z]+\s+[A-Z][a-z]+',
                  '[SIGNATURE_REDACTED]', text, flags=re.IGNORECASE)

    return text
```

**Step 3: Complete Multi-Table Processing**
```python
def prepare_embedding_text(case_data, tasks=None, workorders=None, comments=None, emails=None):
    """
    Complete pipeline: HTML removal → PII removal → Concatenation
    Handles all 6 SFDC tables
    """
    # Step 3a: HTML Tag Removal (for fields that may contain HTML)
    case_data['resolution'] = remove_html_tags(case_data.get('resolution', ''))
    case_data['resolution_plain_text'] = remove_html_tags(case_data.get('resolution_plain_text', ''))

    # Step 3b: PII Removal for all fields
    # Case table fields
    for field in ['subject', 'description', 'cause_plain_text', 'issue_plain_text',
                  'gsd_environment_plain_text', 'resolution_plain_text',
                  'case_resolution_summary', 'close_comments']:
        if case_data.get(field):
            case_data[field] = remove_pii(case_data[field], field_name=field)

    # Task table PII removal
    if tasks:
        for task in tasks:
            if task.get('description'):
                task['description'] = remove_pii(task['description'], field_name='task_description')

    # WorkOrder table PII removal (high PII risk)
    if workorders:
        for wo in workorders:
            for field in ['problem_description', 'onsite_action', 'closing_summary']:
                if wo.get(field):
                    wo[field] = remove_pii(wo[field], field_name=field)

    # CaseComments PII removal (high PII risk)
    if comments:
        for comment in comments:
            if comment.get('commentbody'):
                comment['commentbody'] = remove_pii(comment['commentbody'], field_name='commentbody')

    # EmailMessage PII removal (HIGHEST PII risk)
    if emails:
        for email in emails:
            if email.get('subject'):
                email['subject'] = remove_pii(email['subject'], field_name='email_subject')
            if email.get('textbody'):
                email['textbody'] = remove_pii(email['textbody'], field_name='email_body')

    # Step 3c: Build composite text using our multi-table function
    composite = build_composite_text(case_data, tasks, workorders, comments, emails)

    # Step 3d: Final truncation (8192 tokens ≈ 32,000 chars)
    if len(composite) > 30000:
        # Intelligently truncate - keep Issue and Resolution, truncate middle sections
        composite = smart_truncate(composite, max_length=30000)

    return composite


def smart_truncate(text, max_length=30000):
    """
    Intelligently truncate while preserving Issue and Resolution sections
    """
    if len(text) <= max_length:
        return text

    lines = text.split('\n')
    essential_sections = []
    optional_sections = []

    current_section = None
    current_lines = []

    for line in lines:
        if '===' in line:
            if current_section:
                # Save previous section
                if current_section in ['ISSUE', 'RESOLUTION', 'METADATA']:
                    essential_sections.append('\n'.join(current_lines))
                else:
                    optional_sections.append('\n'.join(current_lines))
            current_section = line.strip('= ')
            current_lines = [line]
        else:
            current_lines.append(line)

    # Add last section
    if current_section:
        if current_section in ['ISSUE', 'RESOLUTION', 'METADATA']:
            essential_sections.append('\n'.join(current_lines))
        else:
            optional_sections.append('\n'.join(current_lines))

    # Build truncated text: Always keep essential, add optional until limit
    result = '\n\n'.join(essential_sections)

    for optional in optional_sections:
        if len(result) + len(optional) < max_length:
            result += '\n\n' + optional
        else:
            result += '\n\n[... TROUBLESHOOTING STEPS AND COMMENTS TRUNCATED ...]'
            break

    return result
```

### 1.1.3 Embedding Generation

**API Call to ChatHPE**
```python
def generate_embedding(text, batch_size=100):
    """
    Generate embeddings using ChatHPE text-embedding-3-large
    Batch processing for efficiency
    """
    import openai

    # Configure ChatHPE endpoint
    openai.api_base = "https://chathpe.internal.hpe.com/v1"
    openai.api_key = get_secret("chathpe_api_key")

    # Batch texts for efficiency
    embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]

        try:
            response = openai.Embedding.create(
                model="text-embedding-3-large",
                input=batch
            )

            batch_embeddings = [item['embedding'] for item in response['data']]
            embeddings.extend(batch_embeddings)

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            # Fallback to Nomic embeddings
            batch_embeddings = generate_nomic_embeddings(batch)
            embeddings.extend(batch_embeddings)

    return embeddings  # Returns list of 3,072-dim vectors
```

### 1.1.4 Weaviate Storage Schema

**Enhanced CaseVectorized Class Definition**
```python
case_schema = {
    "class": "CaseVectorized",
    "description": "Support case with semantic embeddings",
    "vectorizer": "none",  # We provide pre-computed embeddings
    "vectorIndexConfig": {
        "distance": "cosine",
        "efConstruction": 128,
        "maxConnections": 64
    },
    "properties": [
        # Identifiers
        {"name": "caseNumber", "dataType": ["text"], "indexInverted": True},
        {"name": "caseId", "dataType": ["text"], "indexInverted": True},

        # Original text fields (stored separately for display)
        {"name": "title", "dataType": ["text"], "indexInverted": False},
        {"name": "description", "dataType": ["text"], "indexInverted": False},
        {"name": "resolutionSummary", "dataType": ["text"], "indexInverted": False},

        # Composite text (what was embedded)
        {"name": "compositeText", "dataType": ["text"], "indexInverted": False},

        # Metadata for hybrid search
        {"name": "product", "dataType": ["text"], "indexInverted": True},
        {"name": "productFamily", "dataType": ["text"], "indexInverted": True},
        {"name": "category", "dataType": ["text"], "indexInverted": True},
        {"name": "status", "dataType": ["text"], "indexInverted": True},
        {"name": "priority", "dataType": ["text"], "indexInverted": True},

        # Dates
        {"name": "createdDate", "dataType": ["date"]},
        {"name": "closedDate", "dataType": ["date"]},

        # Vector metadata
        {"name": "embeddingModel", "dataType": ["text"]},
        {"name": "embeddingVersion", "dataType": ["text"]},
        {"name": "processedTimestamp", "dataType": ["date"]}
    ]
}
```

### 1.1.5 Data Load Process

**PySpark Pipeline Implementation**
```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, struct
from pyspark.sql.types import ArrayType, FloatType

def load_to_weaviate(df_cases):
    """
    Load processed cases with embeddings to Weaviate
    """
    import weaviate

    # Initialize Weaviate client
    client = weaviate.Client(
        url="https://weaviate.pcai.hpe.com",
        auth_client_secret=weaviate.AuthApiKey(api_key=get_secret("weaviate_key")),
        additional_headers={"X-Tenant": "tenant_cognate"}
    )

    # Prepare data batch
    batch_size = 100
    with client.batch(
        batch_size=batch_size,
        dynamic=True,
        timeout_retries=3,
        callback=check_batch_result
    ) as batch:

        for idx, row in df_cases.iterrows():
            # Prepare properties
            properties = {
                "caseNumber": row['CaseNumber'],
                "caseId": row['Id'],
                "title": row['Subject'],
                "description": row['Description'],
                "resolutionSummary": row['Resolution__c'],
                "compositeText": row['composite_text'],
                "product": row['Product__c'],
                "productFamily": extract_product_family(row['Product__c']),
                "category": row['Category__c'],
                "status": row['Status'],
                "priority": row['Priority'],
                "createdDate": row['CreatedDate'],
                "closedDate": row['ClosedDate'],
                "embeddingModel": "text-embedding-3-large",
                "embeddingVersion": "v1.0",
                "processedTimestamp": datetime.now().isoformat()
            }

            # Add with vector
            batch.add_data_object(
                data_object=properties,
                class_name="CaseVectorized",
                vector=row['embedding']  # 3,072-dim vector
            )

    logger.info(f"Loaded {len(df_cases)} cases to Weaviate")
```

### 1.1.6 Alternative Approach: Multi-Vector Storage (Future Enhancement)

For future optimization, we can store separate vectors:

```python
# Alternative schema with multiple vectors
case_schema_multivector = {
    "class": "CaseVectorizedMulti",
    "properties": [...],
    "vectors": {
        "issue": {
            "vectorizer": "none",
            "vectorIndexConfig": {"distance": "cosine"}
        },
        "resolution": {
            "vectorizer": "none",
            "vectorIndexConfig": {"distance": "cosine"}
        },
        "combined": {
            "vectorizer": "none",
            "vectorIndexConfig": {"distance": "cosine"}
        }
    }
}
```

**Tradeoff Analysis**:
| Approach | Storage Cost | Query Complexity | Accuracy | Implementation |
|----------|-------------|------------------|----------|----------------|
| Single Composite | Low (1x) | Simple | Good | ✅ Recommended |
| Multi-Vector | High (3x) | Complex | Better | Future Phase |

**Recommendation**: Start with single composite embedding for MVP, evaluate multi-vector in Phase 2 based on accuracy metrics.

---

## References
- ChatHPE API Documentation
- Weaviate Schema Configuration Guide
- OpenAI Embedding Best Practices
