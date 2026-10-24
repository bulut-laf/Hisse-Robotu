from datetime import date
from backend.app.data.batch_market_data import toplu_fiyat_verisi_getir

sonuc = toplu_fiyat_verisi_getir(
    ["THYAO", "ASELS"],
    islem_gunu=5,
    indirme_donemi="1mo",
    bugun=date(2026, 7, 31),
)

for sembol, veri in sonuc.veriler.items():
    print(sembol, veri.index[-1], len(veri))

for hata in sonuc.hatalar:
    print("HATA:", hata)
