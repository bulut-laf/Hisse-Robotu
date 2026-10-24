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
from app.backtest.portfolio_backtest import PortfolioBacktestError
from app.backtest.portfolio_risk_comparison import (
    PortfolioRiskComparisonAnalyzer,
)
from app.backtest.position_overlap import cakisan_islemleri_filtrele
from app.data.market_data import MarketDataError, fiyat_verisi_getir


SATIR_GENISLIGI = 176


def argumanlari_al() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Sabit portföy sermaye dağılımını stop mesafesine göre risk "
            "bazlı pozisyon büyüklüğüyle karşılaştırır."
        )
    )
    parser.add_argument("semboller", nargs="+", help="Örnek: THYAO TUPRS ASELS")
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
    parser.add_argument("--islem-riski-yuzde", type=float, default=1.0)
    parser.add_argument("--toplam-risk-yuzde", type=float, default=2.0)
    parser.add_argument(
        "--pozisyon-tavan-yuzde",
        type=float,
        default=None,
        help=(
            "Tek pozisyona ayrılabilecek azami özsermaye yüzdesi. "
            "Belirtilmezse 100 / maksimum pozisyon kullanılır."
        ),
    )
    return parser.parse_args()


def yuzde(oran: float) -> str:
    return f"{oran * 100:.2f}%"


def para(deger: float) -> str:
    return f"{deger:,.2f}"


def sayi(deger: float | None) -> str:
    return "-" if deger is None else f"{deger:.2f}"


def veri_kimligi(veri_kimlikleri: dict[str, str]) -> str:
    icerik = "|".join(
        f"{sembol}:{veri_kimlikleri[sembol]}"
        for sembol in sorted(veri_kimlikleri)
    ).encode("utf-8")
    return sha256(icerik).hexdigest()[:12]


def raporu_yazdir(rapor, semboller, profil, veri_kimlikleri) -> None:
    sabit = rapor.sabit
    risk = rapor.risk_bazli
    risk_ayar = risk.yapilandirma

    print()
    print("=" * SATIR_GENISLIGI)
    print("HİSSE ROBOTU — PORTFÖY RİSK LİMİTİ VE POZİSYON BÜYÜKLÜĞÜ RAPORU")
    print("=" * SATIR_GENISLIGI)
    print(f"Semboller                     : {', '.join(semboller)}")
    print(f"Ayar kimliği                  : {profil.ayar_kimligi}")
    print(f"Portföy veri kimliği          : {veri_kimligi(veri_kimlikleri)}")
    print(f"Maksimum eş zamanlı pozisyon  : {risk_ayar.maksimum_es_zamanli_pozisyon}")
    print(
        "Pozisyon sermaye tavanı     : "
        f"{yuzde(float(risk_ayar.pozisyon_basina_sermaye_orani))}"
    )
    print(f"Zarar durdur mesafesi         : {yuzde(float(risk_ayar.zarar_durdur_orani))}")
    print(f"İşlem başına risk bütçesi     : {yuzde(float(risk_ayar.islem_basina_risk_orani))}")
    print(f"Toplam açık portföy riski     : {yuzde(float(risk_ayar.toplam_acik_risk_orani))}")

    print()
    print("SABİT SERMAYE — RİSK BAZLI KARŞILAŞTIRMA")
    print("-" * SATIR_GENISLIGI)
    print(
        f"{'Ölçüt':<46}"
        f"{'Sabit Sermaye':>24}"
        f"{'Risk Bazlı':>24}"
        f"{'Fark':>24}"
    )
    print("-" * SATIR_GENISLIGI)

    satirlar = (
        (
            "Tamamlanan işlem",
            str(sabit.rapor.tamamlanan_islem_sayisi),
            str(risk.rapor.tamamlanan_islem_sayisi),
            str(risk.rapor.tamamlanan_islem_sayisi - sabit.rapor.tamamlanan_islem_sayisi),
        ),
        (
            "Atlanan işlem",
            str(sabit.rapor.atlanan_islem_sayisi),
            str(risk.rapor.atlanan_islem_sayisi),
            str(risk.rapor.atlanan_islem_sayisi - sabit.rapor.atlanan_islem_sayisi),
        ),
        (
            "Bitiş sermayesi",
            para(sabit.rapor.bitis_sermayesi),
            para(risk.rapor.bitis_sermayesi),
            para(risk.rapor.bitis_sermayesi - sabit.rapor.bitis_sermayesi),
        ),
        (
            "Toplam getiri",
            yuzde(sabit.rapor.toplam_getiri_orani),
            yuzde(risk.rapor.toplam_getiri_orani),
            yuzde(rapor.getiri_farki),
        ),
        (
            "Günlük maksimum düşüş",
            yuzde(sabit.rapor.maksimum_dusus_orani),
            yuzde(risk.rapor.maksimum_dusus_orani),
            yuzde(rapor.maksimum_dusus_farki),
        ),
        (
            "Kâr faktörü",
            sayi(sabit.rapor.kar_faktoru),
            sayi(risk.rapor.kar_faktoru),
            "",
        ),
        (
            "Getiri / maksimum düşüş",
            sayi(sabit.getiri_dusus_orani),
            sayi(risk.getiri_dusus_orani),
            "",
        ),
        (
            "Ortalama sermaye kullanımı",
            yuzde(sabit.rapor.ortalama_sermaye_kullanim_orani),
            yuzde(risk.rapor.ortalama_sermaye_kullanim_orani),
            "",
        ),
        (
            "Maks. günlük risk / güncel özsermaye",
            yuzde(sabit.rapor.maksimum_acik_risk_orani),
            yuzde(risk.rapor.maksimum_acik_risk_orani),
            "",
        ),
        (
            "Maks. giriş risk limiti kullanımı",
            "-",
            yuzde(
                risk.rapor.maksimum_giris_risk_limiti_kullanim_orani
            ),
            "",
        ),
    )

    for baslik, sabit_deger, risk_deger, fark in satirlar:
        print(
            f"{baslik:<46}"
            f"{sabit_deger:>24}"
            f"{risk_deger:>24}"
            f"{fark:>24}"
        )

    print()
    print("RİSK BAZLI SENARYODA ATLANAN İŞLEMLER")
    print("-" * SATIR_GENISLIGI)
    if not risk.atlanma_nedenleri:
        print("Atlanan işlem yok.")
    else:
        for neden, adet in risk.atlanma_nedenleri:
            print(f"{neden:<70}: {adet}")

    print("=" * SATIR_GENISLIGI)
    print(
        "Not: Risk bazlı pozisyon büyüklüğü, işlem başına risk bütçesinin "
        "maliyet dahil stop kaybına bölünmesiyle hesaplanır. Pozisyon sermaye "
        "tavanını veya yeni işlem kabul anındaki toplam açık risk sınırını "
        "aşamaz; kaldıraç kullanılmaz. Günlük risk / güncel özsermaye oranı, "
        "özsermaye sonradan gerilerse girişteki sınırın biraz üzerine çıkabilir; "
        "bu durum yeni işlem kabulünde limit ihlali olduğu anlamına gelmez."
    )


