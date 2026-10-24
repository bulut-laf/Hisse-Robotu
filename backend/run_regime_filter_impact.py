from __future__ import annotations

import argparse

from app.analysis.stock_analyzer import StockAnalyzer, StockAnalyzerError
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
from app.backtest.market_regime_analysis import MarketRegimeConfig
from app.backtest.regime_filter_impact import (
    RegimeFilterImpactAnalyzer,
    RegimeFilterImpactError,
)
from app.backtest.rolling_window_analysis import RollingWindowConfig
from app.data.market_data import MarketDataError, fiyat_verisi_getir


SATIR_GENISLIGI = 154


def argumanlari_al() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Baz strateji ile yalnızca yükseliş trendinde işlem açan "
            "deneysel rejim filtresini karşılaştırır."
        )
    )
    parser.add_argument("sembol")
    parser.add_argument("--islem-gunu", type=int, default=ORTAK_ISLEM_GUNU)
    parser.add_argument(
        "--donem", choices=GECERLI_INDIRME_DONEMLERI, default=ORTAK_INDIRME_DONEMI
    )
    parser.add_argument("--minimum-bar", type=int, default=ORTAK_MINIMUM_BAR)
    parser.add_argument("--elde-tutma", type=int, default=ORTAK_ELDE_TUTMA_GUNU)
    parser.add_argument("--min-skor", type=int, default=ORTAK_MINIMUM_SKOR)
    parser.add_argument("--sermaye", type=float, default=ORTAK_BASLANGIC_SERMAYESI)
    parser.add_argument("--pozisyon-yuzde", type=float, default=ORTAK_POZISYON_YUZDE)
    parser.add_argument("--maliyet-yuzde", type=float, default=ORTAK_MALIYET_YUZDE)
    parser.add_argument("--stop-yuzde", type=float, default=ORTAK_STOP_YUZDE)
    parser.add_argument("--hedef-yuzde", type=float, default=ORTAK_HEDEF_YUZDE)
    parser.add_argument("--pencere-bar", type=int, default=252)
    parser.add_argument("--adim-bar", type=int, default=63)
    parser.add_argument("--minimum-islem", type=int, default=5)
    return parser.parse_args()


def yuzde(deger: float | None) -> str:
    return "-" if deger is None else f"{deger * 100:.2f}%"


def sayi(deger: float | None) -> str:
    return "-" if deger is None else f"{deger:.2f}"


