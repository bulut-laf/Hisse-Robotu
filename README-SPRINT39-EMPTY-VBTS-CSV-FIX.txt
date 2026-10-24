HISSE ROBOTU - SPRINT 39 BOS VBTS CSV GUVENLIK DUZELTMESI

1. ZIP'i doğrudan buraya ayıklayın:
   D:\Projects\Hisse-Robotu

2. Yamayı çalıştırın:
   python .\apply_sprint39_empty_vbts_csv_fix.py

3. Hedef test:
   python -m pytest .\backend\tests\test_manual_vbts_csv_empty.py -q

Beklenen:
1 passed

4. Tam regresyon:
   python -m pytest -q

Beklenen toplam:
685 passed
