HISSE ROBOTU - SPRINT 38 KAP PREFIX NONE FIX

1. ZIP'i doğrudan buraya ayıklayın:
   D:\Projects\Hisse-Robotu

2. Çalıştırın:
   python .\apply_sprint38_kap_prefix_none_fix.py

3. Hedef test:
   python -m pytest .\backend\tests\test_kap_settings.py .\backend\tests\test_kap_factory.py -q

Beklenen:
8 passed

4. Tam regresyon:
   python -m pytest -q

Beklenen:
660 passed
