HISSE ROBOTU — FUND PRESSURE PRODUCTION READ MODEL V1

Implemented
- Aggregates latest KAP fund snapshots by stock.
- Builds fund concentration / Top3 / HHI from current fund positions.
- Reuses the repository's existing BIST OHLCV loader for explicit refresh only.
- Computes ADV20 TL value, 20-day median TL value, 10%/20% liquidation days,
  stress liquidation days, down-volume ratio and 20-day return.
- Reuses stock-level distribution breadth from the existing snapshot change engine.
- Feeds the existing three observational pressure subscores.
- Per-symbol market-data failures are isolated.
- No automatic AL/SAT or canonical ranking mutation.

Repository contract gap
- Exact source contains free_float_shares only in Research Profiles import context.
- No canonical persistent free-float/FDO source is currently available to Fund Analysis.
- V1 therefore does NOT guess FDO from yfinance or another unapproved source.
- Fon/FDO remains unavailable until a canonical free-float source is integrated.

Application contract
1. git apply --check
2. one Git patch
3. target tests
4. full backend regression
5. automatic rollback on failure
