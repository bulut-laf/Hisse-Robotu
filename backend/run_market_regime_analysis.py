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
from app.backtest.backtest_engine import (
    BacktestEngine,
    BacktestEngineError,
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
from app.backtest.market_regime_analysis import (
    MarketRegimeAnalysisError,
    MarketRegimeAnalyzer,
    MarketRegimeConfig,
)
from app.backtest.position_overlap import (
    cakisan_islemleri_filtrele,
)
from app.data.market_data import (
    MarketDataError,
    fiyat_verisi_getir,
)


SATIR_GENISLIGI = 156


def argumanlari_al() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Sabit strateji işlemlerini açıklanabilir piyasa "
            "rejimlerine göre performanslandırır."
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
    parser.add_argument("--hizli-ema", type=int, default=21)
    parser.add_argument("--yavas-ema", type=int, default=55)
    parser.add_argument("--egim-bakisi", type=int, default=ORTAK_ELDE_TUTMA_GUNU)
    parser.add_argument(
        "--minimum-ema-farki-yuzde",
        type=float,
        default=0.50,
    )
    parser.add_argument("--atr-periyodu", type=int, default=14)
    parser.add_argument("--volatilite-bakisi", type=int, default=42)
    parser.add_argument(
        "--yuksek-volatilite-carpani",
        type=float,
        default=1.0,
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


def tarih(tarih_degeri) -> str:
    if tarih_degeri is None:
        return "-"

    return tarih_degeri.isoformat()


def performans_tablosu_yazdir(
    baslik: str,
    performanslar,
) -> None:
    print()
    print(baslik)
    print("-" * SATIR_GENISLIGI)
    print(
        f"{'Rejim':<50}"
        f"{'İşlem':>8}"
        f"{'Pay':>10}"
        f"{'Kazanan':>10}"
        f"{'Kaybeden':>11}"
        f"{'Kazanma':>11}"
        f"{'Ort. Net':>12}"
        f"{'Bileşik':>12}"
        f"{'Kâr F.':>10}"
        f"{'Maks. Kayıp':>12}"
    )
    print("-" * SATIR_GENISLIGI)

    for performans in performanslar:
        print(
            f"{performans.rejim_adi:<50}"
            f"{performans.islem_sayisi:>8}"
            f"{yuzde(performans.toplam_islem_orani):>10}"
            f"{performans.kazanan_islem_sayisi:>10}"
            f"{performans.kaybeden_islem_sayisi:>11}"
            f"{yuzde(performans.kazanma_orani):>11}"
            f"{yuzde(performans.ortalama_net_getiri_orani):>12}"
            f"{yuzde(performans.toplam_net_getiri_orani):>12}"
            f"{sayi(performans.kar_faktoru):>10}"
            f"{performans.maksimum_ardisik_kayip:>12}"
        )


def gun_dagilimi_yazdir(
    baslik: str,
    dagilim,
) -> None:
    print()
    print(baslik)
    print("-" * SATIR_GENISLIGI)

    for kayit in dagilim:
        print(
            f"{kayit.rejim_adi:<30}: "
            f"{kayit.gun_sayisi:>5} gün "
            f"({yuzde(kayit.toplam_gun_orani)})"
        )


def raporu_yazdir(rapor) -> None:
    ayarlar = rapor.yapilandirma

    print()
    print("=" * SATIR_GENISLIGI)
    print("HİSSE ROBOTU — PİYASA REJİMİ VE PERFORMANS RAPORU")
    print("=" * SATIR_GENISLIGI)
    print(f"Sembol                         : {rapor.sembol}")
    print(
        "Sınıflandırma dönemi           : "
        f"{tarih(rapor.ilk_rejim_tarihi)} — "
        f"{tarih(rapor.son_rejim_tarihi)}"
    )
    print(
        "Sınıflandırılan işlem günü     : "
        f"{rapor.siniflandirilan_gun_sayisi}"
    )
    print(
        "İşlem sınıflandırma            : "
        f"{rapor.siniflandirilan_islem_sayisi} / "
        f"{rapor.toplam_islem_sayisi} "
        f"({yuzde(rapor.siniflandirma_orani)})"
    )
    print(
        "Sınıflandırılamayan işlem      : "
        f"{rapor.siniflandirilamayan_islem_sayisi}"
    )
    print()
    print("REJİM KURALLARI")
    print("-" * SATIR_GENISLIGI)
    print(
        "Trend                         : "
        f"Kapanış, EMA{ayarlar.hizli_ema_periyodu}, "
        f"EMA{ayarlar.yavas_ema_periyodu}, "
        f"{ayarlar.egim_bakisi} bar hızlı EMA eğimi"
    )
    print(
        "Minimum EMA farkı             : "
        f"{yuzde(ayarlar.minimum_ema_farki_orani)}"
    )
    print(
        "Volatilite                    : "
        f"ATR{ayarlar.atr_periyodu}/fiyat; "
        f"{ayarlar.volatilite_bakisi} günlük hareketli medyan"
    )
    print(
        "Yüksek volatilite eşiği       : "
        f"Medyan × {ayarlar.yuksek_volatilite_carpani:.2f}"
    )
    print(
        "İşlem rejimi tarihi           : Sinyal günü; "
        "gelecek fiyat kullanılmaz."
    )

    gun_dagilimi_yazdir(
        "TREND REJİMİ GÜN DAĞILIMI",
        rapor.trend_gun_dagilimi,
    )
    gun_dagilimi_yazdir(
        "VOLATİLİTE REJİMİ GÜN DAĞILIMI",
        rapor.volatilite_gun_dagilimi,
    )
    performans_tablosu_yazdir(
        "TREND REJİMİ BAZLI PERFORMANS",
        rapor.trend_performanslari,
    )
    performans_tablosu_yazdir(
        "VOLATİLİTE REJİMİ BAZLI PERFORMANS",
        rapor.volatilite_performanslari,
    )
    performans_tablosu_yazdir(
        "BİRLEŞİK REJİM BAZLI PERFORMANS",
        rapor.birlesik_performanslar,
    )

    print()
    print("REJİM ÖZETİ")
    print("-" * SATIR_GENISLIGI)

    if rapor.en_iyi_birlesik_rejim is not None:
        print(
            "En güçlü birleşik rejim       : "
            f"{rapor.en_iyi_birlesik_rejim.rejim_adi} / "
            f"{yuzde(rapor.en_iyi_birlesik_rejim.toplam_net_getiri_orani)}"
        )

    if rapor.en_zayif_birlesik_rejim is not None:
        print(
            "En zayıf birleşik rejim       : "
            f"{rapor.en_zayif_birlesik_rejim.rejim_adi} / "
            f"{yuzde(rapor.en_zayif_birlesik_rejim.toplam_net_getiri_orani)}"
        )

    print("=" * SATIR_GENISLIGI)
    print(
        "Not: Rejimler sabit ve açıklanabilir kurallarla belirlenir. "
        "Rapor, belirli rejimde işlem açmayı otomatik olarak önermez "
        "ve geçmişe göre parametre optimizasyonu yapmaz."
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
        rejim_ayari = MarketRegimeConfig(
            hizli_ema_periyodu=argumanlar.hizli_ema,
            yavas_ema_periyodu=argumanlar.yavas_ema,
            egim_bakisi=argumanlar.egim_bakisi,
            minimum_ema_farki_orani=(
                argumanlar.minimum_ema_farki_yuzde / 100.0
            ),
            atr_periyodu=argumanlar.atr_periyodu,
            volatilite_bakisi=argumanlar.volatilite_bakisi,
            yuksek_volatilite_carpani=(
                argumanlar.yuksek_volatilite_carpani
            ),
        )

        print()
        print(
            f"{sembol} için piyasa rejimi analizi "
            "başlatılıyor..."
        )
        print(
            "Fiyat verisi ve tarihsel sinyaller hazırlanacak; "
            "tamamlanan işlemler sinyal gününün rejimine atanacak."
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
        ham_sonuc = BacktestEngine().calistir(
            veriler={sembol: fiyat_verisi},
            sinyaller=sinyal_uretimi.sinyaller,
            yapilandirma=backtest_ayari,
        )
        sonuc = cakisan_islemleri_filtrele(
            sonuc=ham_sonuc,
            yapilandirma=backtest_ayari,
        )
        rapor = MarketRegimeAnalyzer().analiz_et(
            sembol=sembol,
            fiyat_verisi=fiyat_verisi,
            islemler=sonuc.islemler,
            backtest_yapilandirmasi=backtest_ayari,
            yapilandirma=rejim_ayari,
        )
        raporu_yazdir(rapor)

    except (
        ValueError,
        MarketDataError,
        StockAnalyzerError,
        HistoricalSignalGeneratorError,
        BacktestEngineError,
        MarketRegimeAnalysisError,
    ) as hata:
        print(f"\nHATA: {hata}")


if __name__ == "__main__":
    main()
