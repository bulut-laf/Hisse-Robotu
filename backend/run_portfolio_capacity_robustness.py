from __future__ import annotations

import argparse
from collections import Counter
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
from app.backtest.portfolio_capacity_robustness import (
    PIYASA_GUCLU,
    PIYASA_NOTR,
    PIYASA_ZAYIF,
    PortfolioCapacityRobustnessAnalyzer,
    PortfolioCapacityRobustnessError,
)
from app.backtest.portfolio_capacity_sensitivity import (
    PortfolioCapacitySensitivityError,
)
from app.backtest.position_overlap import cakisan_islemleri_filtrele
from app.data.market_data import MarketDataError, fiyat_verisi_getir


SATIR_GENISLIGI = 176


def argumanlari_al() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Portföy kapasitesi 1/2/3 sonuçlarını kayan zaman pencereleri "
            "ve bir-hisse-dışarıda senaryolarıyla sağlamlık açısından "
            "karşılaştırır."
        )
    )
    parser.add_argument("semboller", nargs="+", help="Örnek: THYAO TUPRS ASELS")
    parser.add_argument(
        "--kapasiteler",
        nargs="+",
        type=int,
        default=[1, 2, 3],
        help="Karşılaştırılacak eş zamanlı pozisyon sayıları.",
    )
    parser.add_argument(
        "--pencere-bar",
        type=int,
        default=252,
        help="Kayan pencere uzunluğu. Varsayılan: 252 bar.",
    )
    parser.add_argument(
        "--adim-bar",
        type=int,
        default=63,
        help="Kayan pencere adımı. Varsayılan: 63 bar.",
    )
    parser.add_argument(
        "--minimum-islem",
        type=int,
        default=10,
        help="Bir pencerenin rapora alınması için gereken aday işlem.",
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


def yuzde(oran: float | None) -> str:
    if oran is None:
        return "-"
    return f"{oran * 100:.2f}%"


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


def grup_lider_sayilari(rapor, grup: str) -> tuple[int, Counter, Counter]:
    pencereler = tuple(
        pencere for pencere in rapor.pencereler if pencere.piyasa_grubu == grup
    )
    getiri = Counter(
        pencere.getiri_lideri
        for pencere in pencereler
        if pencere.getiri_lideri is not None
    )
    risk = Counter(
        pencere.getiri_dusus_lideri
        for pencere in pencereler
        if pencere.getiri_dusus_lideri is not None
    )
    return len(pencereler), getiri, risk


def lider_metni(sayac: Counter) -> str:
    if not sayac:
        return "-"
    sirali = sorted(sayac.items(), key=lambda oge: (-oge[1], oge[0]))
    return ", ".join(f"K{kapasite}:{adet}" for kapasite, adet in sirali)


def senaryo_kapasite_getirileri(senaryo) -> str:
    return " | ".join(
        f"K{s.kapasite} {yuzde(s.rapor.toplam_getiri_orani)}"
        for s in senaryo.kapasite_raporu.senaryolar
    )


def raporu_yazdir(
    rapor,
    semboller: tuple[str, ...],
    profil: AnalysisProfile,
    veri_kimlikleri: dict[str, str],
) -> None:
    print()
    print("=" * SATIR_GENISLIGI)
    print("HİSSE ROBOTU — PORTFÖY KAPASİTESİ SAĞLAMLIK RAPORU")
    print("=" * SATIR_GENISLIGI)
    print(f"Semboller                     : {', '.join(semboller)}")
    print(f"Ayar kimliği                  : {profil.ayar_kimligi}")
    print(f"Portföy veri kimliği          : {portfoy_veri_kimligi(veri_kimlikleri)}")
    print(f"Pencere / adım                : {rapor.pencere_bar_sayisi} / {rapor.adim_bar_sayisi} bar")
    print(f"Minimum aday işlem            : {rapor.minimum_islem_sayisi}")
    print(f"Yeterli kayan pencere         : {len(rapor.pencereler)}")
    print(f"Piyasa pencere medyan getirisi: {yuzde(rapor.piyasa_getiri_medyan_orani)}")

    print()
    print("KAYAN PENCERE SONUÇLARI")
    print("-" * SATIR_GENISLIGI)
    print(
        f"{'No':>3} {'Başlangıç':<12} {'Bitiş':<12} {'Piyasa':>11} "
        f"{'Grup':<7} {'Aday':>6} {'Getiri Lideri':>14} {'Getiri/DD Lideri':>18}"
    )
    print("-" * SATIR_GENISLIGI)
    for sira, pencere in enumerate(rapor.pencereler, start=1):
        print(
            f"{sira:>3} {pencere.baslangic_tarihi.isoformat():<12} "
            f"{pencere.bitis_tarihi.isoformat():<12} "
            f"{yuzde(pencere.piyasa_getiri_orani):>11} "
            f"{pencere.piyasa_grubu:<7} "
            f"{pencere.aday_islem_sayisi:>6} "
            f"{('K' + str(pencere.getiri_lideri)) if pencere.getiri_lideri else '-':>14} "
            f"{('K' + str(pencere.getiri_dusus_lideri)) if pencere.getiri_dusus_lideri else '-':>18}"
        )

    print()
    print("KAPASİTE PENCERE ÖZETİ")
    print("-" * SATIR_GENISLIGI)
    print(
        f"{'Kapasite':>9}{'Pencere':>10}{'Pozitif':>11}{'Getiri Lideri':>16}"
        f"{'Getiri/DD Lideri':>19}{'Medyan Getiri':>16}{'Medyan DD':>13}{'Medyan Getiri/DD':>19}"
    )
    print("-" * SATIR_GENISLIGI)
    for ozet in rapor.kapasite_ozetleri:
        print(
            f"{ozet.kapasite:>9}{ozet.pencere_sayisi:>10}"
            f"{yuzde(ozet.pozitif_pencere_orani):>11}"
            f"{ozet.getiri_liderligi_sayisi:>16}"
            f"{ozet.getiri_dusus_liderligi_sayisi:>19}"
            f"{yuzde(ozet.medyan_getiri_orani):>16}"
            f"{yuzde(ozet.medyan_maksimum_dusus_orani):>13}"
            f"{sayi(ozet.medyan_getiri_dusus_orani):>19}"
        )

    print()
    print("GÜÇLÜ / ZAYIF PİYASA PENCERELERİ")
    print("-" * SATIR_GENISLIGI)
    for grup in (PIYASA_GUCLU, PIYASA_ZAYIF, PIYASA_NOTR):
        adet, getiri_sayaci, risk_sayaci = grup_lider_sayilari(rapor, grup)
        print(
            f"{grup:<7} | Pencere: {adet:>2} | "
            f"Getiri liderliği: {lider_metni(getiri_sayaci):<20} | "
            f"Getiri/DD liderliği: {lider_metni(risk_sayaci)}"
        )

    print()
    print("BİR HİSSE DIŞARIDA SAĞLAMLIK KONTROLÜ")
    print("-" * SATIR_GENISLIGI)
    for senaryo in rapor.sembol_dislamalari:
        dislanan = senaryo.dislanan_sembol or "Yok (tam sepet)"
        print(
            f"Dışlanan: {dislanan:<16} | Aday: {senaryo.aday_islem_sayisi:>3} | "
            f"Getiri lideri: K{senaryo.getiri_lideri or '-'} | "
            f"Getiri/DD lideri: K{senaryo.getiri_dusus_lideri or '-'} | "
            f"{senaryo_kapasite_getirileri(senaryo)}"
        )

    print("=" * SATIR_GENISLIGI)
    print(
        "Not: Kayan pencereler yalnızca giriş ve çıkışı tamamen pencere "
        "içinde kalan işlemleri kullanır. Güçlü/Zayıf etiketi, pencerenin "
        "eşit ağırlıklı gerçekleşmiş hisse getirisinin pencere medyanına "
        "göre konumudur; işlem filtresi veya gelecek tahmini değildir. "
        "Kapasite otomatik olarak optimize edilmez."
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
        print(
            f"{len(semboller)} hisse için portföy kapasitesi "
            "sağlamlık analizi başlatılıyor..."
        )
        print(
            "Fiyat verileri ve tarihsel işlemler bir kez hazırlanacak; "
            "kayan pencereler ve sembol dışlama senaryoları aynı aday "
            "havuzundan üretilecek."
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

        rapor = PortfolioCapacityRobustnessAnalyzer().analiz_et(
            fiyat_verileri=fiyat_verileri,
            islemler=tum_islemler,
            kapasiteler=argumanlar.kapasiteler,
            pencere_bar_sayisi=argumanlar.pencere_bar,
            adim_bar_sayisi=argumanlar.adim_bar,
            minimum_islem_sayisi=argumanlar.minimum_islem,
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
        PortfolioCapacityRobustnessError,
    ) as hata:
        print(f"\nHATA: {hata}")


if __name__ == "__main__":
    main()
