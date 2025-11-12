# Section 5: PII Data Handling (Removal/Encryption)

## 5.1 Overview

**Objective**: Ensure zero PII (Personally Identifiable Information) in the vector database while maintaining data utility for semantic search and maintaining compliance with HPE data governance policies.

**Key Requirements**:
- **Zero PII** in Weaviate vector database
- **Deterministic PII removal** with pattern matching
- **Encryption** for data at rest and in transit
- **Audit trails** for all PII handling operations
- **Compliance** with GDPR, CCPA, and HPE internal policies

---

## 5.2 PII Classification Across 6 SFDC Tables

### 5.2.1 PII Categories and Table-Specific Risks

| Category | Examples | Risk Level | Tables at Risk | Handling |
|----------|----------|------------|----------------|----------|
| **Direct Identifiers** | Email addresses, phone numbers, employee IDs | Critical | EmailMessage (HIGH), CaseComments, WorkOrder | Remove |
| **Personal Names** | Customer names, engineer names, contact persons | High | CaseComments, EmailMessage, WorkOrder | Remove |
| **Network Identifiers** | IP addresses, MAC addresses | Medium | Case (Description), WorkOrder | Redact |
| **Location Data** | Street addresses, customer site locations | Medium | WorkOrder (HIGH), Case (Description) | Generalize |
| **System Identifiers** | Hostnames with person names, personal device serial numbers | Low | WorkOrder, Case | Selective removal |
| **Email Signatures** | Signature blocks with names, titles, contact info | High | EmailMessage (HIGH) | Remove |
| **Metadata** | Timestamps, case IDs, product names, error codes | None | All tables | Retain |

### 5.2.2 Table-Specific PII Risk Assessment

| Table | PII Risk | High-Risk Fields | Justification |
|-------|----------|------------------|---------------|
| **Case** | Medium | Description, GSD_Environment_Plain_Text, Close_Comments | May contain customer names, IPs, locations |
| **Task** | Low | Description | Usually technical, but may have engineer names |
| **WorkOrder** | **HIGH** | Problem_Description, Onsite_Action, Closing_Summary | Contains customer site addresses, engineer names, contact info |
| **CaseComments** | **HIGH** | CommentBody | Engineer discussions may include customer names, emails |
| **WorkOrderFeed** | Medium | Body | Progress updates may include names |
| **EmailMessage** | **CRITICAL** | Subject, TextBody | Email content with signatures, contact info, customer details |

---

## 5.3 PII Removal Strategy

### 5.3.1 Multi-Stage PII Detection and Removal

