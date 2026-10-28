# Fund Research Sprint 7 вЂ” Erste Market source connector

## Scope
- Adds a network connector for a public Erste Market fund-comparison page, with timeout and injectable opener for tests.
- Records requested URL, source name, retrieval timestamp, HTTP status, content type, title, visible text and fetch status.
- Builds an ISIN-specific comparison URL.
- Supports field-level evidence records only when a source date is explicitly supplied.
- Failed, empty or non-2xx responses remain `not_verified`.
- This connector extracts visible page text; it does not yet map every page field into normalized NAV/return/fee fields. Do not treat page retrieval as verified fund facts.
- No trades or investment recommendations are produced.

## Official source
Erste Market public fund comparison page:
https://www.erstemarket.hu/befektetesi_alapok/osszehasonlitas

## Target tests
`.\.venv\Scripts\python.exe -m pytest backend\tests\test_fund_research_sprint7.py -q`

## Full regression
`.\.venv\Scripts\python.exe -m pytest`