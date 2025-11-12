# KMS 2.5 - Corrected Next Tasks

## ✅ Correction: Data Source

**IMPORTANT**: You are **receiving JSON data from SFDC**, NOT extracting directly from SFDC database.

The actual data flow:
```
SFDC → JSON Export → Your Pipeline → Weaviate
```

NOT:
```
SFDC Database → PySpark Extract → Your Pipeline
```

---

## 🎯 Revised Immediate Next Tasks

### **Priority 1: Get the System Running with JSON Input**

#### Task 1.1: Start Local Infrastructure ⚡ **START HERE**
```bash
cd /Users/jjayaraj/workspaces/HPE/KMS
./scripts/setup_local.sh
```

**Verify:**
- ✅ All services running
- ✅ Can login and get JWT token
- ✅ Weaviate accessible at http://localhost:8080

**Time:** 15 minutes

---

#### Task 1.2: Create JSON Ingestion Script 📥
**NEW FILE:** `src/pipeline/jobs/ingestion/json_ingester.py`

**Purpose:** Read SFDC JSON exports and prepare for processing

```python
"""
JSON Ingestion from SFDC Exports

Reads JSON files exported from SFDC and loads into pipeline.
NOT extracting from SFDC database directly.

Input: JSON files from SFDC
Output: Pandas/PySpark DataFrame for processing
"""

import json
import pandas as pd
from typing import List, Dict
import logging


class JSONIngester:
    """Ingests JSON data from SFDC exports"""

    def __init__(self, json_dir: str = "data/raw/sfdc_exports"):
        """
        Initialize JSON Ingester

        Args:
            json_dir: Directory containing SFDC JSON exports
        """
        self.json_dir = json_dir
        self.logger = logging.getLogger(__name__)

    def load_case_json(self, file_path: str) -> pd.DataFrame:
        """
        Load Case data from JSON export

        Args:
            file_path: Path to Case JSON file

        Returns:
            DataFrame with Case records
        """
        self.logger.info(f"Loading Case data from {file_path}")

        with open(file_path, 'r') as f:
            data = json.load(f)

        # Convert to DataFrame
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict) and 'records' in data:
            # SFDC often exports as {"records": [...]}
            df = pd.DataFrame(data['records'])
        else:
            df = pd.DataFrame([data])

        self.logger.info(f"Loaded {len(df)} Case records")
        return df

    def load_task_json(self, file_path: str) -> pd.DataFrame:
        """Load Task data from JSON export"""
        self.logger.info(f"Loading Task data from {file_path}")

        with open(file_path, 'r') as f:
            data = json.load(f)

        df = pd.DataFrame(data['records'] if 'records' in data else data)
        self.logger.info(f"Loaded {len(df)} Task records")
        return df

    def load_workorder_json(self, file_path: str) -> pd.DataFrame:
        """Load WorkOrder data from JSON export"""
        self.logger.info(f"Loading WorkOrder data from {file_path}")

        with open(file_path, 'r') as f:
            data = json.load(f)

        df = pd.DataFrame(data['records'] if 'records' in data else data)
        self.logger.info(f"Loaded {len(df)} WorkOrder records")
        return df

    def load_casecomment_json(self, file_path: str) -> pd.DataFrame:
        """Load CaseComment data from JSON export"""
        self.logger.info(f"Loading CaseComment data from {file_path}")

        with open(file_path, 'r') as f:
            data = json.load(f)

        df = pd.DataFrame(data['records'] if 'records' in data else data)
        self.logger.info(f"Loaded {len(df)} CaseComment records")
        return df

    def load_all_tables(
        self,
        case_file: str,
        task_file: str,
        workorder_file: str,
        casecomment_file: str
    ) -> Dict[str, pd.DataFrame]:
        """
        Load all 4 tables from JSON files

        Args:
            case_file: Case JSON file path
            task_file: Task JSON file path
            workorder_file: WorkOrder JSON file path
            casecomment_file: CaseComment JSON file path

        Returns:
            Dictionary with table names as keys
        """
        return {
            'case': self.load_case_json(case_file),
            'task': self.load_task_json(task_file),
            'workorder': self.load_workorder_json(workorder_file),
            'casecomment': self.load_casecomment_json(casecomment_file)
        }


def main():
    """Test JSON ingestion with sample files"""
    ingester = JSONIngester()

    # Test with case-fields-mapping.json as sample
    sample_file = "data/case-fields-mapping.json"

    with open(sample_file, 'r') as f:
        test_data = json.load(f)

    print(f"Loaded test data with {len(test_data)} datasets")

    # TODO: Load actual SFDC JSON exports
    # tables = ingester.load_all_tables(
    #     case_file="data/raw/sfdc_exports/cases.json",
    #     task_file="data/raw/sfdc_exports/tasks.json",
    #     workorder_file="data/raw/sfdc_exports/workorders.json",
    #     casecomment_file="data/raw/sfdc_exports/casecomments.json"
    # )


if __name__ == "__main__":
    main()
```