```python
import re
import spacy
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

# Load NLP model for named entity recognition
nlp = spacy.load("en_core_web_lg")

class PIIRemovalEngine:
    """
    Comprehensive PII removal with multiple detection methods
    """

    def __init__(self):
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()

        # Compile regex patterns for performance
        self.patterns = {
            'email': re.compile(
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                re.IGNORECASE
            ),
            'phone_us': re.compile(
                r'(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
                re.IGNORECASE
            ),
            'phone_intl': re.compile(
                r'\+[0-9]{1,3}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,9}',
                re.IGNORECASE
            ),
            'ipv4': re.compile(
                r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
            ),
            'ipv6': re.compile(
                r'\b(?:[A-F0-9]{1,4}:){7}[A-F0-9]{1,4}\b',
                re.IGNORECASE
            ),
            'mac_address': re.compile(
                r'\b(?:[0-9A-F]{2}[:-]){5}[0-9A-F]{2}\b',
                re.IGNORECASE
            ),
            'ssn': re.compile(
                r'\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b'
            ),
            'credit_card': re.compile(
                r'\b[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b'
            ),
            'employee_id': re.compile(
                r'\b(EMP|HPE|emp)[_-]?[0-9]{5,8}\b',
                re.IGNORECASE
            )
        }

    def remove_pii(self, text, field_name="", table_name="", audit_log=None):
        """
        Remove PII from text using multi-stage approach
        ENHANCED: Context-aware PII removal based on table and field

        Args:
            text: Text to clean
            field_name: Name of the field (e.g., 'commentbody', 'onsite_action')
            table_name: Source table (e.g., 'Case', 'WorkOrder', 'EmailMessage')
            audit_log: Optional audit logging object

        Returns: (cleaned_text, pii_detected_list)
        """
        if not text:
            return text, []

        original_text = text
        pii_detected = []

        # Determine PII removal aggressiveness based on table/field
        high_risk_fields = ['commentbody', 'textbody', 'onsite_action',
                            'problem_description', 'email_subject']
        is_high_risk = (field_name in high_risk_fields or
                        table_name in ['EmailMessage', 'CaseComments', 'WorkOrder'])

        # Pre-Stage: HTML tag removal (for Resolution, EmailMessage fields)
        if '<' in text and '>' in text:
            text = self._remove_html_tags(text)

        # Stage 1: Regex-based pattern matching (fast, deterministic)
        text, regex_detections = self._remove_regex_patterns(text)
        pii_detected.extend(regex_detections)

        # Stage 2: Email signature removal (for EmailMessage table)
        if table_name == 'EmailMessage' or field_name in ['textbody', 'email_body']:
            text, sig_detections = self._remove_email_signatures(text)
            pii_detected.extend(sig_detections)

        # Stage 3: Customer site address removal (for WorkOrder table)
        if table_name == 'WorkOrder' or field_name in ['onsite_action', 'problem_description']:
            text, addr_detections = self._remove_site_addresses(text)
            pii_detected.extend(addr_detections)

        # Stage 4: Named Entity Recognition (NER) for person names
        text, ner_detections = self._remove_person_names(text, is_high_risk=is_high_risk)
        pii_detected.extend(ner_detections)

        # Stage 5: Presidio-based detection (additional coverage)
        text, presidio_detections = self._remove_presidio_entities(text)
        pii_detected.extend(presidio_detections)

        # Stage 6: Custom HPE-specific patterns
        text, custom_detections = self._remove_custom_patterns(text)
        pii_detected.extend(custom_detections)

        # Log PII removal activity
        if audit_log and pii_detected:
            audit_log.append({
                'timestamp': datetime.now().isoformat(),
                'pii_types': [d['type'] for d in pii_detected],
                'count': len(pii_detected),
                'text_length': len(original_text)
            })

        return text, pii_detected

    def _remove_regex_patterns(self, text):
        """
        Remove PII using regex patterns
        """
        detections = []

        # Email addresses
        matches = self.patterns['email'].findall(text)
        if matches:
            text = self.patterns['email'].sub('[EMAIL_REDACTED]', text)
            detections.extend([{'type': 'email', 'pattern': 'regex'} for _ in matches])

        # Phone numbers (US format)
        matches = self.patterns['phone_us'].findall(text)
        if matches:
            text = self.patterns['phone_us'].sub('[PHONE_REDACTED]', text)
            detections.extend([{'type': 'phone', 'pattern': 'regex'} for _ in matches])

        # Phone numbers (International)
        matches = self.patterns['phone_intl'].findall(text)
        if matches:
            text = self.patterns['phone_intl'].sub('[PHONE_REDACTED]', text)
            detections.extend([{'type': 'phone_intl', 'pattern': 'regex'} for _ in matches])

        # IPv4 addresses
        matches = self.patterns['ipv4'].findall(text)
        if matches:
            text = self.patterns['ipv4'].sub('[IP_REDACTED]', text)
            detections.extend([{'type': 'ipv4', 'pattern': 'regex'} for _ in matches])

        # IPv6 addresses
        matches = self.patterns['ipv6'].findall(text)
        if matches:
            text = self.patterns['ipv6'].sub('[IP_REDACTED]', text)
            detections.extend([{'type': 'ipv6', 'pattern': 'regex'} for _ in matches])

        # MAC addresses
        matches = self.patterns['mac_address'].findall(text)
        if matches:
            text = self.patterns['mac_address'].sub('[MAC_REDACTED]', text)
            detections.extend([{'type': 'mac_address', 'pattern': 'regex'} for _ in matches])

        # SSN
        matches = self.patterns['ssn'].findall(text)
        if matches:
            text = self.patterns['ssn'].sub('[SSN_REDACTED]', text)
            detections.extend([{'type': 'ssn', 'pattern': 'regex'} for _ in matches])

        # Credit card numbers
        matches = self.patterns['credit_card'].findall(text)
        if matches:
            text = self.patterns['credit_card'].sub('[CC_REDACTED]', text)
            detections.extend([{'type': 'credit_card', 'pattern': 'regex'} for _ in matches])

        # Employee IDs
        matches = self.patterns['employee_id'].findall(text)
        if matches:
            text = self.patterns['employee_id'].sub('[EMPID_REDACTED]', text)
            detections.extend([{'type': 'employee_id', 'pattern': 'regex'} for _ in matches])

        return text, detections

    def _remove_person_names(self, text):
        """
        Remove person names using spaCy NER
        """
        detections = []

        doc = nlp(text)

        for ent in doc.ents:
            if ent.label_ == "PERSON":
                # Only redact if name appears to be a real person (not product names)
                if self._is_likely_person_name(ent.text):
                    text = text.replace(ent.text, '[NAME_REDACTED]')
                    detections.append({
                        'type': 'person_name',
                        'pattern': 'ner',
                        'confidence': 0.9
                    })

        return text, detections

    def _remove_html_tags(self, text):
        """
        NEW: Remove HTML tags from Resolution and EmailMessage fields
        Example: "<p>DIMM replaced</p>" → "DIMM replaced"
        """
        from html import unescape
        import re

        # Unescape HTML entities
        text = unescape(text)

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)

        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _remove_email_signatures(self, text):
        """
        NEW: Remove email signatures from EmailMessage.TextBody
        Common patterns:
        - "Best regards,\nJohn Doe\nHPE Support Engineer"
        - "Thanks,\nJane Smith\nEmail: jane@hpe.com"
        """
        detections = []

        # Pattern 1: Signature with name and title
        sig_pattern1 = re.compile(
            r'(Best regards|Regards|Sincerely|Thanks|Thank you),?\s*\n+'
            r'[A-Z][a-z]+\s+[A-Z][a-z]+\s*\n+'
            r'.*?(Engineer|Support|Team|Specialist)',
            re.IGNORECASE | re.MULTILINE
        )
        matches = sig_pattern1.findall(text)
        if matches:
            text = sig_pattern1.sub('[SIGNATURE_REDACTED]', text)
            detections.extend([{'type': 'email_signature', 'pattern': 'regex'} for _ in matches])

        # Pattern 2: Email footer with contact info
        footer_pattern = re.compile(
            r'(--+|\n{2,})(.*?@.*?\.(com|net|org))',
            re.IGNORECASE | re.MULTILINE
        )
        matches = footer_pattern.findall(text)
        if matches:
            text = footer_pattern.sub('[FOOTER_REDACTED]', text)
            detections.extend([{'type': 'email_footer', 'pattern': 'regex'} for _ in matches])

        return text, detections

    def _remove_site_addresses(self, text):
        """
        NEW: Remove customer site addresses from WorkOrder fields
        Examples:
        - "123 Main Street, Building 5"
        - "Customer Site: 456 Oak Avenue"
        - "Location: 789 Tech Park Drive"
        """
        detections = []

        # Pattern: Street addresses
        address_pattern = re.compile(
            r'\b\d+\s+[A-Z][a-z]+(\s+[A-Z][a-z]+)*\s+'
            r'(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct|Circle|Cir|Place|Pl)',
            re.IGNORECASE
        )
        matches = address_pattern.findall(text)
        if matches:
            text = address_pattern.sub('[ADDRESS_REDACTED]', text)
            detections.extend([{'type': 'street_address', 'pattern': 'regex'} for _ in matches])

        # Pattern: "Customer Site: ..."
        site_pattern = re.compile(
            r'(Customer Site|Site|Location|Address):\s*[^\n]{10,100}',
            re.IGNORECASE
        )
        matches = site_pattern.findall(text)
        if matches:
            text = site_pattern.sub(r'\1: [SITE_REDACTED]', text)
            detections.extend([{'type': 'customer_site', 'pattern': 'regex'} for _ in matches])

        return text, detections

    def _is_likely_person_name(self, name):
        """
        Filter out false positives (e.g., product names)
        """
        # Exclude common product/tech terms
        tech_terms = ['ProLiant', 'Synergy', 'Aruba', 'Gen10', 'iLO',
                      'SimpliVity', 'Primera', 'Nimble', 'Apollo', 'HPE']

        if any(term.lower() in name.lower() for term in tech_terms):
            return False

        # Require at least 2 words for person name
        if len(name.split()) < 2:
            return False

        return True

    def _remove_presidio_entities(self, text):
        """
        Use Microsoft Presidio for additional PII detection
        """
        detections = []

        try:
            # Analyze text for PII
            results = self.analyzer.analyze(
                text=text,
                language='en',
                entities=[
                    'PERSON', 'EMAIL_ADDRESS', 'PHONE_NUMBER',
                    'LOCATION', 'CREDIT_CARD', 'US_SSN'
                ]
            )

            # Anonymize detected entities
            anonymized = self.anonymizer.anonymize(
                text=text,
                analyzer_results=results
            )

            text = anonymized.text

            # Track detections
            for result in results:
                detections.append({
                    'type': result.entity_type,
                    'pattern': 'presidio',
                    'score': result.score
                })

        except Exception as e:
            logger.warning(f"Presidio analysis failed: {e}")

        return text, detections

    def _remove_custom_patterns(self, text):
        """
        HPE-specific custom patterns
        """
        detections = []

        # HPE email domains (additional safety net)
        hpe_email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@(hpe\.com|hp\.com|aruba\.com)\b',
            re.IGNORECASE
        )
        matches = hpe_email_pattern.findall(text)
        if matches:
            text = hpe_email_pattern.sub('[HPE_EMAIL_REDACTED]', text)
            detections.extend([{'type': 'hpe_email', 'pattern': 'custom'} for _ in matches])

        # Hostnames with person names (e.g., "john-doe-pc")
        hostname_pattern = re.compile(
            r'\b[a-z]+-[a-z]+-(?:pc|laptop|server|workstation)\b',
            re.IGNORECASE
        )
        matches = hostname_pattern.findall(text)
        if matches:
            text = hostname_pattern.sub('[HOSTNAME_REDACTED]', text)
            detections.extend([{'type': 'personal_hostname', 'pattern': 'custom'} for _ in matches])

        return text, detections
```

