"""
JSON Ingestion from SFDC Exports (KMS 2.6)

Reads JSON files exported from SFDC and loads into pipeline.
NOT extracting from SFDC database directly.

KMS 2.6 Specification:
- 6 Tables: Case, Task, WorkOrder, CaseComments, WorkOrderFeed, EmailMessage
- 44 Total Fields across all tables
- Single composite vector per case

Input: JSON files from SFDC
Output: Pandas DataFrames for processing
"""

import json
import pandas as pd
from typing import List, Dict, Optional
import logging
from pathlib import Path


class JSONIngester:
    """Ingests JSON data from SFDC exports"""

    def __init__(self, json_dir: str = "data/raw/sfdc_exports"):
        """
        Initialize JSON Ingester

        Args:
            json_dir: Directory containing SFDC JSON exports
        """
        self.json_dir = Path(json_dir)
        self.logger = logging.getLogger(__name__)

        # Ensure directory exists
        if not self.json_dir.exists():
            raise ValueError(f"JSON directory does not exist: {self.json_dir}")

    def _load_json_file(self, file_path: Path) -> List[Dict]:
        """
        Load JSON file and extract records

        Handles both formats:
        1. Simple array: [{"Id": "...", ...}, ...]
        2. SFDC format: {"records": [...], "totalSize": N, "done": true}

        Args:
            file_path: Path to JSON file

        Returns:
            List of records
        """
        self.logger.info(f"Loading JSON from {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extract records based on format
        if isinstance(data, list):
            # Simple array format
            records = data
        elif isinstance(data, dict) and 'records' in data:
            # SFDC export format
            records = data['records']
        elif isinstance(data, dict):
            # Single record
            records = [data]
        else:
            raise ValueError(f"Unexpected JSON format in {file_path}")

        self.logger.info(f"Loaded {len(records)} records from {file_path}")
        return records

    def load_case_json(self, file_path: Optional[str] = None) -> pd.DataFrame:
        """
        Load Case data from JSON export

        Expected fields (21 fields per KMS 2.6):
        - CaseNumber, Id, AccountId, Status, Priority, Product__c, Category__c
        - CreatedDate, ClosedDate, Subject, Description, Resolution__c
        - Error_Codes__c, Issue_Plain_Text__c, Cause_Plain_Text__c
        - GSD_Environment_Plain_Text__c, Resolution_Code__c, Resolution_Plain_Text__c
        - Product_Type__c, Product_Line__c, Root_Cause__c

        Args:
            file_path: Path to Case JSON file (default: json_dir/cases.json)

        Returns:
            DataFrame with Case records
        """
        if file_path is None:
            file_path = self.json_dir / "cases.json"
        else:
            file_path = Path(file_path)

        records = self._load_json_file(file_path)
        df = pd.DataFrame(records)

        self.logger.info(f"Loaded {len(df)} Case records with {len(df.columns)} columns")
        return df

    def load_task_json(self, file_path: Optional[str] = None) -> pd.DataFrame:
        """
        Load Task data from JSON export

        Expected fields (2 fields):
        - Type, Description

        Filter: Only Type IN ('Plan of Action', 'Trouble Shooting')

        Args:
            file_path: Path to Task JSON file (default: json_dir/tasks.json)

        Returns:
            DataFrame with Task records (filtered)
        """
        if file_path is None:
            file_path = self.json_dir / "tasks.json"
        else:
            file_path = Path(file_path)

        records = self._load_json_file(file_path)
        df = pd.DataFrame(records)

        # Filter by Type
        if 'Type' in df.columns:
            df = df[df['Type'].isin(['Plan of Action', 'Trouble Shooting'])]
            self.logger.info(f"Filtered to {len(df)} Task records (Plan of Action + Trouble Shooting)")
        else:
            self.logger.warning("Type column not found in Task data - no filtering applied")

        return df

    def load_workorder_json(self, file_path: Optional[str] = None) -> pd.DataFrame:
        """
        Load WorkOrder data from JSON export

        Expected fields (3 fields):
        - Subject, Description, WorkOrderNumber

        Args:
            file_path: Path to WorkOrder JSON file (default: json_dir/workorders.json)

        Returns:
            DataFrame with WorkOrder records
        """
        if file_path is None:
            file_path = self.json_dir / "workorders.json"
        else:
            file_path = Path(file_path)

        records = self._load_json_file(file_path)
        df = pd.DataFrame(records)

        self.logger.info(f"Loaded {len(df)} WorkOrder records")
        return df

    def load_casecomment_json(self, file_path: Optional[str] = None) -> pd.DataFrame:
        """
        Load CaseComment data from JSON export

        Expected fields (1 field):
        - CommentBody

        Args:
            file_path: Path to CaseComment JSON file (default: json_dir/casecomments.json)

        Returns:
            DataFrame with CaseComment records
        """
        if file_path is None:
            file_path = self.json_dir / "casecomments.json"
        else:
            file_path = Path(file_path)

        records = self._load_json_file(file_path)
        df = pd.DataFrame(records)

        self.logger.info(f"Loaded {len(df)} CaseComment records")
        return df

    def load_workorderfeed_json(self, file_path: Optional[str] = None) -> pd.DataFrame:
        """
        Load WorkOrderFeed data from JSON export (KMS 2.6)

        Expected fields (2 fields):
        - Type: Feed type (e.g., CallUpdate, ServiceNote)
        - Body: Feed content/service notes

        Args:
            file_path: Path to WorkOrderFeed JSON file (default: json_dir/workorderfeeds.json)

        Returns:
            DataFrame with WorkOrderFeed records
        """
        if file_path is None:
            file_path = self.json_dir / "workorderfeeds.json"
        else:
            file_path = Path(file_path)

        records = self._load_json_file(file_path)
        df = pd.DataFrame(records)

        self.logger.info(f"Loaded {len(df)} WorkOrderFeed records")
        return df

    def load_emailmessage_json(self, file_path: Optional[str] = None) -> pd.DataFrame:
        """
        Load EmailMessage data from JSON export (KMS 2.6)

        Expected fields (2 fields):
        - Subject: Email subject line
        - TextBody: Email body content

        Args:
            file_path: Path to EmailMessage JSON file (default: json_dir/emailmessages.json)

        Returns:
            DataFrame with EmailMessage records
        """
        if file_path is None:
            file_path = self.json_dir / "emailmessages.json"
        else:
            file_path = Path(file_path)

        records = self._load_json_file(file_path)
        df = pd.DataFrame(records)

        self.logger.info(f"Loaded {len(df)} EmailMessage records")
        return df

    def load_all_tables(
        self,
        case_file: Optional[str] = None,
        task_file: Optional[str] = None,
        workorder_file: Optional[str] = None,
        casecomment_file: Optional[str] = None,
        workorderfeed_file: Optional[str] = None,
        emailmessage_file: Optional[str] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Load all 6 tables from JSON files (KMS 2.6)

        Args:
            case_file: Case JSON file path (default: json_dir/cases.json)
            task_file: Task JSON file path (default: json_dir/tasks.json)
            workorder_file: WorkOrder JSON file path (default: json_dir/workorders.json)
            casecomment_file: CaseComment JSON file path (default: json_dir/casecomments.json)
            workorderfeed_file: WorkOrderFeed JSON file path (default: json_dir/workorderfeeds.json)
            emailmessage_file: EmailMessage JSON file path (default: json_dir/emailmessages.json)

        Returns:
            Dictionary with table names as keys and DataFrames as values
        """
        self.logger.info("Loading all SFDC tables from JSON files (KMS 2.6 - 6 tables)...")

        tables = {
            'case': self.load_case_json(case_file),
            'task': self.load_task_json(task_file),
            'workorder': self.load_workorder_json(workorder_file),
            'casecomment': self.load_casecomment_json(casecomment_file),
            'workorderfeed': self.load_workorderfeed_json(workorderfeed_file),
            'emailmessage': self.load_emailmessage_json(emailmessage_file)
        }

        # Log summary
        self.logger.info("=" * 60)
        self.logger.info("JSON Ingestion Summary (KMS 2.6):")
        for table_name, df in tables.items():
            self.logger.info(f"  {table_name.upper()}: {len(df)} records, {len(df.columns)} columns")
        self.logger.info("=" * 60)

        return tables


def main():
    """Test JSON ingestion with sample files"""

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger = logging.getLogger(__name__)

    try:
        # Initialize ingester
        ingester = JSONIngester()

        # Check if JSON files exist
        json_dir = Path("data/raw/sfdc_exports")
        required_files = [
            "cases.json", "tasks.json", "workorders.json",
            "casecomments.json", "workorderfeeds.json", "emailmessages.json"
        ]

        missing_files = [f for f in required_files if not (json_dir / f).exists()]

        if missing_files:
            logger.warning(f"Missing JSON files: {missing_files}")
            logger.info("Please run 'python scripts/prepare_sample_json.py' to create sample files")
            return

        # Load all tables
        tables = ingester.load_all_tables()

        # Display sample data
        print("\n" + "=" * 60)
        print("Sample Data from Each Table:")
        print("=" * 60)

        for table_name, df in tables.items():
            print(f"\n{table_name.upper()} Table:")
            print(f"  Records: {len(df)}")
            print(f"  Columns: {list(df.columns)}")

            if len(df) > 0:
                print(f"\n  First record:")
                for col, val in df.iloc[0].items():
                    if pd.notna(val):
                        val_str = str(val)[:60] + "..." if len(str(val)) > 60 else str(val)
                        print(f"    {col}: {val_str}")

        print("\n" + "=" * 60)
        print(" JSON Ingestion Test Complete!")
        print("=" * 60)

    except Exception as e:
        logger.error(f"Error during JSON ingestion: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