**Time:** 2 hours
**Deliverable:** Script to read SFDC JSON exports

---

#### Task 1.3: Prepare Sample JSON Files 📝
**Goal:** Create sample JSON files from test data

**Script:** `scripts/prepare_sample_json.py`

```python
"""
Prepare Sample JSON Files from Test Data

Converts data/case-fields-mapping.json into separate JSON files
that simulate SFDC exports for the 4 tables.
"""

import json
from collections import defaultdict

# Load test data
with open('data/case-fields-mapping.json', 'r') as f:
    test_data = json.load(f)

# Initialize tables
tables = {
    'case': [],
    'task': [],
    'workorder': [],
    'casecomment': []
}

# Process each test dataset
for dataset_name, dataset in test_data.items():
    # Extract fields by source table
    case_record = {}
    task_records = []
    workorder_records = []
    casecomment_records = []

    for source in dataset['data_mapping']['sources']:
        table = source['source_table'].lower()
        field = source['source_field']
        value = source['comment_example']

        if table == 'case':
            case_record[field] = value
        elif table == 'task':
            # Tasks can have multiple records per case
            task_records.append({
                'Type': source.get('Type', 'Plan of Action'),
                field: value,
                'CaseId': case_record.get('Id', f'CASE_{dataset_name}')
            })
        elif table == 'workorder':
            workorder_records.append({
                field: value,
                'CaseId': case_record.get('Id', f'CASE_{dataset_name}')
            })
        elif table == 'casecomments':
            casecomment_records.append({
                field: value,
                'ParentId': case_record.get('Id', f'CASE_{dataset_name}')
            })

    # Add to tables
    if case_record:
        tables['case'].append(case_record)
    tables['task'].extend(task_records)
    tables['workorder'].extend(workorder_records)
    tables['casecomment'].extend(casecomment_records)

# Save as separate JSON files (simulating SFDC exports)
import os
os.makedirs('data/raw/sfdc_exports', exist_ok=True)

for table_name, records in tables.items():
    output = {
        'records': records,
        'totalSize': len(records)
    }

    with open(f'data/raw/sfdc_exports/{table_name}s.json', 'w') as f:
        json.dump(output, f, indent=2)

    print(f"✓ Created {table_name}s.json with {len(records)} records")

print(f"\n✓ Sample JSON files ready in data/raw/sfdc_exports/")
```

**Run:**
```bash
python scripts/prepare_sample_json.py
```

**Time:** 1 hour
**Deliverable:** 4 JSON files simulating SFDC exports

---

#### Task 1.4: Update SFDC Extractor → JSON Loader 🔄
**UPDATE FILE:** `src/pipeline/jobs/extraction/sfdc_extractor.py`

**Change the class name and purpose:**

