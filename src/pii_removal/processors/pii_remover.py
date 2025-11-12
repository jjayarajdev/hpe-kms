"""
PII Removal and Masking Processor (KMS 2.6)

Multi-stage PII removal using 6 stages:
0. Pre-Stage: HTML Cleanup (already done in embedding_generator.py)
1. Stage 1: Regex Pattern Matching (emails, phones, IPs, SSNs, etc.)
2. Stage 2: Email Signature Removal (EmailMessage table only)
3. Stage 3: Site Address Removal (WorkOrder table only)
4. Stage 4: Named Entity Recognition (person names with spaCy)
5. Stage 5: Presidio Detection (additional PII types)
6. Stage 6: Custom HPE Patterns (employee IDs, hostnames)

Detection Rate Target: >95%
False Positive Target: <5%
Processing Time Target: <200ms per case

Task Reference: Phase 2, Task 2.3
Updated: November 2025 (KMS 2.6 alignment)
"""

from typing import List, Dict, Tuple, Optional, Set
import logging
import re


class PIIRemover:
    """Removes or masks PII from text using 6-stage detection pipeline"""

    def __init__(self, table_name: Optional[str] = None):
        """
        Initialize PII Remover with all 6 stages

        Args:
            table_name: Name of source table for context-aware processing
        """
        self.logger = logging.getLogger(__name__)
        self.table_name = table_name

        # Compile regex patterns for performance
        self._compile_patterns()

        # TODO: Initialize AI/ML models when dependencies available
        # import spacy
        # from presidio_analyzer import AnalyzerEngine
        #
        # self.nlp = spacy.load("en_core_web_sm")
        # self.presidio_analyzer = AnalyzerEngine()

        # HPE product whitelist (not person names)
        self.product_whitelist = {
            'proliant', 'synergy', 'apollo', 'primera', 'nimble',
            'ilo', 'oneview', 'infosight', 'aruba', 'simplivity',
            'greenlake', 'ezmeral', 'alletra', 'edgeline'
        }

    def _compile_patterns(self):
        """Compile regex patterns for Stage 1 (performance optimization)"""

        # Email pattern (RFC 5322 simplified)
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        )

        # Phone patterns (US and international)
        self.phone_patterns = [
            re.compile(r'\b\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'),  # US
            re.compile(r'\b\+[0-9]{1,3}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,9}\b'),  # International
        ]

        # IP addresses
        self.ip_patterns = [
            re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),  # IPv4
            re.compile(r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b'),  # IPv6
        ]

        # MAC address
        self.mac_pattern = re.compile(
            r'\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b'
        )

        # Social Security Number
        self.ssn_pattern = re.compile(
            r'\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b'
        )

        # Credit Card (simplified - 13-19 digits)
        self.cc_pattern = re.compile(
            r'\b[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{3,4}\b'
        )

        # Street Address (Stage 3)
        self.address_patterns = [
            re.compile(r'\b\d+\s+[A-Z][a-z]+\s+(Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Way|Boulevard|Blvd|Court|Ct)[,\s]', re.IGNORECASE),
            re.compile(r'Building\s+\d+', re.IGNORECASE),
            re.compile(r'\b[A-Z][a-z]+,\s+[A-Z]{2}\s+\d{5}\b'),  # City, State ZIP
        ]

        # Email Signature patterns (Stage 2)
        self.signature_patterns = [
            re.compile(r'(Best regards|Regards|Sincerely|Thanks|Thank you)[,\n][\s\S]*', re.IGNORECASE),
            re.compile(r'(VP of|Senior|Director|Manager|Engineer)[,\s]+[\w\s]+\n', re.IGNORECASE),
        ]

        # HPE Employee ID patterns (Stage 6)
        self.employee_id_patterns = [
            re.compile(r'\bEMP_\d{5,}\b'),
            re.compile(r'\bHPE-\d{5,}\b'),
        ]

        # Personal hostname patterns (Stage 6)
        self.hostname_pattern = re.compile(
            r'\b[a-z]+-[a-z]+-(?:pc|laptop|workstation|desktop)\b',
            re.IGNORECASE
        )

    def detect_all_pii(
        self,
        text: str,
        table_name: Optional[str] = None
    ) -> List[Dict[str, any]]:
        """
        Run all 6 detection stages and merge results

        Args:
            text: Input text
            table_name: Table name for context-aware processing

        Returns:
            Merged list of all PII detections
        """
        if not text:
            return []

        table = table_name or self.table_name
        detections = []

        # Stage 1: Regex Pattern Matching (all tables)
        detections.extend(self._stage1_regex_detection(text))

        # Stage 2: Email Signature Removal (EmailMessage table only)
        if table and table.lower() == 'emailmessage':
            detections.extend(self._stage2_signature_detection(text))

        # Stage 3: Site Address Removal (WorkOrder table only)
        if table and table.lower() == 'workorder':
            detections.extend(self._stage3_address_detection(text))

        # Stage 4: Named Entity Recognition (all tables)
        # TODO: Enable when spaCy is available
        # detections.extend(self._stage4_ner_detection(text))

        # Stage 5: Presidio Detection (all tables)
        # TODO: Enable when Presidio is available
        # detections.extend(self._stage5_presidio_detection(text))

        # Stage 6: Custom HPE Patterns (all tables)
        detections.extend(self._stage6_custom_hpe_patterns(text))

        # Merge and deduplicate overlapping detections
        merged_detections = self._merge_detections(detections)

        return merged_detections

    def _stage1_regex_detection(self, text: str) -> List[Dict[str, any]]:
        """
        Stage 1: Regex Pattern Matching

        Fast, deterministic detection of:
        - Emails
        - Phone numbers
        - IP addresses
        - MAC addresses
        - SSNs
        - Credit cards

        Args:
            text: Input text

        Returns:
            List of detections with start, end, type, confidence
        """
        detections = []

        # Email addresses
        for match in self.email_pattern.finditer(text):
            detections.append({
                'start': match.start(),
                'end': match.end(),
                'type': 'EMAIL',
                'text': match.group(),
                'confidence': 1.0,
                'stage': 'regex'
            })

        # Phone numbers
        for pattern in self.phone_patterns:
            for match in pattern.finditer(text):
                detections.append({
                    'start': match.start(),
                    'end': match.end(),
                    'type': 'PHONE',
                    'text': match.group(),
                    'confidence': 1.0,
                    'stage': 'regex'
                })

        # IP addresses
        for pattern in self.ip_patterns:
            for match in pattern.finditer(text):
                detections.append({
                    'start': match.start(),
                    'end': match.end(),
                    'type': 'IP_ADDRESS',
                    'text': match.group(),
                    'confidence': 1.0,
                    'stage': 'regex'
                })

        # MAC addresses
        for match in self.mac_pattern.finditer(text):
            detections.append({
                'start': match.start(),
                'end': match.end(),
                'type': 'MAC_ADDRESS',
                'text': match.group(),
                'confidence': 1.0,
                'stage': 'regex'
            })

        # Social Security Numbers
        for match in self.ssn_pattern.finditer(text):
            detections.append({
                'start': match.start(),
                'end': match.end(),
                'type': 'SSN',
                'text': match.group(),
                'confidence': 1.0,
                'stage': 'regex'
            })

        # Credit Cards
        for match in self.cc_pattern.finditer(text):
            detections.append({
                'start': match.start(),
                'end': match.end(),
                'type': 'CREDIT_CARD',
                'text': match.group(),
                'confidence': 0.9,  # May have false positives
                'stage': 'regex'
            })

        return detections

    def _stage2_signature_detection(self, text: str) -> List[Dict[str, any]]:
        """
        Stage 2: Email Signature Removal

        Detects and removes entire email signature blocks.
        Only applied to EmailMessage table (CRITICAL risk).

        Common patterns:
        - Best regards / Sincerely / Thanks
        - Name + Title + Company
        - Contact information in signature

        Args:
            text: Input text

        Returns:
            List of signature block detections
        """
        detections = []

        for pattern in self.signature_patterns:
            for match in pattern.finditer(text):
                detections.append({
                    'start': match.start(),
                    'end': match.end(),
                    'type': 'EMAIL_SIGNATURE',
                    'text': match.group(),
                    'confidence': 0.85,
                    'stage': 'signature'
                })

        return detections

    def _stage3_address_detection(self, text: str) -> List[Dict[str, any]]:
        """
        Stage 3: Site Address Removal

        Detects customer site addresses and locations.
        Only applied to WorkOrder table (HIGH risk).

        Patterns:
        - Street addresses (123 Main Street, Building 5)
        - City, State ZIP codes
        - Building numbers

        Args:
            text: Input text

        Returns:
            List of address detections
        """
        detections = []

        for pattern in self.address_patterns:
            for match in pattern.finditer(text):
                detections.append({
                    'start': match.start(),
                    'end': match.end(),
                    'type': 'SITE_ADDRESS',
                    'text': match.group(),
                    'confidence': 0.8,
                    'stage': 'address'
                })

        return detections

    def _stage4_ner_detection(self, text: str) -> List[Dict[str, any]]:
        """
        Stage 4: Named Entity Recognition (Person Names)

        Uses spaCy NLP model to detect person names.
        Smart filtering to avoid false positives (product names).

        Protected entities (NOT PII):
        - HPE product names (ProLiant, Synergy, etc.)
        - Technical terms
        - Error codes

        Args:
            text: Input text

        Returns:
            List of person name detections
        """
        detections = []

        # TODO: Implement when spaCy is available
        # doc = self.nlp(text)
        #
        # for ent in doc.ents:
        #     if ent.label_ == 'PERSON':
        #         # Check if it's in product whitelist
        #         if ent.text.lower() not in self.product_whitelist:
        #             detections.append({
        #                 'start': ent.start_char,
        #                 'end': ent.end_char,
        #                 'type': 'PERSON_NAME',
        #                 'text': ent.text,
        #                 'confidence': 0.85,
        #                 'stage': 'ner'
        #             })

        return detections

    def _stage5_presidio_detection(self, text: str) -> List[Dict[str, any]]:
        """
        Stage 5: Presidio Additional Detection

        Microsoft Presidio library for additional PII types:
        - Medical IDs
        - Driver's licenses
        - Usernames
        - Credit card (additional check)
        - Edge cases missed by earlier stages

        Args:
            text: Input text

        Returns:
            List of additional PII detections
        """
        detections = []

        # TODO: Implement when Presidio is available
        # results = self.presidio_analyzer.analyze(
        #     text=text,
        #     language='en',
        #     entities=['PERSON', 'EMAIL_ADDRESS', 'PHONE_NUMBER', 'CREDIT_CARD', 'US_SSN']
        # )
        #
        # for result in results:
        #     detections.append({
        #         'start': result.start,
        #         'end': result.end,
        #         'type': result.entity_type,
        #         'text': text[result.start:result.end],
        #         'confidence': result.score,
        #         'stage': 'presidio'
        #     })

        return detections

    def _stage6_custom_hpe_patterns(self, text: str) -> List[Dict[str, any]]:
        """
        Stage 6: Custom HPE Patterns

        HPE-specific PII patterns:
        - Employee IDs (EMP_12345, HPE-67890)
        - Personal hostnames (john-doe-pc, smith-laptop)
        - HPE email domains (extra check for @hpe.com, @hp.com, @aruba.com)

        Final safety net for organization-specific identifiers.

        Args:
            text: Input text

        Returns:
            List of HPE-specific PII detections
        """
        detections = []

        # Employee IDs
        for pattern in self.employee_id_patterns:
            for match in pattern.finditer(text):
                detections.append({
                    'start': match.start(),
                    'end': match.end(),
                    'type': 'EMPLOYEE_ID',
                    'text': match.group(),
                    'confidence': 1.0,
                    'stage': 'custom_hpe'
                })

        # Personal hostnames
        for match in self.hostname_pattern.finditer(text):
            detections.append({
                'start': match.start(),
                'end': match.end(),
                'type': 'PERSONAL_HOSTNAME',
                'text': match.group(),
                'confidence': 0.75,
                'stage': 'custom_hpe'
            })

        return detections

    def _merge_detections(self, detections: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """
        Merge multiple detection results and remove duplicates

        Handles overlapping detections by keeping the one with:
        - Highest confidence
        - Longest match (if confidence is equal)

        Args:
            detections: List of all detections from all stages

        Returns:
            Merged and deduplicated detection list
        """
        if not detections:
            return []

        # Sort by start position
        sorted_detections = sorted(detections, key=lambda x: x['start'])

        merged = []
        current = sorted_detections[0]

        for detection in sorted_detections[1:]:
            # Check for overlap
            if detection['start'] < current['end']:
                # Overlapping - keep the one with higher confidence
                if detection['confidence'] > current['confidence']:
                    current = detection
                elif detection['confidence'] == current['confidence']:
                    # Same confidence - keep longer match
                    if (detection['end'] - detection['start']) > (current['end'] - current['start']):
                        current = detection
            else:
                # No overlap - add current and move to next
                merged.append(current)
                current = detection

        # Add last detection
        merged.append(current)

        return merged

    def remove_pii(
        self,
        text: str,
        table_name: Optional[str] = None,
        replacement_map: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Remove PII from text and replace with redaction tokens

        Args:
            text: Input text
            table_name: Table name for context-aware processing
            replacement_map: Custom replacement tokens by PII type

        Returns:
            Text with PII removed
        """
        if not text:
            return text

        # Default replacement tokens
        default_replacements = {
            'EMAIL': '[EMAIL_REDACTED]',
            'PHONE': '[PHONE_REDACTED]',
            'IP_ADDRESS': '[IP_REDACTED]',
            'MAC_ADDRESS': '[MAC_REDACTED]',
            'SSN': '[SSN_REDACTED]',
            'CREDIT_CARD': '[CC_REDACTED]',
            'PERSON_NAME': '[NAME_REDACTED]',
            'EMAIL_SIGNATURE': '[SIGNATURE_REDACTED]',
            'SITE_ADDRESS': '[ADDRESS_REDACTED]',
            'EMPLOYEE_ID': '[EMPID_REDACTED]',
            'PERSONAL_HOSTNAME': '[HOSTNAME_REDACTED]'
        }

        # Use custom replacements if provided
        replacements = replacement_map or default_replacements

        # Detect all PII
        detections = self.detect_all_pii(text, table_name)

        if not detections:
            return text

        # Sort detections by position (reverse order for replacement)
        detections_sorted = sorted(detections, key=lambda x: x['start'], reverse=True)

        # Replace PII spans with redaction tokens
        cleaned_text = text
        for detection in detections_sorted:
            pii_type = detection['type']
            replacement = replacements.get(pii_type, '[REDACTED]')

            cleaned_text = (
                cleaned_text[:detection['start']] +
                replacement +
                cleaned_text[detection['end']:]
            )

        return cleaned_text

    def remove_pii_batch(
        self,
        texts: List[str],
        table_names: Optional[List[str]] = None
    ) -> List[str]:
        """
        Remove PII from batch of texts (optimized for throughput)

        Target: Process ≥ 300 cases/minute
        Target per case: <200ms

        Args:
            texts: List of input texts
            table_names: List of table names (one per text)

        Returns:
            List of cleaned texts
        """
        if not texts:
            return []

        # If table names not provided, use instance default
        if table_names is None:
            table_names = [self.table_name] * len(texts)

        # Process each text
        cleaned_texts = []
        for text, table_name in zip(texts, table_names):
            cleaned = self.remove_pii(text, table_name)
            cleaned_texts.append(cleaned)

        return cleaned_texts

    def get_pii_report(
        self,
        text: str,
        table_name: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Generate detailed PII detection report

        Args:
            text: Input text
            table_name: Table name for context

        Returns:
            Report with detection counts by type, stage, confidence
        """
        detections = self.detect_all_pii(text, table_name)

        # Count by type
        pii_by_type = {}
        for detection in detections:
            pii_type = detection['type']
            pii_by_type[pii_type] = pii_by_type.get(pii_type, 0) + 1

        # Count by stage
        pii_by_stage = {}
        for detection in detections:
            stage = detection['stage']
            pii_by_stage[stage] = pii_by_stage.get(stage, 0) + 1

        # Average confidence
        avg_confidence = sum(d['confidence'] for d in detections) / len(detections) if detections else 0

        report = {
            'total_pii_count': len(detections),
            'pii_by_type': pii_by_type,
            'pii_by_stage': pii_by_stage,
            'avg_confidence': avg_confidence,
            'has_pii': len(detections) > 0,
            'table_name': table_name or self.table_name,
            'detections': detections
        }

        return report


def main():
    """Test PII remover with case data examples"""
    print("=" * 70)
    print("Testing 6-Stage PII Removal (KMS 2.6)")
    print("=" * 70)
    print()

    # Test cases from different tables
    test_cases = [
        {
            'name': 'EmailMessage (CRITICAL Risk)',
            'table': 'emailmessage',
            'text': '''Hi Support,

ProLiant DL380 Gen11 server at 192.168.10.50 is experiencing boot failures.
Error: iLO_400_MemoryErrors

Contact John Smith at john.smith@acme.com or +1-408-555-1234.

Best regards,
Sarah Johnson
Senior Engineer
HPE Support
Phone: +1-650-555-9999
Email: sarah.johnson@hpe.com'''
        },
        {
            'name': 'WorkOrder (HIGH Risk)',
            'table': 'workorder',
            'text': '''Traveled to customer site at 123 Technology Drive, Building 5, San Jose, CA 95110.
Replaced faulty DIMM in ProLiant DL380 Gen10.
Customer contact: Mike Davis confirmed system stable.
Completed at 11:30 AM.'''
        },
        {
            'name': 'CaseComments (HIGH Risk)',
            'table': 'casecomment',
            'text': '''Customer john.doe@acme.com confirmed DIMM replacement successful.
Server IP 10.20.30.40 now responding.
Engineer EMP_45678 from john-smith-pc completed diagnostics.'''
        },
        {
            'name': 'Case (MEDIUM Risk)',
            'table': 'case',
            'text': '''ProLiant server experiencing memory errors. Customer reported issue.
Server MAC: 00:1A:2B:3C:4D:5E. Error code: iLO_400_MemoryErrors.
Resolution: Replaced faulty DIMM module.'''
        }
    ]

    remover = PIIRemover()

    for test_case in test_cases:
        print(f"Test: {test_case['name']}")
        print(f"Table: {test_case['table'].upper()}")
        print("-" * 70)

        print("Original:")
        print(test_case['text'])
        print()

        # Get PII report
        report = remover.get_pii_report(test_case['text'], test_case['table'])

        print(f"PII Detected: {report['total_pii_count']} instances")
        if report['pii_by_type']:
            print("  By Type:")
            for pii_type, count in report['pii_by_type'].items():
                print(f"    - {pii_type}: {count}")

        if report['pii_by_stage']:
            print("  By Stage:")
            for stage, count in report['pii_by_stage'].items():
                print(f"    - {stage}: {count}")

        print()

        # Clean text
        cleaned = remover.remove_pii(test_case['text'], test_case['table'])

        print("Cleaned:")
        print(cleaned)
        print()
        print("=" * 70)
        print()

    print("✓ 6-Stage PII Removal Test Complete")
    print()
    print("Notes:")
    print("  - Stage 4 (NER) and Stage 5 (Presidio) are stubbed (require spaCy/Presidio)")
    print("  - Stages 1, 2, 3, 6 are fully implemented and tested")
    print("  - Context-aware processing for EmailMessage and WorkOrder tables")


if __name__ == "__main__":
    main()
