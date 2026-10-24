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
from app.backtest.rolling_window_analysis import (
    RollingWindowAnalysisError,
    RollingWindowAnalyzer,
    RollingWindowConfig,
)
from app.data.market_data import (
    MarketDataError,
    fiyat_verisi_getir,
)


SATIR_GENISLIGI = 168


def argumanlari_al() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Sabit strateji ayarlarını örtüşen kayan zaman "
            "pencerelerinde değerlendirir."
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
    parser.add_argument(
        "--pencere-bar",
        type=int,
        default=252,
        help="Her değerlendirme penceresindeki işlem günü sayısı.",
    )
    parser.add_argument(
        "--adim-bar",
        type=int,
        default=63,
        help="Ardışık pencerelerin başlangıçları arasındaki bar sayısı.",
    )
    parser.add_argument(
        "--minimum-islem",
        type=int,
        default=5,
        help="Özet metriklere alınacak pencere için minimum işlem sayısı.",
    )
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


def yuzde(orani: float | None) -> str:
    if orani is None:
        return "-"

    return f"{orani * 100:.2f}%"


def sayi(deger: float | None) -> str:
    if deger is None:
        return "-"

    return f"{deger:.2f}"


def pencere_adi(pencere) -> str:
    return (
        f"{pencere.sira:02d} "
        f"{pencere.baslangic_tarihi.isoformat()} — "
        f"{pencere.bitis_tarihi.isoformat()}"
    )


def raporu_yazdir(rapor) -> None:
    print()
    print("=" * SATIR_GENISLIGI)
    print("HİSSE ROBOTU — KAYAN PENCERE SAĞLAMLIK RAPORU")
    print("=" * SATIR_GENISLIGI)
    print(f"Sembol                 : {rapor.sembol}")
    print(
        "Pencere / adım         : "
        f"{rapor.yapilandirma.pencere_bar_sayisi} / "
        f"{rapor.yapilandirma.adim_bar_sayisi} bar"
    )
    print(
        "Minimum işlem          : "
        f"{rapor.yapilandirma.minimum_islem_sayisi}"
    )
    print(
        "Yöntem                 : Sabit ayarlar, örtüşen dönemler; "
        "parametre optimizasyonu yapılmaz."
    )
    print()
    print(
        f"{'No':<5}"
        f"{'Dönem':<25}"
        f"{'Sinyal':>8}"
        f"{'İşlem':>8}"
        f"{'Yeterli':>9}"
        f"{'Kazanma':>11}"
        f"{'Toplam':>12}"
        f"{'Yıllık':>12}"
        f"{'Maks. DD':>12}"
        f"{'Kâr F.':>10}"
        f"{'Getiri/DD':>12}"
    )
    print("-" * SATIR_GENISLIGI)

    for pencere in rapor.pencereler:
        donem = (
            f"{pencere.baslangic_tarihi.isoformat()} — "
            f"{pencere.bitis_tarihi.isoformat()}"
        )
        print(
            f"{pencere.sira:<5}"
            f"{donem:<25}"
            f"{pencere.sinyal_sayisi:>8}"
            f"{pencere.islem_sayisi:>8}"
            f"{('Evet' if pencere.yeterli_islem_mi else 'Hayır'):>9}"
            f"{yuzde(pencere.kazanma_orani):>11}"
            f"{yuzde(pencere.toplam_getiri_orani):>12}"
            f"{yuzde(pencere.yilliklandirilmis_getiri_orani):>12}"
            f"{yuzde(pencere.maksimum_dusus_orani):>12}"
            f"{sayi(pencere.kar_faktoru):>10}"
            f"{sayi(pencere.getiri_dusus_orani):>12}"
        )

    print()
    print("SAĞLAMLIK ÖZETİ")
    print("-" * SATIR_GENISLIGI)
    print(f"Toplam pencere          : {rapor.pencere_sayisi}")
    print(
        "Değerlendirilen pencere: "
        f"{rapor.degerlendirilen_pencere_sayisi}"
    )
    print(f"Yetersiz pencere        : {rapor.yetersiz_pencere_sayisi}")
    print(
        "Pozitif pencere        : "
        f"{rapor.pozitif_pencere_sayisi} / "
        f"{rapor.degerlendirilen_pencere_sayisi} "
        f"({yuzde(rapor.pozitif_pencere_orani)})"
    )
    print(
        "Medyan toplam getiri   : "
        f"{yuzde(rapor.medyan_toplam_getiri_orani)}"
    )
    print(
        "Medyan yıllık getiri   : "
        f"{yuzde(rapor.medyan_yilliklandirilmis_getiri_orani)}"
    )
    print(
        "Toplam getiri aralığı  : "
        f"{yuzde(rapor.minimum_toplam_getiri_orani)} — "
        f"{yuzde(rapor.maksimum_toplam_getiri_orani)}"
    )
    print(
        "Maksimum düşüş aralığı : "
        f"{yuzde(rapor.minimum_maksimum_dusus_orani)} — "
        f"{yuzde(rapor.maksimum_maksimum_dusus_orani)}"
    )

    if rapor.en_iyi_pencere is not None:
        print(
            "En iyi pencere        : "
            f"{pencere_adi(rapor.en_iyi_pencere)} / "
            f"{yuzde(rapor.en_iyi_pencere.toplam_getiri_orani)}"
        )

    if rapor.en_zayif_pencere is not None:
        print(
            "En zayıf pencere      : "
            f"{pencere_adi(rapor.en_zayif_pencere)} / "
            f"{yuzde(rapor.en_zayif_pencere.toplam_getiri_orani)}"
        )

    print("=" * SATIR_GENISLIGI)
    print(
        "Not: Pencereler aynı sabit stratejiyi farklı dönemlerde "
        "ölçer. Örtüşen pencereler bağımsız yatırım dönemleri değil, "
        "rejim duyarlılığı gözlemleridir."
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
        backtest_ayari = profil.backtest_yapilandirmasi()
        pencere_ayari = RollingWindowConfig(
            pencere_bar_sayisi=argumanlar.pencere_bar,
            adim_bar_sayisi=argumanlar.adim_bar,
            minimum_islem_sayisi=argumanlar.minimum_islem,
        )

        print()
        print(
            f"{sembol} için kayan pencere sağlamlık "
            "analizi başlatılıyor..."
        )
        print(
            "Fiyat verisi ve tarihsel sinyaller bir kez hazırlanacak; "
            "sabit ayarlar dönemler boyunca ölçülecek."
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
        rapor = RollingWindowAnalyzer().analiz_et(
            sembol=sembol,
            fiyat_verisi=fiyat_verisi,
            sinyaller=sinyal_uretimi.sinyaller,
            backtest_yapilandirmasi=backtest_ayari,
            yapilandirma=pencere_ayari,
        )
        raporu_yazdir(rapor)

    except (
        ValueError,
        MarketDataError,
        StockAnalyzerError,
        HistoricalSignalGeneratorError,
        RollingWindowAnalysisError,
    ) as hata:
        print(f"\nHATA: {hata}")


if __name__ == "__main__":
    main()
