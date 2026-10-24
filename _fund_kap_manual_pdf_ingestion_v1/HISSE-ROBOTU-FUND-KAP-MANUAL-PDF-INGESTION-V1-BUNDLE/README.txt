HISSE ROBOTU - FUND KAP MANUAL PDF INGESTION V1

Purpose
-------
Adds an explicit manual PDF upload path for real KAP Portfolio Allocation Report attachments.
KAP URL ingestion remains available but is optional.

Safety
------
- No automatic crawling.
- The actual portfolio attachment PDF is required.
- A PDF print/screenshot of the KAP notification page is rejected.
- Report year/month and publication date are explicit user inputs.
- Existing append-only snapshot store and change engine are reused.
- Same canonical KAP snapshot content is idempotent even if transport/source reference differs.
- No AL/SAT or canonical ranking mutation.

Verified against reconstructed exact current source
---------------------------------------------------
- git apply --check: PASS
- targeted tests: 20 passed
- changed Python AST parse: PASS

Apply
-----
Run APPLY-HISSE-ROBOTU-FUND-KAP-MANUAL-PDF-INGESTION-V1.ps1 from this folder.
