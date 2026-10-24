HISSE ROBOTU - SPRINT 39 MANUEL VBTS KURULUM VARLIKLARI

1. ZIP'i doğrudan buraya ayıklayın:
   D:\Projects\Hisse-Robotu

2. Hedef testi çalıştırın:
   python -m pytest .\backend\tests\test_manual_vbts_setup_assets.py -q

Beklenen:
5 passed

3. Tam regresyon:
   python -m pytest -q

Beklenen toplam:
690 passed

NOT:
Bu paket vbts_guncel.csv oluşturmaz ve örnek/piyasa verisi eklemez.
Gerçek dosya yalnızca resmî KAP bildirimlerinden kullanıcı tarafından
hazırlanmalıdır.
