HISSE ROBOTU - KAP FUND CODE PARSER ROBUSTNESS V1

Problem:
Some real KAP portfolio PDFs extract the value of "A. FONUN ADI" out of visual order.
AP5 June 2026 extracts "A. FONUN ADI :" blank while AP5 is visible in the report title
and later as "AP5-ATLAS ...". The previous parser failed closed with KAP_FUND_CODE_MISSING.

Fix:
- Preserve existing canonical A. FONUN ADI parser.
- Add bounded fallbacks for a report-title fund code and detached CODE-NAME line.
- No UI change, no store change, no AL/SAT/ranking mutation.
- New regression test for detached extraction order.

Local validation before packaging:
- Target ingestion tests: 8 passed.
- Real cleaned AP5 June 2026 PDF: fund:tefas:AP5, 2026-06-30,
  SAHOL 4800 / 468000 / 47.57%, TTKOM 8400 / 515760 / 52.43%.
