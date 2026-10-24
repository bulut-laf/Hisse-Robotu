HISSE ROBOTU - SPRINT 39 MANUEL VBTS KURULUM VARLIKLARI TESTI

ZIP'i doğrudan şu klasöre ayıklayın:
D:\Projects\Hisse-Robotu

Eklenen test:
backend\tests\test_manual_vbts_setup_assets.py

Çalıştırma:
python -m pytest .\backend\tests\test_manual_vbts_setup_assets.py -q

Beklenen ilk sonuç:
5 failed

Bu test henüz bulunmayan şu güvenli kurulum varlıklarını tanımlar:
- data\vbts\vbts_sablon.csv
- VBTS-Manuel-Kaynak-Ayarla.ps1
- docs\VBTS_MANUEL_CSV_KULLANIMI.md

Şablon yalnızca başlık içerir ve doğrudan aktif veri dosyası sayılmaz.