### 5.3.2 PII Removal Pipeline Integration

```python
def process_case_with_pii_removal(case_record):
    """
    Process SFDC case record with comprehensive PII removal
    """
    pii_engine = PIIRemovalEngine()
    audit_log = []

    cleaned_record = case_record.copy()

    # Fields to clean
    text_fields = ['Subject', 'Description', 'Resolution__c', 'Comments__c']

    total_pii_detected = 0

    for field in text_fields:
        if field in cleaned_record and cleaned_record[field]:
            original_text = cleaned_record[field]

            # Remove PII
            cleaned_text, pii_detected = pii_engine.remove_pii(
                original_text,
                audit_log=audit_log
            )

            cleaned_record[field] = cleaned_text
            total_pii_detected += len(pii_detected)

    # Store audit log
    store_pii_audit_log(
        case_id=case_record['Id'],
        case_number=case_record['CaseNumber'],
        pii_detected_count=total_pii_detected,
        audit_log=audit_log
    )

    # Flag if PII detected
    cleaned_record['_pii_removed'] = total_pii_detected > 0
    cleaned_record['_pii_count'] = total_pii_detected

    return cleaned_record
```

---

## 5.4 Encryption Strategy

### 5.4.1 Encryption at Rest

**Staging Layer Encryption**:
```python
def encrypt_staging_data():
    """
    Encrypt data at rest in staging folder on PC AI

    Uses: AES-256 encryption with key from HPE Vault
    """
    from cryptography.fernet import Fernet
    import base64

    # Get encryption key from secure vault
    encryption_key = get_secret_from_vault('staging_encryption_key')

    # Initialize Fernet cipher
    cipher = Fernet(encryption_key)

    # Encrypt parquet files
    staging_files = glob.glob('/staging/sfdc_cases/*.parquet')

    for file_path in staging_files:
        # Read file
        with open(file_path, 'rb') as f:
            file_data = f.read()

        # Encrypt
        encrypted_data = cipher.encrypt(file_data)

        # Write encrypted file
        encrypted_path = file_path + '.enc'
        with open(encrypted_path, 'wb') as f:
            f.write(encrypted_data)

        # Remove original (if policy requires)
        # os.remove(file_path)

        logger.info(f"Encrypted {file_path}")
```

