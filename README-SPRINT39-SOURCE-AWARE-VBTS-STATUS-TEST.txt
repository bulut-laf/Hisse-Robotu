HISSE ROBOTU - SPRINT 39 KAYNAK DUYARLI VBTS DURUM KARTI TESTI

ZIP'i doğrudan şu klasöre ayıklayın:
D:\Projects\Hisse-Robotu

Eklenen dosya:
backend\tests\test_dashboard_source_aware_vbts_status.py

Test:
python -m pytest .\backend\tests\test_dashboard_source_aware_vbts_status.py -q

Beklenen ilk sonuç:
3 failed, 1 passed
veya mevcut metinlere bağlı olarak 4 failed

Amaç:
- VBTS kaynak seçimi okunmalı.
- Kaynak yoksa doğru kilit mesajı gösterilmeli.
- manual_csv seçili ama yol eksikse doğru mesaj gösterilmeli.
- Geçerli manual_csv durumunda aktif koruma mesajı bulunmalı.
