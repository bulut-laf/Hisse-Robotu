from __future__ import annotations

import sys

from app.analysis.support_resistance import (
    SupportResistanceError,
    destek_direnc_bul,
)
from app.data.market_data import (
    MarketDataError,
    fiyat_verisi_getir,
)


def main() -> None:
    sembol = (
        sys.argv[1].strip().upper()
        if len(sys.argv) > 1
        else "ASELS.IS"
    )

    print(
        f"\n{sembol} destek ve direnç analizi hazırlanıyor...\n"
    )

    try:
        fiyat_verisi = fiyat_verisi_getir(
            sembol=sembol,
            islem_gunu=160,
            indirme_donemi="1y",
            yalnizca_tamamlanmis_gunler=True,
        )

        sonuc = destek_direnc_bul(
            veri=fiyat_verisi,
            bakis_periyodu=120,
            pivot_genisligi=2,
            birlestirme_toleransi_yuzde=1.00,
        )

    except (
        ValueError,
        MarketDataError,
        SupportResistanceError,
    ) as hata:
        print(f"HATA: {hata}")
        return

    print(f"Mevcut fiyat         : {sonuc.mevcut_fiyat:.2f}")
    print(f"Pivot dip sayısı     : {sonuc.pivot_dip_sayisi}")
    print(f"Pivot tepe sayısı    : {sonuc.pivot_tepe_sayisi}")

    print("\nDESTEK")
    print("-" * 50)

    if sonuc.destek is None:
        print("Yakın destek seviyesi bulunamadı.")
    else:
        print(f"Destek fiyatı        : {sonuc.destek.fiyat:.2f}")
        print(
            f"Fiyata uzaklık       : "
            f"%{sonuc.destek_uzaklik_yuzde:.2f}"
        )
        print(
            f"Temas sayısı         : "
            f"{sonuc.destek.temas_sayisi}"
        )
        print(f"Seviye gücü          : {sonuc.destek.guc}")
        print(
            f"Son temas tarihi     : "
            f"{sonuc.destek.son_temas_tarihi}"
        )

    print("\nDİRENÇ")
    print("-" * 50)

    if sonuc.direnc is None:
        print("Yakın direnç seviyesi bulunamadı.")
    else:
        print(f"Direnç fiyatı        : {sonuc.direnc.fiyat:.2f}")
        print(
            f"Fiyata uzaklık       : "
            f"%{sonuc.direnc_uzaklik_yuzde:.2f}"
        )
        print(
            f"Temas sayısı         : "
            f"{sonuc.direnc.temas_sayisi}"
        )
        print(f"Seviye gücü          : {sonuc.direnc.guc}")
        print(
            f"Son temas tarihi     : "
            f"{sonuc.direnc.son_temas_tarihi}"
        )


if __name__ == "__main__":
    main()