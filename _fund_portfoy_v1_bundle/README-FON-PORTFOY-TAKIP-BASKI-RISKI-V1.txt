HISSE ROBOTU — FON PORTFOY TAKIP + BASKI RISKI V1

Bu paket kaynak-dogru Git patch kullanir.
PowerShell string/regex kaynak mutasyonu yapmaz.

Eklenenler:
- Append-only tarihli fon portfoy snapshot store
- Snapshot change engine
- NEW_ENTRY / INCREASED / REDUCED / FULL_EXIT / UNCHANGED / UNKNOWN
- Share-count bazli confirmed change; weight-only degisim trade diye etiketlenmez
- Partial snapshot full-exit kaniti sayilmaz
- Hisse bazli accumulation/distribution breadth
- Fon/FDO ve kurumsal concentration metrikleri
- ADV20 %10 / %20 + stress liquidation-day senaryolari
- Cross-sectional percentile engine
- Fund concentration / exit difficulty / active selling pressure observational alt skorlari
- automatic_trade_authority=NONE

Exact-source sandbox dogrulamasi:
- git apply --check: PASS
- hedef testler: 14 passed

Not:
Exact-source ZIP icinde backend/app/ui/fund_analysis_center.py yoktu.
Bu nedenle mevcut UI'yi tahmin ederek degistirmedik.
UI bridge bir sonraki source-accurate bloktur.
