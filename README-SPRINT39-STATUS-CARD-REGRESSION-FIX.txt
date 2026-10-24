HISSE ROBOTU - SPRINT 39 DURUM KARTI REGRESYON DUZELTMESI

1. ZIP'i doğrudan buraya ayıklayın:
   D:\Projects\Hisse-Robotu

2. Yamayı çalıştırın:
   python .\apply_sprint39_status_card_regression_fix.py

3. Hedef testler:
   python -m pytest .\backend\tests\test_dashboard_kap_status_card.py .\backend\tests\test_dashboard_source_aware_vbts_status.py -q

Beklenen:
8 passed

4. Tam regresyon:
   python -m pytest -q

Beklenen toplam:
684 passed