def raporu_yazdir(rapor) -> None:
    print()
    print("=" * SATIR_GENISLIGI)
    print("HİSSE ROBOTU — REJİM FİLTRESİ ETKİ VE SAĞLAMLIK RAPORU")
    print("=" * SATIR_GENISLIGI)
    print(f"Sembol                        : {rapor.sembol}")
    print(f"Toplam sinyal                 : {rapor.toplam_sinyal_sayisi}")
    print(
        "Rejimi belirlenen sinyal      : "
        f"{rapor.rejimi_belirlenen_sinyal_sayisi}"
    )
    print(
        "Rejimi belirlenemeyen sinyal  : "
        f"{rapor.rejimi_belirlenemeyen_sinyal_sayisi}"
    )
    print(
        "Yükseliş filtresine uygun     : "
        f"{rapor.filtreye_uygun_sinyal_sayisi}"
    )
    print(f"Filtre dışı sinyal            : {rapor.filtre_disi_sinyal_sayisi}")
    print()
    print("TOPLAM DÖNEM KARŞILAŞTIRMASI")
    print("-" * SATIR_GENISLIGI)
    print(
        f"{'Ölçüt':<42}{'Baz Strateji':>25}"
        f"{'Yükseliş Filtresi':>25}{'Fark':>20}"
    )
    print("-" * SATIR_GENISLIGI)
    print(
        f"{'Sinyal sayısı':<42}{rapor.baz.sinyal_sayisi:>25}"
        f"{rapor.filtreli.sinyal_sayisi:>25}"
        f"{rapor.filtreli.sinyal_sayisi - rapor.baz.sinyal_sayisi:>20}"
    )
    print(
        f"{'Tamamlanan işlem':<42}{rapor.baz.islem_sayisi:>25}"
        f"{rapor.filtreli.islem_sayisi:>25}{rapor.islem_sayisi_farki:>20}"
    )
    print(
        f"{'Kazanma oranı':<42}{yuzde(rapor.baz.kazanma_orani):>25}"
        f"{yuzde(rapor.filtreli.kazanma_orani):>25}{'':>20}"
    )
    print(
        f"{'Toplam getiri':<42}{yuzde(rapor.baz.toplam_getiri_orani):>25}"
        f"{yuzde(rapor.filtreli.toplam_getiri_orani):>25}"
        f"{yuzde(rapor.toplam_getiri_farki_orani):>20}"
    )
    print(
        f"{'Yıllıklandırılmış getiri':<42}"
        f"{yuzde(rapor.baz.yilliklandirilmis_getiri_orani):>25}"
        f"{yuzde(rapor.filtreli.yilliklandirilmis_getiri_orani):>25}"
        f"{yuzde(rapor.yillik_getiri_farki_orani):>20}"
    )
    print(
        f"{'Günlük maksimum düşüş':<42}"
        f"{yuzde(rapor.baz.maksimum_dusus_orani):>25}"
        f"{yuzde(rapor.filtreli.maksimum_dusus_orani):>25}"
        f"{yuzde(rapor.maksimum_dusus_farki_orani):>20}"
    )
    print(
        f"{'Kâr faktörü':<42}{sayi(rapor.baz.kar_faktoru):>25}"
        f"{sayi(rapor.filtreli.kar_faktoru):>25}{'':>20}"
    )
    print(
        f"{'Getiri / maksimum düşüş':<42}"
        f"{sayi(rapor.baz.getiri_dusus_orani):>25}"
        f"{sayi(rapor.filtreli.getiri_dusus_orani):>25}{'':>20}"
    )

    ozet = rapor.kayan_pencere_ozeti
    print()
    print("KAYAN PENCERE SAĞLAMLIK KARŞILAŞTIRMASI")
    print("-" * SATIR_GENISLIGI)
    print(f"Eşleşmiş yeterli pencere      : {ozet.toplam_eslesmis_pencere}")
    print(f"Filtrenin üstün olduğu        : {ozet.filtre_ustun_pencere}")
    print(f"Bazın üstün olduğu            : {ozet.baz_ustun_pencere}")
    print(f"Eşit pencere                  : {ozet.esit_pencere}")
    print(f"Filtre üstünlük oranı         : {yuzde(ozet.filtre_ustunluk_orani)}")
    print(
        "Medyan pencere getiri farkı   : "
        f"{yuzde(ozet.medyan_getiri_farki_orani)}"
    )
    print(
        "Pencere getiri farkı aralığı  : "
        f"{yuzde(ozet.minimum_getiri_farki_orani)} — "
        f"{yuzde(ozet.maksimum_getiri_farki_orani)}"
    )
    print("=" * SATIR_GENISLIGI)
    print(
        "Not: Yükseliş filtresi deneysel karşılaştırmadır. "
        "Ana stratejiye otomatik olarak uygulanmaz ve geçmişe göre "
        "filtre optimizasyonu yapılmaz."
    )


def main() -> None:
    args = argumanlari_al()
    sembol = sembolu_hazirla(args.sembol)

    try:
        profil = AnalysisProfile(
            islem_gunu=args.islem_gunu,
            indirme_donemi=args.donem,
            minimum_bar_sayisi=args.minimum_bar,
            elde_tutma_gunu=args.elde_tutma,
            minimum_skor=args.min_skor,
            baslangic_sermayesi=args.sermaye,
            pozisyon_yuzde=args.pozisyon_yuzde,
            maliyet_yuzde=args.maliyet_yuzde,
            stop_yuzde=args.stop_yuzde,
            hedef_yuzde=args.hedef_yuzde,
        )

        print()
        print(f"{sembol} için rejim filtresi etki analizi başlatılıyor...")
        print(
            "Tarihsel sinyaller bir kez hazırlanacak; baz ve deneysel "
            "yükseliş filtresi aynı veriyle karşılaştırılacak."
        )
        fiyat_verisi = fiyat_verisi_getir(
            sembol=sembol,
            islem_gunu=args.islem_gunu,
            indirme_donemi=args.donem,
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
        sinyal_uretimi = HistoricalSignalGenerator(
            StockAnalyzer().veriden_analiz_et
        ).uret(
            sembol=sembol,
            fiyat_verisi=fiyat_verisi,
            yapilandirma=profil.sinyal_yapilandirmasi(),
        )
        backtest_ayari = profil.backtest_yapilandirmasi()
        rapor = RegimeFilterImpactAnalyzer().analiz_et(
            sembol=sembol,
            fiyat_verisi=fiyat_verisi,
            sinyaller=sinyal_uretimi.sinyaller,
            backtest_yapilandirmasi=backtest_ayari,
            rejim_yapilandirmasi=MarketRegimeConfig(),
            kayan_pencere_yapilandirmasi=RollingWindowConfig(
                pencere_bar_sayisi=args.pencere_bar,
                adim_bar_sayisi=args.adim_bar,
                minimum_islem_sayisi=args.minimum_islem,
            ),
        )
        raporu_yazdir(rapor)

    except (
        ValueError,
        MarketDataError,
        StockAnalyzerError,
        HistoricalSignalGeneratorError,
        RegimeFilterImpactError,
    ) as hata:
        print(f"\nHATA: {hata}")


if __name__ == "__main__":
    main()
