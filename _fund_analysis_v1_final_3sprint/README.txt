HISSE ROBOTU — FUND ANALYSIS V1 FINAL 3-SPRINT PACKAGE

SPRINT 1 — FDO OFFICIAL KAP AUTO POPULATION
- Uses official KAP BIST company directory.
- Resolves company summary links to official KAP general-information pages.
- Parses "Fiili Dolaşımdaki Pay Tutarı (TL)" for only equity symbols actually held
  in the latest fund portfolio snapshots.
- Stores records in the existing canonical KAP/MKK free-float store.
- Observation date is the explicit fetch date; source_ref is the exact KAP company page.
- Per-symbol failures are isolated and do not fabricate missing FDO values.

SPRINT 2 — FUND PRESSURE FULL PRODUCTION ACTIVATION
- Adds one explicit "KAP FDO + Baskı Riskini Tam Güncelle" UI action.
- Runs official KAP FDO population, then the existing production pressure read model.
- Fon/FDO, ADV20, liquidation days, concentration/HHI, distribution breadth and
  the three observational pressure subscores are displayed when their inputs exist.
- No automatic trading authority.

SPRINT 3 — PRODUCTION HARDENING
- No page-open network call.
- Explicit refresh only.
- Official KAP HTTPS/host/path validation.
- Bounded directory/general-page payload sizes.
- Max 100 held symbols per refresh to prevent an unbounded KAP request burst.
- Redirect validation and fail-closed source handling.
- Idempotent canonical FDO persistence.
- Manual canonical FDO import and manual portfolio PDF remain fallback paths.
- AL/SAT and canonical ranking remain untouched.

Application contract
1. git apply --check
2. one Git patch
3. target regression
4. full backend regression
5. automatic patch rollback on test failure

After installation, perform FINAL_LIVE_SMOKE from Fon Analiz Merkezi:
"KAP FDO + Baskı Riskini Tam Güncelle"