def main() -> None:
    argumanlar = argumanlari_al()

    try:
        semboller = tuple(
            dict.fromkeys(sembolu_hazirla(sembol) for sembol in argumanlar.semboller)
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
        print(f"{len(semboller)} hisse için portföy risk karşılaştırması başlatılıyor...")
        print(
            "Fiyat verileri ve tek-hisse işlemleri bir kez hazırlanacak; "
            "sabit ve risk bazlı senaryolar aynı aday havuzuyla çalışacak."
        )

        fiyat_verileri = {}
        veri_kimlikleri: dict[str, str] = {}
        tum_islemler = []
        analizci = StockAnalyzer()
        sinyal_ureticisi = HistoricalSignalGenerator(analizci.veriden_analiz_et)
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
            baglam = analiz_baglamini_olustur(fiyat_verisi=fiyat_verisi, profil=profil)
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

        rapor = PortfolioRiskComparisonAnalyzer().analiz_et(
            fiyat_verileri=fiyat_verileri,
            islemler=tum_islemler,
            baslangic_sermayesi=argumanlar.sermaye,
            maksimum_es_zamanli_pozisyon=argumanlar.maks_pozisyon,
            islem_maliyeti_orani=argumanlar.maliyet_yuzde / 100.0,
            zarar_durdur_orani=argumanlar.stop_yuzde / 100.0,
            islem_basina_risk_orani=argumanlar.islem_riski_yuzde / 100.0,
            toplam_acik_risk_orani=argumanlar.toplam_risk_yuzde / 100.0,
            maksimum_pozisyon_sermaye_orani=(
                argumanlar.pozisyon_tavan_yuzde / 100.0
                if argumanlar.pozisyon_tavan_yuzde is not None
                else None
            ),
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
    ) as hata:
        print(f"\nHATA: {hata}")


if __name__ == "__main__":
    main()
