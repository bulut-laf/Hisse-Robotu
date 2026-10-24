HISSE ROBOTU — KAP FDO AGGREGATE TABLE REPAIR V1

Repair:
- Uses KAP's official aggregate 'Fiili Dolaşımdaki Paylar' table.
- One KAP request supplies all requested held symbols.
- SAHOL and TTKOM table row shapes are covered by tests.
- Multiple rows for one symbol are summed.
- Missing symbols remain fail-closed.
- Existing canonical FDO store/read model is preserved.
- No AL/SAT or canonical ranking mutation.