**Weaviate Persistent Volume Encryption**:
```yaml
# Kubernetes PVC with encryption
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: weaviate-data-pvc
  namespace: vector-search
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 3Ti
  storageClassName: encrypted-ssd  # Use encrypted storage class
```

**Encrypted Storage Class Configuration**:
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: encrypted-ssd
provisioner: kubernetes.io/aws-ebs  # Or appropriate provisioner
parameters:
  type: gp3
  encrypted: "true"
  kmsKeyId: "arn:aws:kms:us-west-2:123456789:key/xxx"  # KMS key
```

### 5.4.2 Encryption in Transit

**TLS 1.3 for All Communications**:
```python
# Weaviate client with TLS
import weaviate

client = weaviate.Client(
    url="https://weaviate.pcai.hpe.com:8080",
    auth_client_secret=weaviate.AuthApiKey(api_key=get_secret("weaviate_key")),
    additional_headers={
        "X-Tenant": "tenant_cognate"
    },
    # Force TLS 1.3
    additional_config=weaviate.AdditionalConfig(
        connection_config=weaviate.ConnectionConfig(
            session_pool_connections=20,
            session_pool_maxsize=100,
            timeout_config=(5, 60)  # (connect, read) timeout
        )
    )
)
```

**ChatHPE API with mTLS**:
```python
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.ssl_ import create_urllib3_context

class TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.minimum_version = ssl.TLSVersion.TLSv1_3
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)

# Use TLS 1.3 for ChatHPE requests
session = requests.Session()
session.mount('https://', TLSAdapter())

response = session.post(
    'https://chathpe.internal.hpe.com/v1/embeddings',
    headers={'Authorization': f'Bearer {get_secret("chathpe_api_key")}'},
    json={'model': 'text-embedding-3-large', 'input': texts},
    verify=True  # Verify SSL certificate
)
```

---

## 5.5 PII Audit and Compliance

### 5.5.1 PII Audit Log Schema

```sql
CREATE TABLE pii_audit_log (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id VARCHAR(255) NOT NULL,
    case_number VARCHAR(255) NOT NULL,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    pii_detected_count INT NOT NULL,
    pii_types JSONB,  -- Array of detected PII types
    field_wise_counts JSONB,  -- Breakdown by field
    removal_method VARCHAR(50),  -- regex, ner, presidio, custom
    operator_id VARCHAR(100),  -- System user/job ID
    data_classification VARCHAR(50) DEFAULT 'HPE_CONFIDENTIAL',
    compliance_flags JSONB
);

CREATE INDEX idx_pii_audit_case ON pii_audit_log(case_id);
CREATE INDEX idx_pii_audit_timestamp ON pii_audit_log(processed_at);
CREATE INDEX idx_pii_audit_detection ON pii_audit_log(pii_detected_count);
```

### 5.5.2 PII Compliance Reporting

```python
def generate_pii_compliance_report(start_date, end_date):
    """
    Generate compliance report for audit purposes

    Includes:
    - Total records processed
    - PII detection rate
    - PII types detected
    - Zero-leak validation results
    """
    query = """
        SELECT
            COUNT(*) as total_records,
            SUM(pii_detected_count) as total_pii_detected,
            COUNT(CASE WHEN pii_detected_count > 0 THEN 1 END) as records_with_pii,
            jsonb_object_agg(pii_type, count) as pii_type_breakdown
        FROM (
            SELECT
                case_id,
                pii_detected_count,
                jsonb_array_elements_text(pii_types) as pii_type,
                COUNT(*) as count
            FROM pii_audit_log
            WHERE processed_at BETWEEN %s AND %s
            GROUP BY case_id, pii_detected_count, pii_type
        ) subquery
    """

    results = db.execute(query, (start_date, end_date))

    report = f"""
# PII Compliance Report
**Period**: {start_date} to {end_date}
**Generated**: {datetime.now().isoformat()}

## Summary

- **Total Records Processed**: {results['total_records']:,}
- **Records with PII Detected**: {results['records_with_pii']:,} ({results['records_with_pii']/results['total_records']*100:.1f}%)
- **Total PII Instances Removed**: {results['total_pii_detected']:,}

## PII Type Breakdown

{format_pii_breakdown(results['pii_type_breakdown'])}

## Zero-Leak Validation

{run_zero_leak_validation()}

## Compliance Status

✓ All PII removed before vector embedding
✓ Encryption enabled for data at rest
✓ TLS 1.3 enforced for data in transit
✓ Audit trail complete and immutable
✓ GDPR Article 17 (Right to Erasure) compliant
✓ CCPA compliance maintained

---
**Auditor**: Algoleap QA Team
**Approved By**: [Security Officer]
"""

    # Save report
    save_compliance_report(report, start_date, end_date)

    return report

