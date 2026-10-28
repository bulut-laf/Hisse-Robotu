# Fund Research Sprint 6 вЂ” Source-aware evidence ingestion

## Scope
- Adds field-level evidence validation, fund snapshot validation, CSV ingestion and an audit ledger.
- Does not perform network requests or fabricate real fund data.
- Every observation retains its source name, URL, source date and optional capture timestamp.
- Missing fields stay unknown; repeated observations are preserved rather than silently overwritten.
- A source-documentation status confirms required source metadata is present, not that the underlying source was independently audited.

## CSV format
Required columns: `isin,field_name,field_value,source_name,source_url,source_date`
Optional column: `captured_at`

## Target tests
`.\.venv\Scripts\python.exe -m pytest backend\tests\test_fund_research_sprint6.py -q`

## Full regression
`.\.venv\Scripts\python.exe -m pytest`