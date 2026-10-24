HISSE ROBOTU — FUND PORTFOLIO AUTO-DISCOVERY & AUTO-INGESTION V1

Scope
- Official KAP disclosure-list discovery, only on explicit UI button press.
- Filters discovery against the known TEFAS/snapshot fund-code universe.
- Resolves KAP detail pages and portfolio-report PDF attachments automatically.
- Automatically unwraps transport-wrapped PDF payloads containing an embedded %PDF- stream.
- Reuses current fund-code / report-period / publication-date parser, append-only snapshot store and idempotency rules.
- Candidate-level failures are isolated and reported; one bad KAP report does not abort the entire scan.
- Manual PDF upload remains as fallback only.
- No startup network call.
- No AL/SAT mutation.
- No canonical ranking mutation.

Application contract
1. git apply --check
2. apply one Git patch
3. target tests
4. full backend regression
5. automatic rollback on test failure
