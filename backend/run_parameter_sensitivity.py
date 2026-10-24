from __future__ import annotations

import argparse

from app.analysis.scan_filter import (
    NEGATIF_GORUNUM,
    NOTR_GORUNUM,
    POZITIF_GORUNUM,
    TUM_GORUNUMLER,
)
from app.analysis.stock_analyzer import (
    StockAnalyzer,
    StockAnalyzerError,
)
from app.backtest.analysis_context import analiz_baglamini_olustur
from app.backtest.analysis_profile import (
    AnalysisProfile,
    GECERLI_GORUNUM_SECIMLERI,
    GECERLI_INDIRME_DONEMLERI,
    ORTAK_BASLANGIC_SERMAYESI,
    ORTAK_ELDE_TUTMA_GUNU,
    ORTAK_GORUNUM_SECIMI,
    ORTAK_HEDEF_YUZDE,
    ORTAK_INDIRME_DONEMI,
    ORTAK_ISLEM_GUNU,
    ORTAK_MALIYET_YUZDE,
    ORTAK_MINIMUM_BAR,
    ORTAK_MINIMUM_SKOR,
    ORTAK_POZISYON_YUZDE,
    ORTAK_STOP_YUZDE,
    sembolu_hazirla,
)
from app.backtest.historical_signal_generator import (
    HistoricalSignalGenerator,
    HistoricalSignalGeneratorError,
)
from app.backtest.parameter_sensitivity import (
    ParameterSensitivityAnalyzer,
    ParameterSensitivityError,
    varsayilan_tek_degisken_senaryolari,
)
from app.data.market_data import (
    MarketDataError,
    fiyat_verisi_getir,
)


SATIR_GENISLIGI = 154


def argumanlari_al() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Aynı tarihsel sinyaller üzerinde tek değişkenli "
            "parametre duyarlılığı analizi çalıştırır."
        )
    )
    parser.add_argument("sembol", help="Örnek: THYAO veya THYAO.IS")
    parser.add_argument("--islem-gunu", type=int, default=ORTAK_ISLEM_GUNU)
    parser.add_argument(
        "--donem",
        choices=GECERLI_INDIRME_DONEMLERI,
        default=ORTAK_INDIRME_DONEMI,
    )
    parser.add_argument("--minimum-bar", type=int, default=ORTAK_MINIMUM_BAR)
    parser.add_argument(
        "--gorunum",
        choices=GECERLI_GORUNUM_SECIMLERI,
        default=ORTAK_GORUNUM_SECIMI,
    )
    parser.add_argument("--elde-tutma", type=int, default=ORTAK_ELDE_TUTMA_GUNU)
    parser.add_argument("--min-skor", type=int, default=ORTAK_MINIMUM_SKOR)
    parser.add_argument("--sermaye", type=float, default=ORTAK_BASLANGIC_SERMAYESI)
    parser.add_argument("--pozisyon-yuzde", type=float, default=ORTAK_POZISYON_YUZDE)
    parser.add_argument("--maliyet-yuzde", type=float, default=ORTAK_MALIYET_YUZDE)
    parser.add_argument("--stop-yuzde", type=float, default=ORTAK_STOP_YUZDE)
    parser.add_argument("--hedef-yuzde", type=float, default=ORTAK_HEDEF_YUZDE)
    return parser.parse_args()


def gorunumleri_coz(secim: str) -> tuple[str, ...]:
    return {
        "tum": TUM_GORUNUMLER,
        "pozitif": (POZITIF_GORUNUM,),
        "notr": (NOTR_GORUNUM,),
        "negatif": (NEGATIF_GORUNUM,),
        "pozitif-notr": (
            POZITIF_GORUNUM,
            NOTR_GORUNUM,
        ),
    }[secim]


def yuzde(orani: float) -> str:
    return f"{orani * 100:.2f}%"


def sayi(deger: float | None) -> str:
    if deger is None:
        return "-"

    return f"{deger:.2f}"


