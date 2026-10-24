from __future__ import annotations

import argparse

if __package__:
    from backend.app.analysis.multi_timeframe_analysis import (
        MultiTimeframeAnalysisError,
        coklu_zaman_dilimi_teknik_analizi_yap,
    )
    from backend.app.data.multi_timeframe_data import (
        MultiTimeframeDataError,
        coklu_zaman_dilimi_verisi_getir,
    )
else:
    from app.analysis.multi_timeframe_analysis import (
        MultiTimeframeAnalysisError,
        coklu_zaman_dilimi_teknik_analizi_yap,
    )
    from app.data.multi_timeframe_data import (
        MultiTimeframeDataError,
        coklu_zaman_dilimi_verisi_getir,
    )


def argumanlari_oku() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Bir BIST hissesi için haftalık trend, günlük yön teyidi "
            "ve saatlik zamanlama analizi üretir."
        )
    )
    parser.add_argument(
        "sembol",
        help="BIST sembolü. Örnek: THYAO",
    )
    return parser.parse_args()


def main() -> int:
    argumanlar = argumanlari_oku()
    sembol = argumanlar.sembol.upper()

    print(f"{sembol} için çoklu zaman dilimi teknik analizi hazırlanıyor...")

    try:
        paket = coklu_zaman_dilimi_verisi_getir(sembol)
        analiz = coklu_zaman_dilimi_teknik_analizi_yap(paket)
    except (
        MultiTimeframeDataError,
        MultiTimeframeAnalysisError,
        ValueError,
    ) as hata:
        print(f"\nHATA: {hata}")
        return 1

    print("\n" + "=" * 100)
    print("HİSSE ROBOTU — ÇOKLU ZAMAN DİLİMİ TEKNİK TEYİT RAPORU")
    print("=" * 100)
    print(f"Sembol             : {analiz.sembol}")
    print(f"Veri kimliği       : {analiz.veri_kimligi}")
    print(f"Analiz kimliği     : {analiz.analiz_kimligi}")
    print(f"Uyum skoru         : {analiz.uyum_skoru}/100")
    print(f"Teyit durumu       : {analiz.teyit_durumu}")

    print("\nZAMAN DİLİMİ SONUÇLARI")
    print("-" * 100)
    print(
        f"{'Rol':<18}{'Zaman':<12}{'Son tarih':<20}{'Kapanış':>11}"
        f"{'RSI14':>9}{'Skor':>8}  {'Yön':<10}"
    )
    print("-" * 100)

    satirlar = (
        ("Ana trend", analiz.haftalik),
        ("Yön teyidi", analiz.gunluk),
        ("Zamanlama", analiz.saatlik),
    )
    for rol, sonuc in satirlar:
        print(
            f"{rol:<18}{sonuc.ad:<12}{str(sonuc.son_zaman):<20}"
            f"{sonuc.kapanis:>11.2f}{sonuc.rsi14:>9.2f}"
            f"{sonuc.skor:>8}  {sonuc.yon:<10}"
        )

    print("\nPOZİTİF TEYİTLER")
    if analiz.pozitif_nedenler:
        for neden in analiz.pozitif_nedenler:
            print(f"  + {neden}")
    else:
        print("  + Belirgin pozitif teyit yok.")

    print("\nRİSKLER / BEKLEYEN TEYİTLER")
    if analiz.riskler:
        for risk in analiz.riskler:
            print(f"  - {risk}")
    else:
        print("  - Belirgin teknik uyumsuzluk yok.")

    print("=" * 100)
    print(
        "Not: Bu rapor alış veya satış emri üretmez. Yalnızca tamamlanmış "
        "mumlar üzerinden zaman dilimleri arasındaki teknik uyumu gösterir."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
