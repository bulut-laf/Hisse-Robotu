HISSE ROBOTU - SPRINT 39 BOS VBTS CSV GUVENLIK TESTI

ZIP'i doğrudan şu klasöre ayıklayın:
D:\Projects\Hisse-Robotu

Eklenen dosya:
backend\tests\test_manual_vbts_csv_empty.py

Test:
python -m pytest .\backend\tests\test_manual_vbts_csv_empty.py -q

Beklenen ilk sonuç:
1 failed

Amaç:
Yalnızca başlık satırı bulunan boş CSV dosyası geçerli sayılmamalı ve
Toplu Tarama kilidini açmamalıdır.