def raporu_yazdir(rapor) -> None:
    baz = rapor.baz_sonuc

    print()
    print("=" * SATIR_GENISLIGI)
    print("HİSSE ROBOTU — PARAMETRE DUYARLILIĞI RAPORU")
    print("=" * SATIR_GENISLIGI)
    print(f"Sembol: {rapor.sembol}")
    print(
        "Yöntem: Tek değişkenli yerel duyarlılık; "
        "kombinasyon optimizasyonu yapılmaz."
    )
    print()
    print(
        f"{'Senaryo':<27}"
        f"{'İşlem':>8}"
        f"{'Kazanma':>11}"
        f"{'Toplam':>12}"
        f"{'Yıllık':>12}"
        f"{'Maks. DD':>12}"
        f"{'Kâr F.':>10}"
        f"{'Getiri/DD':>12}"
        f"{'Baza fark':>13}"
    )
    print("-" * SATIR_GENISLIGI)

    for sonuc in rapor.sonuclar:
        fark = (
            sonuc.toplam_getiri_orani
            - baz.toplam_getiri_orani
        )
        print(
            f"{sonuc.senaryo.ad:<27}"
            f"{sonuc.islem_sayisi:>8}"
            f"{yuzde(sonuc.kazanma_orani):>11}"
            f"{yuzde(sonuc.toplam_getiri_orani):>12}"
            f"{yuzde(sonuc.yilliklandirilmis_getiri_orani):>12}"
            f"{yuzde(sonuc.maksimum_dusus_orani):>12}"
            f"{sayi(sonuc.kar_faktoru):>10}"
            f"{sayi(sonuc.getiri_dusus_orani):>12}"
            f"{yuzde(fark):>13}"
        )

    print()
    print("DUYARLILIK ÖZETİ")
    print("-" * SATIR_GENISLIGI)
    print(
        f"Senaryo sayısı              : {rapor.senaryo_sayisi}"
    )
    print(
        "Pozitif senaryo             : "
        f"{rapor.olumlu_senaryo_sayisi} / "
        f"{rapor.senaryo_sayisi} "
        f"({yuzde(rapor.olumlu_senaryo_orani)})"
    )
    print(
        "Medyan toplam getiri        : "
        f"{yuzde(rapor.medyan_getiri_orani)}"
    )
    print(
        "Toplam getiri aralığı       : "
        f"{yuzde(rapor.minimum_getiri_orani)} — "
        f"{yuzde(rapor.maksimum_getiri_orani)}"
    )
    print(
        "Maksimum düşüş aralığı      : "
        f"{yuzde(rapor.minimum_maksimum_dusus_orani)} — "
        f"{yuzde(rapor.maksimum_maksimum_dusus_orani)}"
    )
    print("=" * SATIR_GENISLIGI)
    print(
        "Not: Rapor geçmişte en yüksek getiriyi veren ayarı seçmez; "
        "baz ayarın yakınındaki sonuçların ne kadar değiştiğini gösterir."
    )


def main() -> None:
    argumanlar = argumanlari_al()

    try:
        sembol = sembolu_hazirla(argumanlar.sembol)
        profil = AnalysisProfile(
            islem_gunu=argumanlar.islem_gunu,
            indirme_donemi=argumanlar.donem,
            minimum_bar_sayisi=argumanlar.minimum_bar,
            gorunum_secimi=argumanlar.gorunum,
            elde_tutma_gunu=argumanlar.elde_tutma,
            minimum_skor=argumanlar.min_skor,
            baslangic_sermayesi=argumanlar.sermaye,
            pozisyon_yuzde=argumanlar.pozisyon_yuzde,
            maliyet_yuzde=argumanlar.maliyet_yuzde,
            stop_yuzde=argumanlar.stop_yuzde,
            hedef_yuzde=argumanlar.hedef_yuzde,
        )
        baz_ayar = profil.backtest_yapilandirmasi()

        print()
        print(
            f"{sembol} için parametre duyarlılığı "
            "analizi başlatılıyor..."
        )
        print(
            "Fiyat verisi ve tarihsel sinyaller bir kez hazırlanacak; "
            "ardından yerel senaryolar çalıştırılacak."
        )

        fiyat_verisi = fiyat_verisi_getir(
            sembol=sembol,
            islem_gunu=argumanlar.islem_gunu,
            indirme_donemi=argumanlar.donem,
            yalnizca_tamamlanmis_gunler=True,
        )
        baglam = analiz_baglamini_olustur(
            fiyat_verisi=fiyat_verisi,
            profil=profil,
        )
        print(
            f"Analiz / veri / ayar kimliği: "
            f"{baglam.analiz_kimligi} / "
            f"{baglam.veri_kimligi} / "
            f"{baglam.ayar_kimligi}"
        )
        analizci = StockAnalyzer()
        sinyal_uretimi = HistoricalSignalGenerator(
            analizci.veriden_analiz_et
        ).uret(
            sembol=sembol,
            fiyat_verisi=fiyat_verisi,
            yapilandirma=profil.sinyal_yapilandirmasi(),
        )
        senaryolar = varsayilan_tek_degisken_senaryolari(
            baz_ayar
        )
        rapor = ParameterSensitivityAnalyzer().analiz_et(
            sembol=sembol,
            fiyat_verisi=fiyat_verisi,
            sinyaller=sinyal_uretimi.sinyaller,
            senaryolar=senaryolar,
            baz_senaryo_adi="Baz",
        )
        raporu_yazdir(rapor)

    except (
        ValueError,
        MarketDataError,
        StockAnalyzerError,
        HistoricalSignalGeneratorError,
        ParameterSensitivityError,
    ) as hata:
        print(f"\nHATA: {hata}")


if __name__ == "__main__":
    main()
