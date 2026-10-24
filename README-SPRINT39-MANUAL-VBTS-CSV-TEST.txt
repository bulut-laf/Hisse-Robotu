HISSE ROBOTU - SPRINT 39 MANUEL RESMI VBTS CSV TESTI

ZIP'i dogrudan su klasore ayiklayin:
D:\Projects\Hisse-Robotu

Eklenen dosya:
backend\tests\test_manual_vbts_csv.py

Test:
python -m pytest .\backend\tests\test_manual_vbts_csv.py -q

Beklenen ilk sonuc:
4 failed

Tanımlanan CSV sütunları:
symbol
measure_type
start_date
end_date
source_reference

Güvenlik:
- Zorunlu sütun eksikse reddedilir.
- Başlangıç/bitiş tarihi hatalıysa reddedilir.
- Dosya belirlenen süreden eskiyse reddedilir.
- Geçerli kayıtlar VbtsDataset biçimine dönüştürülür.
