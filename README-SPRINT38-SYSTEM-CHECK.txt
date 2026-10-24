HISSE ROBOTU - SPRINT 38 SISTEM KONTROLU

1. ZIP'i doğrudan buraya ayıklayın:
   D:\Projects\Hisse-Robotu

2. Yamayı çalıştırın:
   python .\apply_sprint38_system_check_update.py

3. Hedef test:
   python -m pytest .\backend\tests\test_system_check.py -q

4. Tam regresyon:
   python -m pytest -q

5. Sistem kontrolü:
   python .\backend\run_system_check.py

Beklenen:
Sürüm: Sprint-38
Başarılı / Uyarı / Hata: 21 / 0 / 0
SONUÇ: Sistem kullanıma hazır.
