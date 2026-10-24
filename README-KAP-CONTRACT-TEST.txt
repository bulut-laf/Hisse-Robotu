HISSE ROBOTU - SPRINT 38 KAP ABONELIK SOZLESMESI TESTI

ZIP'i dogrudan su klasore ayiklayin:
D:\Projects\Hisse-Robotu

Test:
python -m pytest .\backend\tests\test_kap_contract_settings.py -q

Beklenen ilk sonuc:
3 failed

Amac:
- /notifications sabit yolunu kaldirmak
- Bearer varsayimini kaldirmak
- endpoint, API anahtar basligi ve yanit liste anahtarini abonelik ayarlarindan almak
- bu ayarlar eksikse guvenli durmak
