from __future__ import annotations

import argparse

if __package__:
    from backend.app.data.multi_timeframe_data import (
        MultiTimeframeDataError,
        coklu_zaman_dilimi_verisi_getir,
    )
else:
    from app.data.multi_timeframe_data import (
        MultiTimeframeDataError,
        coklu_zaman_dilimi_verisi_getir,
    )


def argumanlari_oku() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Bir BIST hissesi için saatlik, günlük ve haftalık "
            "tamamlanmış fiyat verisini hazırlar."
        )
    )
    parser.add_argument(
        "sembol",
        help="BIST sembolü. Örnek: THYAO",
    )
    return parser.parse_args()


def main() -> int:
    argumanlar = argumanlari_oku()

    print(
        f"{argumanlar.sembol.upper()} için çoklu zaman dilimi "
        "verisi hazırlanıyor..."
    )

    try:
        paket = coklu_zaman_dilimi_verisi_getir(
            argumanlar.sembol
        )
    except (MultiTimeframeDataError, ValueError) as hata:
        print(f"\nHATA: {hata}")
        return 1

    print("\n" + "=" * 104)
    print("HİSSE ROBOTU — BIST ÇOKLU ZAMAN DİLİMİ VERİ RAPORU")
    print("=" * 104)
    print(f"Sembol                  : {paket.sembol}")
    print(f"Paket veri kimliği      : {paket.veri_kimligi}")
    print(
        "Ortak referans tarihi  : "
        f"{paket.ortak_referans_tarihi.date()}"
    )
    print("\nZAMAN DİLİMLERİ")
    print("-" * 104)
    print(
        f"{'Zaman':<12}{'Aralık':<10}{'Dönem':<10}{'Bar':>8}"
        f"  {'İlk veri':<19}{'Son veri':<19}{'Eksik son mum':<14}"
        "Veri kimliği"
    )
    print("-" * 104)

    for zaman_dilimi in paket.zaman_dilimleri:
        durum = (
            "Çıkarıldı"
            if zaman_dilimi.tamamlanmamis_bar_cikarildi
            else "Yok"
        )
        print(
            f"{zaman_dilimi.ad:<12}"
            f"{zaman_dilimi.interval:<10}"
            f"{zaman_dilimi.period:<10}"
            f"{zaman_dilimi.bar_sayisi:>8}  "
            f"{str(zaman_dilimi.ilk_zaman):<19}"
            f"{str(zaman_dilimi.son_zaman):<19}"
            f"{durum:<14}"
            f"{zaman_dilimi.veri_kimligi}"
        )

    print("=" * 104)
    print(
        "Not: Bu sprint yalnızca tamamlanmış saatlik, günlük ve haftalık "
        "veri altyapısını hazırlar; henüz çoklu zaman dilimi sinyali üretmez."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
