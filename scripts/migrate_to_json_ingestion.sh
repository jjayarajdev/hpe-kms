#!/bin/bash

# KMS 2.5 - Migration Script
# Migrate from SFDC Extraction to JSON Ingestion

set -e

echo "=========================================="
echo "KMS 2.5 - Migration to JSON Ingestion"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PROJECT_ROOT="/Users/jjayaraj/workspaces/HPE/KMS"

cd "$PROJECT_ROOT"

echo -e "${BLUE}Step 1: Backing up old extraction module...${NC}"
if [ -d "src/pipeline/jobs/extraction" ]; then
    mkdir -p archive/migration_backup/$(date +%Y%m%d)
    cp -r src/pipeline/jobs/extraction archive/migration_backup/$(date +%Y%m%d)/
    echo -e "${GREEN}✓ Backup created in archive/migration_backup/${NC}"
else
    echo -e "${YELLOW}⚠ No extraction folder found (already migrated?)${NC}"
fi

echo ""
echo -e "${BLUE}Step 2: Removing old extraction module...${NC}"
if [ -d "src/pipeline/jobs/extraction" ]; then
    rm -rf src/pipeline/jobs/extraction
    echo -e "${GREEN}✓ Removed src/pipeline/jobs/extraction/${NC}"
else
    echo -e "${YELLOW}⚠ Extraction folder already removed${NC}"
fi

echo ""
echo -e "${BLUE}Step 3: Creating new ingestion module...${NC}"
mkdir -p src/pipeline/jobs/ingestion
touch src/pipeline/jobs/ingestion/__init__.py
echo -e "${GREEN}✓ Created src/pipeline/jobs/ingestion/${NC}"

echo ""
echo -e "${BLUE}Step 4: Creating data folders...${NC}"
mkdir -p data/raw/sfdc_exports/archive
mkdir -p data/processed/joined
mkdir -p data/processed/pii_clean
mkdir -p data/processed/ready_for_embedding
mkdir -p data/embeddings/issue_vectors
mkdir -p data/embeddings/resolution_vectors
echo -e "${GREEN}✓ Created data folder structure${NC}"

echo ""
echo -e "${BLUE}Step 5: Creating placeholder files...${NC}"
touch src/pipeline/jobs/ingestion/json_ingester.py
touch src/pipeline/jobs/ingestion/json_validator.py
echo -e "${GREEN}✓ Created ingestion module files${NC}"

echo ""
echo -e "${BLUE}Step 6: Creating utility scripts...${NC}"
touch scripts/prepare_sample_json.py
touch scripts/ingest_sfdc_json.py
touch scripts/validate_json_structure.py
touch scripts/archive_processed_files.py
chmod +x scripts/*.py
echo -e "${GREEN}✓ Created utility scripts${NC}"

echo ""
echo -e "${BLUE}Step 7: Updating .gitignore...${NC}"
cat >> .gitignore << 'EOF'

# SFDC JSON Exports
data/raw/sfdc_exports/*.json
data/raw/sfdc_exports/archive/**/*.json

# Processed data
data/processed/**/*.parquet
data/processed/**/*.csv

# Embeddings
data/embeddings/**/*.npy
data/embeddings/**/*.pkl
EOF
echo -e "${GREEN}✓ Updated .gitignore${NC}"

echo ""
echo -e "${BLUE}Step 8: Creating README for JSON ingestion...${NC}"
cat > data/raw/sfdc_exports/README.md << 'EOF'
# SFDC JSON Exports

Place your SFDC JSON exports in this directory.

## Expected Files

- `cases.json` - Case records
- `tasks.json` - Task records
- `workorders.json` - WorkOrder records
- `casecomments.json` - CaseComment records

## JSON Format

Files should be in SFDC export format:
```json
{
  "records": [
    {
      "Id": "500...",
      "Field1": "value1",
      ...
    }
  ],
  "totalSize": 1000,
  "done": true
}
```

Or simple array format:
```json
[
  {
    "Id": "500...",
    "Field1": "value1",
    ...
  }
]
```

## Processing

After placing JSON files here:
1. Run: `python scripts/ingest_sfdc_json.py`
2. Processed files will be moved to `archive/`
3. Data will be loaded into pipeline

## Archive

Processed files are automatically archived to:
`archive/YYYY-MM-DD/`
EOF
echo -e "${GREEN}✓ Created README${NC}"

echo ""
echo "=========================================="
echo -e "${GREEN}✓ Migration Complete!${NC}"
echo "=========================================="
echo ""
echo "Changes made:"
echo "  • Removed: src/pipeline/jobs/extraction/"
echo "  • Created: src/pipeline/jobs/ingestion/"
echo "  • Created: data/raw/sfdc_exports/"
echo "  • Created: utility scripts in scripts/"
echo "  • Updated: .gitignore"
echo ""
echo "Next steps:"
echo "  1. Place SFDC JSON files in data/raw/sfdc_exports/"
echo "  2. Implement json_ingester.py (see CORRECTED_NEXT_TASKS.md)"
echo "  3. Run: python scripts/prepare_sample_json.py"
echo "  4. Test ingestion pipeline"
echo ""
echo "Backup location:"
echo "  archive/migration_backup/$(date +%Y%m%d)/"
echo ""