def run_zero_leak_validation():
    """
    Validate that no PII exists in Weaviate
    """
    # Sample 1000 random records from Weaviate
    sample_records = get_random_weaviate_records(n=1000)

    pii_engine = PIIRemovalEngine()
    leaks_detected = 0

    for record in sample_records:
        composite_text = record.get('compositeText', '')

        # Scan for PII
        _, pii_detected = pii_engine.remove_pii(composite_text)

        if pii_detected:
            leaks_detected += 1
            logger.error(f"PII LEAK DETECTED in case {record['caseNumber']}: {pii_detected}")

            # Critical alert
            send_critical_alert(
                subject='PII LEAK DETECTED IN WEAVIATE',
                message=f"Case {record['caseNumber']} contains PII: {[p['type'] for p in pii_detected]}",
                severity='critical'
            )

    if leaks_detected == 0:
        return "✓ Zero PII leaks detected in sample of 1,000 records"
    else:
        return f"✗ CRITICAL: {leaks_detected} PII leaks detected in sample"
```

---

## 5.6 Red Team Testing for PII Detection

### 5.6.1 Adversarial PII Testing

```python
def run_pii_red_team_tests():
    """
    Adversarial testing to find edge cases in PII detection

    Tests include:
    - Obfuscated emails (e.g., john[dot]doe[at]hpe[dot]com)
    - Formatted phone numbers (e.g., 1.800.CALL.HPE)
    - Partial PII (e.g., j***@hpe.com)
    - Encoded PII (Base64, URL encoding)
    """
    test_cases = [
        {
            'description': 'Obfuscated email',
            'text': 'Contact john[dot]doe[at]hpe[dot]com for support',
            'expected_pii': ['email']
        },
        {
            'description': 'Phone with letters',
            'text': 'Call 1-800-CALL-HPE for assistance',
            'expected_pii': ['phone']
        },
        {
            'description': 'Partial email',
            'text': 'Email sent to j***@hpe.com',
            'expected_pii': ['email']
        },
        {
            'description': 'IP in different format',
            'text': 'Server at 192[.]168[.]1[.]1 is down',
            'expected_pii': ['ip']
        },
        {
            'description': 'Name in username',
            'text': 'User john.doe logged in',
            'expected_pii': ['person_name']
        },
        {
            'description': 'Encoded email',
            'text': f'Contact {base64.b64encode(b"john@hpe.com").decode()}',
            'expected_pii': ['email']
        }
    ]

    pii_engine = PIIRemovalEngine()
    results = []

    for test in test_cases:
        cleaned, detected = pii_engine.remove_pii(test['text'])

        detected_types = [d['type'] for d in detected]

        passed = all(exp in str(detected_types) for exp in test['expected_pii'])

        results.append({
            'description': test['description'],
            'original': test['text'],
            'cleaned': cleaned,
            'detected': detected_types,
            'expected': test['expected_pii'],
            'status': 'PASS' if passed else 'FAIL'
        })

        if not passed:
            logger.warning(f"Red team test FAILED: {test['description']}")

    # Generate report
    generate_red_team_report(results)

    return results
