HISSE ROBOTU — FDO CANONICAL SOURCE INTEGRATION V1

What this block does
- Adds a persistent canonical free-float/FDO store.
- Accepts only KAP or MKK-tagged records.
- Requires symbol, free_float_shares, as_of date and source_ref.
- Rejects non-canonical providers instead of guessing FDO.
- Applies a 45-day staleness guard.
- Automatically feeds fresh canonical FDO values into Fund Pressure Read Model.
- Fon/FDO becomes production when a fresh canonical record exists.
- Manual CSV/JSON canonical import is available in Fon Analiz Merkezi.
- No automatic AL/SAT authority.
- No canonical ranking mutation.

Important
This closes the repository data-contract gap. It does NOT yet crawl all KAP company
pages automatically. The next block is official KAP FDO auto-population.
