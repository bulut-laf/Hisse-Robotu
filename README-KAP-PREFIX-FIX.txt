HISSE ROBOTU - SPRINT 38 KAP API KEY PREFIX FIX

1. ZIP'i dogrudan buraya ayiklayin:
   D:\Projects\Hisse-Robotu

2. Calistirin:
   python .\apply_sprint38_kap_prefix_fix.py

3. Test:
   python -m pytest .\backend\tests\test_kap_contract_settings.py -q

Beklenen:
3 passed

Davranis:
- Authorization basligi ve prefix belirtilmemisse Bearer korunur.
- X-API-KEY gibi ozel basliklarda prefix belirtilmemisse yalnizca anahtar gonderilir.
