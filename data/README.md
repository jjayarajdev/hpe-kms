# Data

Data storage for KMS 2.5 Vector Search project.

## Structure

- **raw/**: Raw data from SFDC tables
  - vw_de_sfdc_case_snapshot
  - vw_de_sfdc_task_snapshot
  - vw_de_sfdc_workorder_snapshot
  - vw_de_sfdc_casecomment_snapshot
- **processed/**: Processed and cleaned data
  - After PII removal
  - After multi-table joins
  - Ready for embedding
- **embeddings/**: Generated vector embeddings
  - Issue vectors (3,072 dimensions)
  - Resolution vectors (3,072 dimensions)
- **test_datasets/**: Test data for validation
  - See case-fields-mapping.json for test scenarios

## Data Volumes

- Historical cases: 1M+ records
- Daily incremental: ~5,000 cases
- Storage requirement: ~500GB (raw + processed + embeddings)

## Data Pipeline

1. Extract from SFDC tables → raw/
2. Clean and join → processed/
3. Remove PII → processed/pii_clean/
4. Generate embeddings → embeddings/
5. Load to Weaviate vector database

## Test Datasets

Located in `case-fields-mapping.json`:
- test_dataset_1: DIMM Failure Hardware Issue
- test_dataset_2: Storage Array Tape Drive Failure
- test_dataset_3: HDD Failure with Storage Degradation
- test_dataset_4: 3PAR Storage False Alarm
- test_dataset_5: Order Processing Query
