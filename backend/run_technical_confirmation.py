from __future__ import annotations

import argparse

if __package__:
    from backend.app.analysis.technical_confirmation import (
        TechnicalConfirmationError,
        teknik_teyit_analizi_yap,
    )
    from backend.app.data.multi_timeframe_data import (
        MultiTimeframeDataError,
        coklu_zaman_dilimi_verisi_getir,
    )
else:
    from app.analysis.technical_confirmation import (
        TechnicalConfirmationError,
        teknik_teyit_analizi_yap,
    )
    from app.data.multi_timeframe_data import (
        MultiTimeframeDataError,
        coklu_zaman_dilimi_verisi_getir,
    )


def argumanlari_oku() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Bir BIST hissesi için trend çizgisi kırılımı, hacim teyidi, "
            "EMA kesişimleri, Golden Cross / Death Cross ve RSI-MACD "
            "teknik teyidi üretir."
        )
    )
    parser.add_argument(
        "sembol",
        help="BIST sembolü. Örnek: THYAO",
    )
    return parser.parse_args()


def _fiyat_metni(deger: float | None) -> str:
    return "Yok" if deger is None else f"{deger:.2f}"


def _oran_metni(deger: float | None) -> str:
    return "Yok" if deger is None else f"{deger:.2f}x"


def main() -> int:
    argumanlar = argumanlari_oku()
    sembol = argumanlar.sembol.upper()

    print(f"{sembol} için trend, kırılım ve teknik teyit hazırlanıyor...")

    try:
        paket = coklu_zaman_dilimi_verisi_getir(sembol)
        analiz = teknik_teyit_analizi_yap(paket)
    except (
        MultiTimeframeDataError,
        TechnicalConfirmationError,
        ValueError,
    ) as hata:
        print(f"\nHATA: {hata}")
        return 1

    print("\n" + "=" * 118)
    print("HİSSE ROBOTU — TREND, KIRILIM VE TEKNİK TEYİT RAPORU")
    print("=" * 118)
    print(f"Sembol              : {analiz.sembol}")
    print(f"Veri kimliği        : {analiz.veri_kimligi}")
    print(f"Analiz kimliği      : {analiz.analiz_kimligi}")
    print(f"Teknik teyit skoru  : {analiz.teyit_skoru}/100")
    print(f"Teyit durumu        : {analiz.teyit_durumu}")

    print("\nZAMAN DİLİMİ ÖZETİ")
    print("-" * 118)
    print(
        f"{'Rol':<17}{'Zaman':<11}{'Son tarih':<20}{'Kapanış':>10}"
        f"{'Skor':>7}  {'Yön':<9}{'Kırılım':<38}"
    )
    print("-" * 118)
    satirlar = (
        ("Ana trend", analiz.haftalik),
        ("Yön teyidi", analiz.gunluk),
        ("Zamanlama", analiz.saatlik),
    )
    for rol, sonuc in satirlar:
        print(
            f"{rol:<17}{sonuc.ad:<11}{str(sonuc.son_zaman):<20}"
            f"{sonuc.kapanis:>10.2f}{sonuc.skor:>7}  "
            f"{sonuc.yon:<9}{sonuc.kirilim.durum:<38}"
        )

    print("\nDESTEK / DİRENÇ")
    print("-" * 118)
    for rol, sonuc in satirlar:
        print(
            f"{rol:<17} Destek: {_fiyat_metni(sonuc.destek):>10} "
            f"({sonuc.destek_gucu or 'Yok':<6})  "
            f"Direnç: {_fiyat_metni(sonuc.direnc):>10} "
            f"({sonuc.direnc_gucu or 'Yok':<6})"
        )

    print("\nHAREKETLİ ORTALAMA TEYİTLERİ")
    print("-" * 118)
    for rol, sonuc in satirlar:
        ort = sonuc.ortalamalar
        print(f"{rol:<17} EMA9/21 : {ort.ema9_21_durumu}")
        print(f"{'':<17} EMA21/55: {ort.ema21_55_durumu}")
        print(f"{'':<17} SMA50/200: {ort.uzun_vade_durumu}")

    print("\nMOMENTUM / HACİM")
    print("-" * 118)
    for rol, sonuc in satirlar:
        momentum = sonuc.momentum
        kirilim = sonuc.kirilim
        print(
            f"{rol:<17} RSI14: {momentum.rsi14:>6.2f}  "
            f"MACD teyidi: {momentum.durum:<8}  "
            f"Hacim oranı: {_oran_metni(kirilim.hacim_orani):>7}  "
            f"Hacim teyidi: {'Var' if kirilim.hacim_teyidi else 'Yok'}"
        )

    print("\nPOZİTİF TEYİTLER")
    if analiz.pozitif_nedenler:
        for neden in analiz.pozitif_nedenler:
            print(f"  + {neden}")
    else:
        print("  + Belirgin ortak pozitif teyit yok.")

    print("\nRİSKLER / BEKLEYEN TEYİTLER")
    if analiz.riskler:
        for risk in analiz.riskler:
            print(f"  - {risk}")
    else:
        print("  - Belirgin teknik risk bulunmadı.")

    print("=" * 118)
    print(
        "Not: Erken uyarı, mum içindeki geçici kırılımı; teyitli kırılım ise "
        "tamamlanmış mum kapanışını ifade eder. Bu sprint alış, satış, stop "
        "veya hedef fiyatı üretmez."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
