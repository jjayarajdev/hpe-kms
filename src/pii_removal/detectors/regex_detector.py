"""
Regex-based PII Detector

Detects PII using regular expression patterns:
- Email addresses
- Phone numbers (multiple formats)
- IP addresses (IPv4/IPv6)
- Serial numbers (HPE format)
- Credit card numbers
- Social security numbers

Task Reference: Phase 2, Task 2.3
"""

import re
from typing import List, Dict, Tuple
import logging


class RegexPIIDetector:
    """Detects PII using regex patterns"""

    # Regex patterns for common PII types
    PATTERNS = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        'ipv4': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
        'ipv6': r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b',
        'serial_number': r'\b[A-Z]{2}[0-9]{2}[A-Z0-9]{6}\b',  # HPE serial format
        'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
    }

    def __init__(self):
        """Initialize Regex PII Detector"""
        self.logger = logging.getLogger(__name__)
        self.compiled_patterns = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.PATTERNS.items()
        }

    def detect(self, text: str) -> List[Dict[str, any]]:
        """
        Detect PII in text using regex patterns

        Args:
            text: Input text to scan

        Returns:
            List of detected PII with type, value, and position
            Example:
            [
                {
                    'type': 'email',
                    'value': 'user@example.com',
                    'start': 10,
                    'end': 27
                }
            ]
        """
        if not text:
            return []

        detections = []

        for pii_type, pattern in self.compiled_patterns.items():
            for match in pattern.finditer(text):
                detections.append({
                    'type': pii_type,
                    'value': match.group(),
                    'start': match.start(),
                    'end': match.end()
                })

        self.logger.debug(f"Detected {len(detections)} PII items using regex")
        return detections

    def detect_batch(self, texts: List[str]) -> List[List[Dict[str, any]]]:
        """
        Detect PII in batch of texts

        Args:
            texts: List of input texts

        Returns:
            List of detection results for each text
        """
        return [self.detect(text) for text in texts]

    def has_pii(self, text: str) -> bool:
        """
        Quick check if text contains any PII

        Args:
            text: Input text

        Returns:
            True if PII detected, False otherwise
        """
        return len(self.detect(text)) > 0


def main():
    """Test regex detector with sample data"""
    detector = RegexPIIDetector()

    # Test cases from case-fields-mapping.json examples
    test_texts = [
        "Contact me at john.doe@hpe.com or call 555-123-4567",
        "Server IP: 10.20.30.40 Serial: CZ34278RY2",
        "Customer SSN: 123-45-6789 Credit Card: 4532-1234-5678-9010"
    ]

    for text in test_texts:
        detections = detector.detect(text)
        print(f"Text: {text}")
        print(f"Detections: {detections}\n")


if __name__ == "__main__":
    main()
