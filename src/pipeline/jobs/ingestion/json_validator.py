"""
JSON Validator for SFDC Exports

Validates JSON structure, required fields, and data quality
before ingestion into the pipeline.
"""

import json
import pandas as pd
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
import logging


class JSONValidator:
    """Validates SFDC JSON exports for data quality and structure"""

    # Expected fields for each table (KMS 2.6 - 6 tables)
    EXPECTED_FIELDS = {
        'case': {
            'required': {'Id', 'CaseNumber', 'Subject', 'Description', 'Status'},
            'optional': {
                'Priority', 'Type', 'Severity__c', 'Category__c', 'Sub_Category__c',
                'Reason', 'Product_Type__c', 'Environment__c', 'Root_Cause__c',
                'Issue__c', 'Resolution__c', 'AccountId', 'ContactId',
                'CreatedDate', 'ClosedDate', 'Product__c', 'Error_Codes__c',
                'Issue_Plain_Text__c', 'Cause_Plain_Text__c', 'GSD_Environment_Plain_Text__c',
                'Resolution_Code__c', 'Resolution_Plain_Text__c', 'Product_Line__c'
            }
        },
        'task': {
            'required': {'Type', 'Description', 'CaseId'},
            'optional': set()
        },
        'workorder': {
            'required': {'WorkOrderNumber', 'CaseId'},
            'optional': {'Subject', 'Description'}
        },
        'casecomment': {
            'required': {'CommentBody', 'ParentId'},
            'optional': set()
        },
        'workorderfeed': {
            'required': {'Type', 'Body', 'ParentId'},
            'optional': set()
        },
        'emailmessage': {
            'required': {'Subject', 'TextBody', 'ParentId'},
            'optional': set()
        }
    }

    # Valid values for specific fields
    VALID_VALUES = {
        'task_types': {'Plan of Action', 'Trouble Shooting'},
        'case_status': {'New', 'In Progress', 'Pending', 'Closed', 'Cancelled'},
        'case_priority': {'Low', 'Medium', 'High', 'Critical'}
    }

    def __init__(self):
        """Initialize JSON Validator"""
        self.logger = logging.getLogger(__name__)
        self.validation_errors = []
        self.validation_warnings = []

    def validate_json_structure(self, file_path: Path, table_name: str) -> Tuple[bool, List[str]]:
        """
        Validate JSON file structure

        Args:
            file_path: Path to JSON file
            table_name: Name of table (case, task, workorder, casecomment)

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        try:
            # Load JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check structure
            if isinstance(data, list):
                records = data
            elif isinstance(data, dict) and 'records' in data:
                records = data['records']
            else:
                errors.append(f"Invalid JSON structure in {file_path}. Expected array or {{records: [...]}} format")
                return False, errors

            # Check if empty
            if not records:
                errors.append(f"No records found in {file_path}")
                return False, errors

            # Validate fields
            if table_name in self.EXPECTED_FIELDS:
                is_valid, field_errors = self._validate_fields(records, table_name)
                errors.extend(field_errors)

            return len(errors) == 0, errors

        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON in {file_path}: {e}")
            return False, errors
        except Exception as e:
            errors.append(f"Error validating {file_path}: {e}")
            return False, errors

    def _validate_fields(self, records: List[Dict], table_name: str) -> Tuple[bool, List[str]]:
        """
        Validate fields in records

        Args:
            records: List of record dictionaries
            table_name: Name of table

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        expected = self.EXPECTED_FIELDS.get(table_name, {})
        required_fields = expected.get('required', set())

        # Check first record for required fields
        if records:
            first_record = records[0]
            record_fields = set(first_record.keys())

            # Check for missing required fields
            missing_fields = required_fields - record_fields
            if missing_fields:
                errors.append(
                    f"{table_name}: Missing required fields: {missing_fields}"
                )

            # Check all records for required fields
            for idx, record in enumerate(records):
                record_fields = set(record.keys())
                missing_in_record = required_fields - record_fields

                if missing_in_record:
                    errors.append(
                        f"{table_name} record {idx}: Missing required fields: {missing_in_record}"
                    )

        return len(errors) == 0, errors

    def validate_data_quality(self, df: pd.DataFrame, table_name: str) -> Tuple[bool, List[str], List[str]]:
        """
        Validate data quality in DataFrame

        Args:
            df: DataFrame to validate
            table_name: Name of table

        Returns:
            Tuple of (is_valid, error_messages, warning_messages)
        """
        errors = []
        warnings = []

        if df.empty:
            errors.append(f"{table_name}: DataFrame is empty")
            return False, errors, warnings

        expected = self.EXPECTED_FIELDS.get(table_name, {})
        required_fields = expected.get('required', set())

        # Check for null values in required fields
        for field in required_fields:
            if field in df.columns:
                null_count = df[field].isnull().sum()
                if null_count > 0:
                    errors.append(
                        f"{table_name}: {null_count} null values in required field '{field}'"
                    )

        # Table-specific validations
        if table_name == 'case':
            # Check for duplicate Case IDs
            if 'Id' in df.columns:
                duplicate_ids = df[df['Id'].duplicated()]['Id'].tolist()
                if duplicate_ids:
                    errors.append(f"case: Duplicate Case IDs found: {duplicate_ids}")

            # Check Status values
            if 'Status' in df.columns:
                invalid_status = df[~df['Status'].isin(self.VALID_VALUES['case_status'])]['Status'].unique()
                if len(invalid_status) > 0:
                    warnings.append(
                        f"case: Unexpected Status values: {invalid_status.tolist()}"
                    )

            # Check Priority values
            if 'Priority' in df.columns:
                invalid_priority = df[
                    (df['Priority'].notna()) &
                    (~df['Priority'].isin(self.VALID_VALUES['case_priority']))
                ]['Priority'].unique()
                if len(invalid_priority) > 0:
                    warnings.append(
                        f"case: Unexpected Priority values: {invalid_priority.tolist()}"
                    )

        elif table_name == 'task':
            # Check Task Type values
            if 'Type' in df.columns:
                invalid_types = df[~df['Type'].isin(self.VALID_VALUES['task_types'])]['Type'].unique()
                if len(invalid_types) > 0:
                    warnings.append(
                        f"task: Tasks with unexpected Type values will be filtered: {invalid_types.tolist()}"
                    )

            # Check for orphaned tasks (no CaseId match)
            if 'CaseId' in df.columns:
                null_case_ids = df['CaseId'].isnull().sum()
                if null_case_ids > 0:
                    errors.append(f"task: {null_case_ids} tasks with null CaseId")

        elif table_name == 'workorder':
            # Check for orphaned workorders
            if 'CaseId' in df.columns:
                null_case_ids = df['CaseId'].isnull().sum()
                if null_case_ids > 0:
                    errors.append(f"workorder: {null_case_ids} workorders with null CaseId")

        elif table_name == 'casecomment':
            # Check for orphaned comments
            if 'ParentId' in df.columns:
                null_parent_ids = df['ParentId'].isnull().sum()
                if null_parent_ids > 0:
                    errors.append(f"casecomment: {null_parent_ids} comments with null ParentId")

        elif table_name == 'workorderfeed':
            # Check for orphaned work order feeds
            if 'ParentId' in df.columns:
                null_parent_ids = df['ParentId'].isnull().sum()
                if null_parent_ids > 0:
                    errors.append(f"workorderfeed: {null_parent_ids} feeds with null ParentId")

            # Check for empty Body
            if 'Body' in df.columns:
                null_body = df['Body'].isnull().sum()
                if null_body > 0:
                    warnings.append(f"workorderfeed: {null_body} feeds with null Body")

        elif table_name == 'emailmessage':
            # Check for orphaned email messages
            if 'ParentId' in df.columns:
                null_parent_ids = df['ParentId'].isnull().sum()
                if null_parent_ids > 0:
                    errors.append(f"emailmessage: {null_parent_ids} emails with null ParentId")

            # Check for empty TextBody
            if 'TextBody' in df.columns:
                null_body = df['TextBody'].isnull().sum()
                if null_body > 0:
                    warnings.append(f"emailmessage: {null_body} emails with null TextBody")

        return len(errors) == 0, errors, warnings

    def validate_all_files(self, json_dir: Path) -> Dict[str, Dict]:
        """
        Validate all JSON files in directory

        Args:
            json_dir: Directory containing JSON files

        Returns:
            Dictionary with validation results for each file
        """
        results = {}

        files = {
            'case': json_dir / 'cases.json',
            'task': json_dir / 'tasks.json',
            'workorder': json_dir / 'workorders.json',
            'casecomment': json_dir / 'casecomments.json',
            'workorderfeed': json_dir / 'workorderfeeds.json',
            'emailmessage': json_dir / 'emailmessages.json'
        }

        for table_name, file_path in files.items():
            self.logger.info(f"Validating {table_name}: {file_path}")

            if not file_path.exists():
                results[table_name] = {
                    'valid': False,
                    'errors': [f"File not found: {file_path}"],
                    'warnings': []
                }
                continue

            # Validate structure
            is_valid, errors = self.validate_json_structure(file_path, table_name)

            if is_valid:
                # Load and validate data quality
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    records = data['records'] if 'records' in data else data
                    df = pd.DataFrame(records)

                    is_valid, data_errors, warnings = self.validate_data_quality(df, table_name)
                    errors.extend(data_errors)
                except Exception as e:
                    is_valid = False
                    errors.append(f"Error loading data: {e}")
                    warnings = []
            else:
                warnings = []

            results[table_name] = {
                'valid': is_valid,
                'errors': errors,
                'warnings': warnings if is_valid else []
            }

        return results

    def print_validation_report(self, results: Dict[str, Dict]) -> bool:
        """
        Print validation report

        Args:
            results: Validation results from validate_all_files()

        Returns:
            True if all valid, False otherwise
        """
        print("\n" + "=" * 60)
        print("JSON Validation Report")
        print("=" * 60)

        all_valid = True

        for table_name, result in results.items():
            status = " PASS" if result['valid'] else " FAIL"
            print(f"\n{table_name.upper()}: {status}")

            if result['errors']:
                print("  Errors:")
                for error in result['errors']:
                    print(f"    - {error}")
                all_valid = False

            if result['warnings']:
                print("  Warnings:")
                for warning in result['warnings']:
                    print(f"    - {warning}")

        print("\n" + "=" * 60)
        if all_valid:
            print(" All validations passed!")
        else:
            print(" Validation failed - please fix errors before ingestion")
        print("=" * 60 + "\n")

        return all_valid


def main():
    """Test JSON validation"""

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    validator = JSONValidator()

    # Validate all files
    json_dir = Path("data/raw/sfdc_exports")

    if not json_dir.exists():
        print(f"ERROR: Directory not found: {json_dir}")
        print("Please run 'python scripts/prepare_sample_json.py' first")
        return 1

    results = validator.validate_all_files(json_dir)
    all_valid = validator.print_validation_report(results)

    return 0 if all_valid else 1


if __name__ == "__main__":
    exit(main())