```

---

## 5.7 Data Classification and Labeling

### 5.7.1 Automatic Data Classification

```python
def classify_data_sensitivity(record):
    """
    Classify data sensitivity level

    Levels:
    - PUBLIC: No sensitive data
    - INTERNAL: HPE internal use only
    - CONFIDENTIAL: Contains business-sensitive info
    - RESTRICTED: Contains PII or highly sensitive data
    """
    classification = 'INTERNAL'  # Default

    # Check for PII
    pii_engine = PIIRemovalEngine()
    _, pii_detected = pii_engine.remove_pii(record.get('description', ''))

    if pii_detected:
        classification = 'RESTRICTED'
        logger.warning(f"Record {record['caseNumber']} classified as RESTRICTED due to PII")

    # Check for confidential keywords
    confidential_keywords = [
        'confidential', 'proprietary', 'trade secret',
        'password', 'secret', 'credential'
    ]

    text = f"{record.get('Subject', '')} {record.get('Description', '')}".lower()

    if any(keyword in text for keyword in confidential_keywords):
        classification = 'CONFIDENTIAL'

    return classification

def apply_data_labels(record, classification):
    """
    Apply data classification labels to record
    """
    labels = {
        'data_classification': classification,
        'pii_status': 'removed' if record.get('_pii_removed') else 'none_detected',
        'encryption_required': classification in ['CONFIDENTIAL', 'RESTRICTED'],
        'retention_period_days': 2555 if classification == 'RESTRICTED' else 3650,  # 7 or 10 years
        'data_owner': 'HPE_GRS_TEAM',
        'compliance_tags': ['GDPR', 'CCPA', 'HPE_DATA_POLICY']
    }

    return labels
```

---

## Summary: PII Handling Checklist

### Pre-Processing
- [ ] PII detection engine initialized (regex + NER + Presidio)
- [ ] Custom HPE patterns configured
- [ ] Audit logging enabled

### Processing
- [ ] All text fields scanned for PII
- [ ] Multi-stage PII removal applied
- [ ] PII audit log created for each record
- [ ] Data classification applied

### Post-Processing
- [ ] Zero-leak validation performed
- [ ] Encryption applied (at rest and in transit)
- [ ] Compliance report generated
- [ ] Red team testing passed

### Ongoing
- [ ] Weekly PII audit reports
- [ ] Quarterly red team testing
- [ ] Annual compliance certification

---

## References
- Microsoft Presidio Documentation
- GDPR Article 17 (Right to Erasure)
- CCPA Privacy Requirements
- HPE Data Classification Policy
- NIST SP 800-122 (PII Protection)
