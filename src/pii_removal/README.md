# PII Removal Service

Multi-layer PII detection and removal pipeline.

## Components

- **detectors/**: PII detection engines
  - Regex patterns for common PII (emails, phones, IPs, serial numbers)
  - spaCy NER for entity recognition
  - Microsoft Presidio for advanced detection
- **processors/**: PII removal and masking logic
- **validators/**: PII leakage validation
- **rules/**: Custom PII detection rules

## Detection Layers

1. **Regex Layer**: Fast pattern matching for known formats
2. **NER Layer**: Named entity recognition using spaCy
3. **Presidio Layer**: Advanced context-aware PII detection
4. **Validation Layer**: Zero-leakage verification

## Performance Target

- 100% PII detection rate (zero leakage tolerance)
- Processing speed: ≥ 300 cases/minute
