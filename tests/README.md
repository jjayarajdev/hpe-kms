# Tests

Comprehensive test suite for KMS 2.5 Vector Search.

## Test Structure

- **unit/**: Unit tests for individual components
  - pipeline/: Pipeline job tests
  - api/: API endpoint tests
  - pii_removal/: PII detection tests
- **integration/**: Integration tests for multi-component workflows
  - search/: Search functionality tests
  - embedding/: Embedding generation tests
  - reconciliation/: Data validation tests
- **e2e/**: End-to-end tests for complete user scenarios
  - scenarios/: User journey tests
  - fixtures/: Test data fixtures
- **performance/**: Performance and load tests

## Running Tests

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit

# Run with coverage
pytest --cov=src tests/

# Run performance tests
pytest tests/performance -v
```

## Test Data

Test datasets are located in `/data/test_datasets/` and include:
- DIMM failure scenarios
- Storage array failures
- Order processing queries
- False alarm cases