```python
"""
SFDC JSON Loader (NOT Database Extractor)

Loads data from SFDC JSON exports (not direct database connection).

Input: JSON files from SFDC
Output: DataFrames for transformation pipeline
"""

from typing import Dict
import pandas as pd
import logging


class SFDCJSONLoader:
    """Loads SFDC data from JSON exports"""

    def __init__(self, json_dir: str = "data/raw/sfdc_exports"):
        """
        Initialize SFDC JSON Loader

        Args:
            json_dir: Directory containing SFDC JSON exports
        """
        self.json_dir = json_dir
        self.logger = logging.getLogger(__name__)

    def load_case_data(self) -> pd.DataFrame:
        """Load Case data from JSON"""
        import json

        file_path = f"{self.json_dir}/cases.json"
        self.logger.info(f"Loading Case data from {file_path}")

        with open(file_path, 'r') as f:
            data = json.load(f)

        df = pd.DataFrame(data['records'])
        self.logger.info(f"Loaded {len(df)} Case records")
        return df

    def load_task_data(self) -> pd.DataFrame:
        """Load Task data from JSON"""
        import json

        file_path = f"{self.json_dir}/tasks.json"
        self.logger.info(f"Loading Task data from {file_path}")

        with open(file_path, 'r') as f:
            data = json.load(f)

        df = pd.DataFrame(data['records'])

        # Filter: Only Plan of Action and Trouble Shooting
        df = df[df['Type'].isin(['Plan of Action', 'Trouble Shooting'])]

        self.logger.info(f"Loaded {len(df)} Task records")
        return df

    def load_workorder_data(self) -> pd.DataFrame:
        """Load WorkOrder data from JSON"""
        import json

        file_path = f"{self.json_dir}/workorders.json"
        with open(file_path, 'r') as f:
            data = json.load(f)

        df = pd.DataFrame(data['records'])
        self.logger.info(f"Loaded {len(df)} WorkOrder records")
        return df

    def load_casecomment_data(self) -> pd.DataFrame:
        """Load CaseComment data from JSON"""
        import json

        file_path = f"{self.json_dir}/casecomments.json"
        with open(file_path, 'r') as f:
            data = json.load(f)

        df = pd.DataFrame(data['records'])
        self.logger.info(f"Loaded {len(df)} CaseComment records")
        return df

    def load_all(self) -> Dict[str, pd.DataFrame]:
        """Load all 4 tables from JSON files"""
        return {
            'case': self.load_case_data(),
            'task': self.load_task_data(),
            'workorder': self.load_workorder_data(),
            'casecomment': self.load_casecomment_data()
        }


def main():
    """Test JSON loading"""
    loader = SFDCJSONLoader()
    tables = loader.load_all()

    for table_name, df in tables.items():
        print(f"\n{table_name.upper()} Table:")
        print(f"  Records: {len(df)}")
        print(f"  Columns: {list(df.columns)}")


if __name__ == "__main__":
    main()
```

**Time:** 1 hour
**Deliverable:** Updated loader for JSON input

---

## 📋 Revised Week 1 Tasks

### Day 1: Setup & JSON Preparation
1. ✅ Run `./scripts/setup_local.sh`
2. ✅ Create `scripts/prepare_sample_json.py`
3. ✅ Run script to generate sample JSON files
4. ✅ Verify JSON files in `data/raw/sfdc_exports/`

### Day 2: JSON Ingestion
1. ✅ Create `src/pipeline/jobs/ingestion/json_ingester.py`
2. ✅ Update `src/pipeline/jobs/extraction/sfdc_extractor.py` → `sfdc_json_loader.py`
3. ✅ Test JSON loading with sample files

### Day 3: Weaviate & Search
1. ✅ Complete Weaviate schema (Task 1.2 from original)
2. ✅ Load test data from JSON into Weaviate
3. ✅ Implement basic search

---

## 🔄 Updated Data Pipeline Flow

### Correct Flow:
```
1. Receive SFDC JSON exports
   ↓
2. JSON Ingester (read JSON files)
   ↓
3. Multi-Table Transformer (join 4 tables)
   ↓
4. PII Removal
   ↓
5. Text Concatenation (Issue + Resolution)
   ↓
6. Embedding Generation (separate Issue & Resolution vectors)
   ↓
7. Load to Weaviate
```

### File Locations:
```
data/raw/sfdc_exports/
├── cases.json          ← Receive from SFDC
├── tasks.json          ← Receive from SFDC
├── workorders.json     ← Receive from SFDC
└── casecomments.json   ← Receive from SFDC

↓ Process with

src/pipeline/jobs/ingestion/json_ingester.py       ← NEW
src/pipeline/jobs/transformation/multi_table_joiner.py
src/pii_removal/processors/pii_remover.py
src/pipeline/jobs/embedding/embedding_generator.py
src/pipeline/jobs/loading/weaviate_loader.py
```

---

## ❓ Questions to Clarify

1. **JSON Format**: What format do you receive from SFDC?
   - Single file with all tables?
   - Separate files per table?
   - Nested JSON structure?

2. **Update Frequency**: How often do you receive new JSON exports?
   - Daily?
   - Weekly?
   - On-demand?

3. **Data Volume**: What's the typical size of JSON exports?
   - Number of cases per file?
   - File size?

4. **Sample Data**: Do you have actual SFDC JSON samples I can work with?

---

## ✅ What to Do RIGHT NOW

1. **Run setup:**
   ```bash
   ./scripts/setup_local.sh
   ```

2. **Create sample JSON files:**
   ```bash
   python scripts/prepare_sample_json.py
   ```

3. **Check output:**
   ```bash
   ls -lh data/raw/sfdc_exports/
   cat data/raw/sfdc_exports/cases.json | jq
   ```

4. **Then we can proceed** with loading JSON → processing → Weaviate

---

**Ready to start?** Let me know the format of your SFDC JSON exports, and I'll adjust the ingestion code accordingly! 🚀
