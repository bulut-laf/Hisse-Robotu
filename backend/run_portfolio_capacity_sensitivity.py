from __future__ import annotations

import argparse
from hashlib import sha256

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
    ORTAK_STOP_YUZDE,
    sembolu_hazirla,
)
from app.backtest.backtest_engine import BacktestEngine, BacktestEngineError
from app.backtest.historical_signal_generator import (
    HistoricalSignalGenerator,
    HistoricalSignalGeneratorError,
)
from app.backtest.portfolio_capacity_sensitivity import (
    PortfolioCapacitySensitivityAnalyzer,
    PortfolioCapacitySensitivityError,
)
from app.backtest.portfolio_backtest import PortfolioBacktestError
from app.backtest.position_overlap import cakisan_islemleri_filtrele
from app.data.market_data import MarketDataError, fiyat_verisi_getir


SATIR_GENISLIGI = 170


def argumanlari_al() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Aynı çoklu-hisse veri ve işlemleriyle farklı portföy "
            "kapasitelerinin getiri, düşüş ve sermaye kullanımını "
            "karşılaştırır."
        )
    )
    parser.add_argument(
        "semboller",
        nargs="+",
        help="Örnek: THYAO TUPRS ASELS",
    )
    parser.add_argument(
        "--kapasiteler",
        nargs="+",
        type=int,
        default=[1, 2, 3],
        help="Karşılaştırılacak eş zamanlı pozisyon sayıları.",
    )
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
    parser.add_argument("--maliyet-yuzde", type=float, default=ORTAK_MALIYET_YUZDE)
    parser.add_argument("--stop-yuzde", type=float, default=ORTAK_STOP_YUZDE)
    parser.add_argument("--hedef-yuzde", type=float, default=ORTAK_HEDEF_YUZDE)
    return parser.parse_args()


def yuzde(oran: float) -> str:
    return f"{oran * 100:.2f}%"


def para(deger: float) -> str:
    return f"{deger:,.2f}"


def sayi(deger: float | None) -> str:
    if deger is None:
        return "-"

    return f"{deger:.2f}"


def portfoy_veri_kimligi(veri_kimlikleri: dict[str, str]) -> str:
    icerik = "|".join(
        f"{sembol}:{veri_kimlikleri[sembol]}"
        for sembol in sorted(veri_kimlikleri)
    ).encode("utf-8")
    return sha256(icerik).hexdigest()[:12]


def raporu_yazdir(
    rapor,
    semboller: tuple[str, ...],
    profil: AnalysisProfile,
    veri_kimlikleri: dict[str, str],
) -> None:
    print()
    print("=" * SATIR_GENISLIGI)
    print("HİSSE ROBOTU — PORTFÖY KAPASİTESİ DUYARLILIK RAPORU")
    print("=" * SATIR_GENISLIGI)
    print(f"Semboller                     : {', '.join(semboller)}")
    print(f"Ayar kimliği                  : {profil.ayar_kimligi}")
    print(f"Portföy veri kimliği          : {portfoy_veri_kimligi(veri_kimlikleri)}")
    print(
        "Karşılaştırılan kapasite     : "
        + ", ".join(str(senaryo.kapasite) for senaryo in rapor.senaryolar)
    )

    print()
    print("KAPASİTE KARŞILAŞTIRMASI")
    print("-" * SATIR_GENISLIGI)
    print(
        f"{'Kapasite':>10}"
        f"{'Pozisyon Payı':>16}"
        f"{'İşlem':>10}"
        f"{'Atlanan':>10}"
        f"{'Bitiş Sermayesi':>20}"
        f"{'Toplam Getiri':>16}"
        f"{'Maks. Düşüş':>14}"
        f"{'Kâr F.':>10}"
        f"{'Getiri/DD':>12}"
        f"{'Ort. Kullanım':>16}"
        f"{'Maks. Kullanım':>17}"
    )
    print("-" * SATIR_GENISLIGI)

    for senaryo in rapor.senaryolar:
        sonuc = senaryo.rapor
        print(
            f"{senaryo.kapasite:>10}"
            f"{yuzde(senaryo.pozisyon_basina_sermaye_orani):>16}"
            f"{sonuc.tamamlanan_islem_sayisi:>10}"
            f"{sonuc.atlanan_islem_sayisi:>10}"
            f"{para(sonuc.bitis_sermayesi):>20}"
            f"{yuzde(sonuc.toplam_getiri_orani):>16}"
            f"{yuzde(sonuc.maksimum_dusus_orani):>14}"
            f"{sayi(sonuc.kar_faktoru):>10}"
            f"{sayi(senaryo.getiri_dusus_orani):>12}"
            f"{yuzde(sonuc.ortalama_sermaye_kullanim_orani):>16}"
            f"{yuzde(sonuc.maksimum_sermaye_kullanim_orani):>17}"
        )

    print()
    print("ÖZET")
    print("-" * SATIR_GENISLIGI)
    en_yuksek = rapor.en_yuksek_getiri_senaryosu
    en_dusuk = rapor.en_dusuk_dusus_senaryosu
    en_iyi_oran = rapor.en_iyi_getiri_dusus_senaryosu
    print(
        "En yüksek toplam getiri      : "
        f"Kapasite {en_yuksek.kapasite} "
        f"({yuzde(en_yuksek.rapor.toplam_getiri_orani)})"
    )
    print(
        "En düşük maksimum düşüş      : "
        f"Kapasite {en_dusuk.kapasite} "
        f"({yuzde(en_dusuk.rapor.maksimum_dusus_orani)})"
    )
    print(
        "En iyi getiri / düşüş        : "
        + (
            f"Kapasite {en_iyi_oran.kapasite} "
            f"({sayi(en_iyi_oran.getiri_dusus_orani)})"
            if en_iyi_oran is not None
            else "Hesaplanamadı"
        )
    )
    print("=" * SATIR_GENISLIGI)
    print(
        "Not: Her kapasite aynı fiyat verisi, aynı sinyaller ve aynı "
        "tek-hisse işlemleriyle çalışır. Pozisyon payı otomatik olarak "
        "1 / kapasite seçilir; kaldıraç kullanılmaz ve geçmişe göre "
        "kapasite optimizasyonu yapılmaz."
    )


