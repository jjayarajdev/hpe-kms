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
