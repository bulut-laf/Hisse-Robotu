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
from app.backtest.portfolio_backtest import (
    PortfolioBacktestAnalyzer,
    PortfolioBacktestConfig,
    PortfolioBacktestError,
)
from app.backtest.position_overlap import cakisan_islemleri_filtrele
from app.data.market_data import MarketDataError, fiyat_verisi_getir


SATIR_GENISLIGI = 158


def argumanlari_al() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Birden fazla BIST hissesini ortak sermaye, pozisyon sınırı "
            "ve günlük mark-to-market özsermaye ile backtest eder."
        )
    )
    parser.add_argument(
        "semboller",
        nargs="+",
        help="Örnek: THYAO TUPRS ASELS",
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
    parser.add_argument("--maks-pozisyon", type=int, default=3)
    parser.add_argument(
        "--pozisyon-yuzde",
        type=float,
        default=None,
        help=(
            "Her portföy pozisyonuna ayrılacak özsermaye yüzdesi. "
            "Belirtilmezse 100 / maksimum pozisyon kullanılır."
        ),
    )
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
    portfoy_ayarlari: PortfolioBacktestConfig,
) -> None:
    print()
    print("=" * SATIR_GENISLIGI)
    print("HİSSE ROBOTU — ÇOKLU HİSSE PORTFÖY BACKTEST RAPORU")
    print("=" * SATIR_GENISLIGI)
    print(f"Semboller                     : {', '.join(semboller)}")
    print(f"Ayar kimliği                  : {profil.ayar_kimligi}")
    print(f"Portföy veri kimliği          : {portfoy_veri_kimligi(veri_kimlikleri)}")
    print(
        "Portföy dönemi               : "
        f"{rapor.ilk_tarih or '-'} — {rapor.son_tarih or '-'}"
    )

    print()
    print("PORTFÖY AYARLARI")
    print("-" * SATIR_GENISLIGI)
    print(f"Başlangıç sermayesi           : {para(rapor.baslangic_sermayesi)}")
    print(
        "Maksimum eş zamanlı pozisyon : "
        f"{portfoy_ayarlari.maksimum_es_zamanli_pozisyon}"
    )
    print(
        "Pozisyon başına sermaye      : "
        f"{yuzde(float(portfoy_ayarlari.pozisyon_basina_sermaye_orani))}"
    )
    print(
        "İşlem maliyeti               : "
        f"{yuzde(portfoy_ayarlari.islem_maliyeti_orani)} alış + satış"
    )
    print("Aynı gün aday önceliği        : Yüksek skor, sonra sembol")
    print("Çıkış günü sermaye kullanımı  : Ertesi işlem gününden itibaren")

    print()
    print("PORTFÖY PERFORMANSI")
    print("-" * SATIR_GENISLIGI)
    print(f"Tamamlanan işlem              : {rapor.tamamlanan_islem_sayisi}")
    print(f"Portföy nedeniyle atlanan     : {rapor.atlanan_islem_sayisi}")
    print(f"Bitiş sermayesi               : {para(rapor.bitis_sermayesi)}")
    print(f"Toplam getiri                 : {yuzde(rapor.toplam_getiri_orani)}")
    print(f"Günlük maksimum düşüş         : {yuzde(rapor.maksimum_dusus_orani)}")
    print(f"Güncel düşüş                  : {yuzde(rapor.guncel_dusus_orani)}")
    print(f"Kâr faktörü                   : {sayi(rapor.kar_faktoru)}")
    print(
        "Gerçekleşen maks. pozisyon   : "
        f"{rapor.maksimum_es_zamanli_pozisyon}"
    )
    print(
        "Ortalama sermaye kullanımı   : "
        f"{yuzde(rapor.ortalama_sermaye_kullanim_orani)}"
    )
    print(
        "Maksimum sermaye kullanımı   : "
        f"{yuzde(rapor.maksimum_sermaye_kullanim_orani)}"
    )

    print()
    print("HİSSE BAZLI KATKI")
    print("-" * SATIR_GENISLIGI)
    print(
        f"{'Sembol':<14}"
        f"{'İşlem':>8}"
        f"{'Kazanma':>12}"
        f"{'Ayrılan Sermaye':>20}"
        f"{'Net Kâr':>18}"
        f"{'Başlangıca Katkı':>20}"
    )
    print("-" * SATIR_GENISLIGI)

    for katki in rapor.sembol_katkilari:
        print(
            f"{katki.sembol:<14}"
            f"{katki.islem_sayisi:>8}"
            f"{yuzde(katki.kazanma_orani):>12}"
            f"{para(katki.toplam_ayrilan_sermaye):>20}"
            f"{para(katki.net_kar):>18}"
            f"{yuzde(katki.baslangic_sermayesine_katki_orani):>20}"
        )

    if rapor.atlanan_islemler:
        neden_sayilari: dict[str, int] = {}
        for atlanan in rapor.atlanan_islemler:
            neden_sayilari[atlanan.neden] = (
                neden_sayilari.get(atlanan.neden, 0) + 1
            )

        print()
        print("PORTFÖY NEDENİYLE ATLANAN İŞLEMLER")
        print("-" * SATIR_GENISLIGI)
        for neden, adet in sorted(neden_sayilari.items()):
            print(f"{neden:<60}: {adet}")

        print()
        print("İlk atlanan örnekler:")
        for atlanan in rapor.atlanan_islemler[:5]:
            islem = atlanan.islem
            print(
                f"- {islem.giris_tarihi} {islem.sembol} "
                f"(skor {islem.skor}): {atlanan.neden}"
            )

    print("=" * SATIR_GENISLIGI)
    print(
        "Not: Portföy motoru kaldıraç kullanmaz. Aynı gün başlayan "
        "adaylar yüksek skordan düşüğe sıralanır; çıkış günündeki nakit "
        "aynı gün yeni girişe aktarılmaz."
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
        pozisyon_orani = (
            argumanlar.pozisyon_yuzde / 100.0
            if argumanlar.pozisyon_yuzde is not None
            else None
        )
        portfoy_ayarlari = PortfolioBacktestConfig(
            baslangic_sermayesi=argumanlar.sermaye,
            maksimum_es_zamanli_pozisyon=argumanlar.maks_pozisyon,
            pozisyon_basina_sermaye_orani=pozisyon_orani,
            islem_maliyeti_orani=argumanlar.maliyet_yuzde / 100.0,
        )

        print()
        print(
            f"{len(semboller)} hisse için portföy backtest’i başlatılıyor..."
        )
        print(
            "Her hissenin geçmiş sinyalleri aynı ortak profil ile "
            "hazırlanacak; ardından tek sermaye altında birleştirilecek."
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

        rapor = PortfolioBacktestAnalyzer().analiz_et(
            fiyat_verileri=fiyat_verileri,
            islemler=tum_islemler,
            yapilandirma=portfoy_ayarlari,
        )
        raporu_yazdir(
            rapor=rapor,
            semboller=semboller,
            profil=profil,
            veri_kimlikleri=veri_kimlikleri,
            portfoy_ayarlari=portfoy_ayarlari,
        )

    except (
        ValueError,
        MarketDataError,
        StockAnalyzerError,
        HistoricalSignalGeneratorError,
        BacktestEngineError,
        PortfolioBacktestError,
    ) as hata:
        print(f"\nHATA: {hata}")


if __name__ == "__main__":
    main()