def main() -> None:
    argumanlar = argumanlari_al()

    try:
        semboller = tuple(
            dict.fromkeys(
                sembolu_hazirla(sembol)
                for sembol in argumanlar.semboller
            )
        )
        profil = AnalysisProfile(
            islem_gunu=argumanlar.islem_gunu,
            indirme_donemi=argumanlar.donem,
            minimum_bar_sayisi=argumanlar.minimum_bar,
            gorunum_secimi=argumanlar.gorunum,
            elde_tutma_gunu=argumanlar.elde_tutma,
            minimum_skor=argumanlar.min_skor,
            baslangic_sermayesi=argumanlar.sermaye,
            pozisyon_yuzde=100.0,
            maliyet_yuzde=argumanlar.maliyet_yuzde,
            stop_yuzde=argumanlar.stop_yuzde,
            hedef_yuzde=argumanlar.hedef_yuzde,
        )

        print()
        print(
            f"{len(semboller)} hisse için portföy kapasitesi "
            "duyarlılık analizi başlatılıyor..."
        )
        print(
            "Fiyat verileri ve tarihsel işlemler bir kez hazırlanacak; "
            "tüm kapasiteler aynı aday havuzuyla karşılaştırılacak."
        )

        fiyat_verileri = {}
        veri_kimlikleri: dict[str, str] = {}
        tum_islemler = []
        analizci = StockAnalyzer()
        sinyal_ureticisi = HistoricalSignalGenerator(
            analizci.veriden_analiz_et
        )
        backtest_motoru = BacktestEngine()
        tek_hisse_ayarlari = profil.backtest_yapilandirmasi()

        for sira, sembol in enumerate(semboller, start=1):
            print(f"[{sira}/{len(semboller)}] {sembol} hazırlanıyor...")
            fiyat_verisi = fiyat_verisi_getir(
                sembol=sembol,
                islem_gunu=profil.islem_gunu,
                indirme_donemi=profil.indirme_donemi,
                yalnizca_tamamlanmis_gunler=True,
            )
            baglam = analiz_baglamini_olustur(
                fiyat_verisi=fiyat_verisi,
                profil=profil,
            )
            sinyal_uretimi = sinyal_ureticisi.uret(
                sembol=sembol,
                fiyat_verisi=fiyat_verisi,
                yapilandirma=profil.sinyal_yapilandirmasi(),
            )
            ham_sonuc = backtest_motoru.calistir(
                veriler={sembol: fiyat_verisi},
                sinyaller=sinyal_uretimi.sinyaller,
                yapilandirma=tek_hisse_ayarlari,
            )
            sonuc = cakisan_islemleri_filtrele(
                sonuc=ham_sonuc,
                yapilandirma=tek_hisse_ayarlari,
            )
            fiyat_verileri[sembol] = fiyat_verisi
            veri_kimlikleri[sembol] = baglam.veri_kimligi
            tum_islemler.extend(sonuc.islemler)
            print(
                f"    {len(sinyal_uretimi.sinyaller)} sinyal / "
                f"{len(sonuc.islemler)} tek-hisse işlemi"
            )

        rapor = PortfolioCapacitySensitivityAnalyzer().analiz_et(
            fiyat_verileri=fiyat_verileri,
            islemler=tum_islemler,
            kapasiteler=argumanlar.kapasiteler,
            baslangic_sermayesi=argumanlar.sermaye,
            islem_maliyeti_orani=argumanlar.maliyet_yuzde / 100.0,
        )
        raporu_yazdir(
            rapor=rapor,
            semboller=semboller,
            profil=profil,
            veri_kimlikleri=veri_kimlikleri,
        )

    except (
        ValueError,
        MarketDataError,
        StockAnalyzerError,
        HistoricalSignalGeneratorError,
        BacktestEngineError,
        PortfolioBacktestError,
        PortfolioCapacitySensitivityError,
    ) as hata:
        print(f"\nHATA: {hata}")


if __name__ == "__main__":
    main()
