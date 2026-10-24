from __future__ import annotations

import argparse
from datetime import date

from app.analysis.scan_filter import (
    NEGATIF_GORUNUM,
    NOTR_GORUNUM,
    POZITIF_GORUNUM,
    TUM_GORUNUMLER,
)
from app.backtest.analysis_profile import (
    AnalysisProfile,
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
)
from app.backtest.backtest_engine import (
    SkippedSignal,
)
from app.backtest.backtest_service import (
    GECERLI_INDIRME_DONEMLERI,
    BacktestServiceConfig,
    BacktestServiceError,
    StockBacktestReport,
    StockBacktestService,
)
from app.backtest.position_overlap import (
    CAKISMA_NEDENI,
)


SATIR_GENISLIGI = 150
ATLANAN_ORNEK_SAYISI = 3
ETIKET_GENISLIGI = 29


def tarih_argumani(
    metin: str,
) -> date:
    try:
        return date.fromisoformat(
            metin
        )

    except ValueError as hata:
        raise argparse.ArgumentTypeError(
            "Tarih YYYY-AA-GG biçiminde olmalıdır."
        ) from hata


def argumanlari_al() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Gerçek geçmiş piyasa verisi üzerinde "
            "Hisse Robotu backtest çalıştırır."
        )
    )

    parser.add_argument(
        "sembol",
        help=(
            "Backtest uygulanacak hisse sembolü. "
            "Örnek: THYAO veya THYAO.IS"
        ),
    )

    parser.add_argument(
        "--islem-gunu",
        type=int,
        default=ORTAK_ISLEM_GUNU,
        help=(
            "İndirilecek en fazla işlem günü. "
            f"Varsayılan: {ORTAK_ISLEM_GUNU}"
        ),
    )

    parser.add_argument(
        "--donem",
        choices=GECERLI_INDIRME_DONEMLERI,
        default=ORTAK_INDIRME_DONEMI,
        help=(
            "Veri indirme dönemi. "
            f"Varsayılan: {ORTAK_INDIRME_DONEMI}"
        ),
    )

    parser.add_argument(
        "--minimum-bar",
        type=int,
        default=ORTAK_MINIMUM_BAR,
        help=(
            "İlk sinyalden önce gereken minimum "
            "fiyat barı. Varsayılan: 60"
        ),
    )

    parser.add_argument(
        "--baslangic",
        type=tarih_argumani,
        default=None,
        help=(
            "Sinyal başlangıç tarihi. "
            "Biçim: YYYY-AA-GG"
        ),
    )

    parser.add_argument(
        "--bitis",
        type=tarih_argumani,
        default=None,
        help=(
            "Sinyal bitiş tarihi. "
            "Biçim: YYYY-AA-GG"
        ),
    )

    parser.add_argument(
        "--gorunum",
        choices=(
            "tum",
            "pozitif",
            "notr",
            "negatif",
            "pozitif-notr",
        ),
        default=ORTAK_GORUNUM_SECIMI,
        help=(
            "Backtest’e alınacak teknik görünüm. "
            f"Varsayılan: {ORTAK_GORUNUM_SECIMI}"
        ),
    )

    parser.add_argument(
        "--elde-tutma",
        type=int,
        default=ORTAK_ELDE_TUTMA_GUNU,
        help=(
            "İşlemin en fazla açık kalacağı bar sayısı. "
            f"Varsayılan: {ORTAK_ELDE_TUTMA_GUNU}"
        ),
    )

    parser.add_argument(
        "--min-skor",
        type=int,
        default=ORTAK_MINIMUM_SKOR,
        help=(
            "İşleme alınacak minimum sinyal skoru. "
            f"Varsayılan: {ORTAK_MINIMUM_SKOR}"
        ),
    )

    parser.add_argument(
        "--sermaye",
        type=float,
        default=ORTAK_BASLANGIC_SERMAYESI,
        help=(
            "Başlangıç sermayesi. "
            f"Varsayılan: {ORTAK_BASLANGIC_SERMAYESI:.0f}"
        ),
    )

    parser.add_argument(
        "--pozisyon-yuzde",
        type=float,
        default=ORTAK_POZISYON_YUZDE,
        help=(
            "Her işlemde kullanılan sermaye yüzdesi. "
            f"Varsayılan: {ORTAK_POZISYON_YUZDE:g}"
        ),
    )

    parser.add_argument(
        "--maliyet-yuzde",
        type=float,
        default=ORTAK_MALIYET_YUZDE,
        help=(
            "Alış ve satışta ayrı ayrı uygulanan "
            f"işlem maliyeti yüzdesi. Varsayılan: {ORTAK_MALIYET_YUZDE:g}"
        ),
    )

    parser.add_argument(
        "--stop-yuzde",
        type=float,
        default=ORTAK_STOP_YUZDE,
        help=(
            "Sabit zarar durdur yüzdesi. "
            f"Varsayılan: {ORTAK_STOP_YUZDE:g}"
        ),
    )

    parser.add_argument(
        "--hedef-yuzde",
        type=float,
        default=ORTAK_HEDEF_YUZDE,
        help=(
            "Sabit hedef yüzdesi. "
            f"Varsayılan: {ORTAK_HEDEF_YUZDE:g}"
        ),
    )

    parser.add_argument(
        "--islem-goster",
        type=int,
        default=20,
        help=(
            "Ekranda gösterilecek işlem sayısı. "
            "Varsayılan: 20"
        ),
    )

    return parser.parse_args()


def gorunumleri_coz(
    secim: str,
) -> tuple[str, ...]:
    donusumler = {
        "tum": TUM_GORUNUMLER,
        "pozitif": (
            POZITIF_GORUNUM,
        ),
        "notr": (
            NOTR_GORUNUM,
        ),
        "negatif": (
            NEGATIF_GORUNUM,
        ),
        "pozitif-notr": (
            POZITIF_GORUNUM,
            NOTR_GORUNUM,
        ),
    }

    return donusumler[secim]


def yuzdeyi_orana_cevir(
    deger: float | None,
) -> float | None:
    if deger is None:
        return None

    return deger / 100.0


def yapilandirma_olustur(
    argumanlar: argparse.Namespace,
) -> BacktestServiceConfig:
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

    return BacktestServiceConfig(
        islem_gunu=profil.islem_gunu,
        indirme_donemi=profil.indirme_donemi,
        yalnizca_tamamlanmis_gunler=True,
        pozisyon_cakismalarini_engelle=True,
        sinyal_ayarlari=profil.sinyal_yapilandirmasi(
            baslangic_tarihi=argumanlar.baslangic,
            bitis_tarihi=argumanlar.bitis,
        ),
        backtest_ayarlari=profil.backtest_yapilandirmasi(),
    )


def oran_yuzde_metni(
    oran: float,
) -> str:
    return f"{oran * 100:.2f}%"


def opsiyonel_oran_metni(
    oran: float | None,
) -> str:
    if oran is None:
        return "-"

    return oran_yuzde_metni(
        oran
    )


def opsiyonel_sayi_metni(
    deger: float | None,
) -> str:
    if deger is None:
        return "-"

    return f"{deger:.2f}"


def para_metni(
    deger: float,
) -> str:
    return f"{deger:,.2f}"


def etiket_yazdir(
    etiket: str,
    deger: object,
) -> None:
    print(
        f"{etiket:<{ETIKET_GENISLIGI}}: {deger}"
    )


def skor_nedeni_mi(
    neden: str,
) -> bool:
    temiz_neden = neden.casefold()

    return (
        "sinyal skoru" in temiz_neden
        and "minimum" in temiz_neden
    )


def atlanan_sinyalleri_ayir(
    rapor: StockBacktestReport,
) -> tuple[
    tuple[SkippedSignal, ...],
    tuple[SkippedSignal, ...],
    tuple[SkippedSignal, ...],
]:
    atlananlar = (
        rapor.backtest_sonucu
        .atlanan_sinyaller
    )

    skor_nedeniyle_atlananlar = tuple(
        atlanan
        for atlanan in atlananlar
        if (
            CAKISMA_NEDENI
            not in atlanan.neden
            and skor_nedeni_mi(
                atlanan.neden
            )
        )
    )

    cakisma_nedeniyle_atlananlar = tuple(
        atlanan
        for atlanan in atlananlar
        if CAKISMA_NEDENI in atlanan.neden
    )

    diger_nedenlerle_atlananlar = tuple(
        atlanan
        for atlanan in atlananlar
        if (
            atlanan
            not in skor_nedeniyle_atlananlar
            and atlanan
            not in cakisma_nedeniyle_atlananlar
        )
    )

    return (
        skor_nedeniyle_atlananlar,
        cakisma_nedeniyle_atlananlar,
        diger_nedenlerle_atlananlar,
    )


def atlanan_grubu_yazdir(
    baslik: str,
    kayitlar: tuple[
        SkippedSignal,
        ...,
    ],
) -> None:
    if not kayitlar:
        return

    print()
    print(baslik)

    for atlanan in kayitlar[
        :ATLANAN_ORNEK_SAYISI
    ]:
        print(
            f"- {atlanan.sinyal.sinyal_tarihi}: "
            f"{atlanan.neden}"
        )

    if len(kayitlar) > ATLANAN_ORNEK_SAYISI:
        print(
            f"  İlk {ATLANAN_ORNEK_SAYISI} kayıt "
            f"gösterildi. Toplam: {len(kayitlar)}"
        )


def yillik_performansi_yazdir(
    rapor: StockBacktestReport,
) -> None:
    dagilim = rapor.performans_dagilimi
    yillik_performanslar = (
        dagilim.yillik_performanslar
    )

    print()
    print("YILLIK PERFORMANS")
    print("-" * SATIR_GENISLIGI)

    if not yillik_performanslar:
        print(
            "Yıllık performans oluşturacak "
            "tamamlanmış işlem bulunamadı."
        )
        return

    print(
        f"{'Yıl':<7}"
        f"{'İşlem':>8}"
        f"{'Kazanan':>10}"
        f"{'Kaybeden':>11}"
        f"{'Kazanma':>11}"
        f"{'Ort. Net':>12}"
        f"{'Bileşik':>12}"
        f"{'Kâr F.':>10}"
        f"{'Yıl Başı':>17}"
        f"{'Yıl Sonu':>17}"
    )

    print("-" * SATIR_GENISLIGI)

    for performans in yillik_performanslar:
        print(
            f"{performans.yil:<7}"
            f"{performans.islem_sayisi:>8}"
            f"{performans.kazanan_islem_sayisi:>10}"
            f"{performans.kaybeden_islem_sayisi:>11}"
            f"{oran_yuzde_metni(performans.kazanma_orani):>11}"
            f"{oran_yuzde_metni(performans.ortalama_net_getiri_orani):>12}"
            f"{oran_yuzde_metni(performans.bilesik_getiri_orani):>12}"
            f"{opsiyonel_sayi_metni(performans.kar_faktoru):>10}"
            f"{para_metni(performans.yil_basi_sermayesi):>17}"
            f"{para_metni(performans.yil_sonu_sermayesi):>17}"
        )

    print()

    if dagilim.en_karli_yil is not None:
        etiket_yazdir(
            "En kârlı yıl",
            (
                f"{dagilim.en_karli_yil.yil} "
                f"({oran_yuzde_metni(dagilim.en_karli_yil.bilesik_getiri_orani)})"
            ),
        )

    if dagilim.en_zararli_yil is not None:
        etiket_yazdir(
            "En zayıf yıl",
            (
                f"{dagilim.en_zararli_yil.yil} "
                f"({oran_yuzde_metni(dagilim.en_zararli_yil.bilesik_getiri_orani)})"
            ),
        )


def cikis_nedeni_analizini_yazdir(
    rapor: StockBacktestReport,
) -> None:
    performanslar = (
        rapor.performans_dagilimi
        .cikis_nedeni_performanslari
    )

    print()
    print("ÇIKIŞ NEDENİ ANALİZİ")
    print("-" * SATIR_GENISLIGI)

    if not performanslar:
        print(
            "Çıkış nedeni analizi oluşturacak "
            "tamamlanmış işlem bulunamadı."
        )
        return

    print(
        f"{'Çıkış Nedeni':<25}"
        f"{'İşlem':>9}"
        f"{'Pay':>10}"
        f"{'Kazanan':>10}"
        f"{'Kaybeden':>11}"
        f"{'Kazanma':>11}"
        f"{'Ort. Net':>12}"
        f"{'Bileşik':>12}"
    )

    print("-" * SATIR_GENISLIGI)

    for performans in performanslar:
        print(
            f"{performans.cikis_nedeni:<25}"
            f"{performans.islem_sayisi:>9}"
            f"{oran_yuzde_metni(performans.toplam_islem_orani):>10}"
            f"{performans.kazanan_islem_sayisi:>10}"
            f"{performans.kaybeden_islem_sayisi:>11}"
            f"{oran_yuzde_metni(performans.kazanma_orani):>11}"
            f"{oran_yuzde_metni(performans.ortalama_net_getiri_orani):>12}"
            f"{oran_yuzde_metni(performans.bilesik_getiri_orani):>12}"
        )


def opsiyonel_tarih_metni(
    tarih: date | None,
) -> str:
    if tarih is None:
        return "-"

    return tarih.isoformat()


def ozsermaye_ve_dusus_analizini_yazdir(
    rapor: StockBacktestReport,
) -> None:
    ozsermaye = rapor.ozsermaye_raporu

    print()
    print("ÖZSERMAYE VE DÜŞÜŞ ANALİZİ")
    print("-" * SATIR_GENISLIGI)

    etiket_yazdir(
        "Özsermaye noktası",
        ozsermaye.islem_sayisi,
    )

    etiket_yazdir(
        "Başlangıç sermayesi",
        para_metni(
            ozsermaye.baslangic_sermayesi
        ),
    )

    etiket_yazdir(
        "Son özsermaye",
        para_metni(
            ozsermaye.bitis_sermayesi
        ),
    )

    etiket_yazdir(
        "Toplam bileşik getiri",
        oran_yuzde_metni(
            ozsermaye
            .toplam_bilesik_getiri_orani
        ),
    )

    if not ozsermaye.noktalar:
        print(
            "Düşüş analizi oluşturacak tamamlanmış "
            "işlem bulunamadı."
        )
        return

    son_nokta = ozsermaye.noktalar[-1]

    etiket_yazdir(
        "Son özsermaye tarihi",
        son_nokta.tarih.isoformat(),
    )

    etiket_yazdir(
        "Güncel zirve sermayesi",
        para_metni(
            son_nokta.zirve_sermayesi
        ),
    )

    etiket_yazdir(
        "Güncel düşüş",
        oran_yuzde_metni(
            son_nokta.dusus_orani
        ),
    )

    maksimum = (
        ozsermaye.maksimum_dusus_donemi
    )

    if maksimum is None:
        etiket_yazdir(
            "Maksimum düşüş",
            "0.00%",
        )
        etiket_yazdir(
            "Düşüş dönemi sayısı",
            0,
        )

    else:
        etiket_yazdir(
            "Maksimum düşüş",
            oran_yuzde_metni(
                maksimum.dusus_orani
            ),
        )

        etiket_yazdir(
            "Maks. düşüş zirvesi",
            (
                f"{maksimum.zirve_tarihi.isoformat()} / "
                f"{para_metni(maksimum.zirve_sermayesi)}"
            ),
        )

        etiket_yazdir(
            "Maks. düşüş dibi",
            (
                f"{maksimum.dip_tarihi.isoformat()} / "
                f"{para_metni(maksimum.dip_sermayesi)}"
            ),
        )

        etiket_yazdir(
            "Maks. düşüş toparlanması",
            opsiyonel_tarih_metni(
                maksimum.toparlanma_tarihi
            ),
        )

        etiket_yazdir(
            "Maks. zirve altında süre",
            (
                f"{maksimum.zirve_altinda_gun_sayisi} "
                "takvim günü"
            ),
        )

        etiket_yazdir(
            "Maks. düşüş durumu",
            (
                "Toparlandı"
                if maksimum.toparlandi_mi
                else "Açık — henüz toparlanmadı"
            ),
        )

        etiket_yazdir(
            "Düşüş dönemi sayısı",
            ozsermaye.dusus_donemi_sayisi,
        )

    en_uzun = (
        ozsermaye.en_uzun_dusus_donemi
    )

    if en_uzun is not None:
        etiket_yazdir(
            "En uzun düşüş süresi",
            (
                f"{en_uzun.zirve_altinda_gun_sayisi} "
                "takvim günü"
            ),
        )

        etiket_yazdir(
            "En uzun dönem zirvesi",
            (
                f"{en_uzun.zirve_tarihi.isoformat()} / "
                f"{para_metni(en_uzun.zirve_sermayesi)}"
            ),
        )

        etiket_yazdir(
            "En uzun dönem dibi",
            (
                f"{en_uzun.dip_tarihi.isoformat()} / "
                f"{para_metni(en_uzun.dip_sermayesi)}"
            ),
        )

        etiket_yazdir(
            "En uzun dönem toparlanması",
            opsiyonel_tarih_metni(
                en_uzun.toparlanma_tarihi
            ),
        )

        etiket_yazdir(
            "En uzun dönem durumu",
            (
                "Toparlandı"
                if en_uzun.toparlandi_mi
                else "Açık — henüz toparlanmadı"
            ),
        )



def gunluk_mark_to_market_analizini_yazdir(
    rapor: StockBacktestReport,
) -> None:
    gunluk = rapor.gunluk_ozsermaye_raporu

    print()
    print("GÜNLÜK MARK-TO-MARKET RİSK ANALİZİ")
    print("-" * SATIR_GENISLIGI)

    if gunluk is None:
        print(
            "Pozisyon çakışma filtresi kapalı olduğu için "
            "günlük özsermaye analizi üretilmedi."
        )
        return

    if not gunluk.noktalar:
        print(
            "Günlük özsermaye analizi oluşturacak "
            "tamamlanmış işlem bulunamadı."
        )
        return

    etiket_yazdir(
        "Analiz dönemi",
        (
            f"{gunluk.baslangic_tarihi.isoformat()} — "
            f"{gunluk.bitis_tarihi.isoformat()}"
        ),
    )

    etiket_yazdir(
        "Günlük özsermaye noktası",
        gunluk.islem_gunu_sayisi,
    )

    etiket_yazdir(
        "Başlangıç sermayesi",
        para_metni(gunluk.baslangic_sermayesi),
    )

    etiket_yazdir(
        "Son özsermaye",
        para_metni(gunluk.bitis_sermayesi),
    )

    etiket_yazdir(
        "Toplam bileşik getiri",
        oran_yuzde_metni(
            gunluk.toplam_bilesik_getiri_orani
        ),
    )

    son_nokta = gunluk.noktalar[-1]

    etiket_yazdir(
        "Güncel zirve sermayesi",
        para_metni(son_nokta.zirve_sermayesi),
    )

    etiket_yazdir(
        "Güncel düşüş",
        oran_yuzde_metni(
            gunluk.guncel_dusus_orani
        ),
    )

    maksimum = gunluk.maksimum_dusus_donemi

    if maksimum is None:
        etiket_yazdir(
            "Günlük maksimum düşüş",
            "0.00%",
        )
        etiket_yazdir(
            "Düşüş dönemi sayısı",
            0,
        )
        return

    etiket_yazdir(
        "Günlük maksimum düşüş",
        oran_yuzde_metni(
            maksimum.dusus_orani
        ),
    )

    etiket_yazdir(
        "Maks. düşüş zirvesi",
        (
            f"{maksimum.zirve_tarihi.isoformat()} / "
            f"{para_metni(maksimum.zirve_sermayesi)}"
        ),
    )

    etiket_yazdir(
        "Maks. düşüş dibi",
        (
            f"{maksimum.dip_tarihi.isoformat()} / "
            f"{para_metni(maksimum.dip_sermayesi)}"
        ),
    )

    etiket_yazdir(
        "Maks. düşüş toparlanması",
        opsiyonel_tarih_metni(
            maksimum.toparlanma_tarihi
        ),
    )

    etiket_yazdir(
        "Maks. zirve altında süre",
        (
            f"{maksimum.zirve_altinda_gun_sayisi} "
            "takvim günü"
        ),
    )

    etiket_yazdir(
        "Maks. düşüş durumu",
        (
            "Toparlandı"
            if maksimum.toparlandi_mi
            else "Açık — henüz toparlanmadı"
        ),
    )

    etiket_yazdir(
        "Düşüş dönemi sayısı",
        gunluk.dusus_donemi_sayisi,
    )

    en_uzun = gunluk.en_uzun_dusus_donemi

    if en_uzun is not None:
        etiket_yazdir(
            "En uzun düşüş süresi",
            (
                f"{en_uzun.zirve_altinda_gun_sayisi} "
                "takvim günü"
            ),
        )


def al_tut_detaylarini_yazdir(
    baslik: str,
    benchmark: object,
) -> None:
    al_tut = benchmark.al_tut

    print()
    print(baslik)
    print("-" * SATIR_GENISLIGI)

    etiket_yazdir(
        "Karşılaştırma dönemi",
        (
            f"{al_tut.baslangic_tarihi.isoformat()} — "
            f"{al_tut.bitis_tarihi.isoformat()}"
        ),
    )

    etiket_yazdir(
        "Takvim günü",
        al_tut.takvim_gunu_sayisi,
    )

    etiket_yazdir(
        "Al-Tut giriş fiyatı",
        f"{al_tut.giris_fiyati:.2f}",
    )

    etiket_yazdir(
        "Al-Tut çıkış fiyatı",
        f"{al_tut.cikis_fiyati:.2f}",
    )

    etiket_yazdir(
        "Al-Tut brüt getiri",
        oran_yuzde_metni(
            al_tut.brut_getiri_orani
        ),
    )

    etiket_yazdir(
        "Al-Tut net getiri",
        oran_yuzde_metni(
            al_tut.net_getiri_orani
        ),
    )

    etiket_yazdir(
        "Al-Tut yıllık getiri",
        oran_yuzde_metni(
            al_tut
            .yilliklandirilmis_getiri_orani
        ),
    )

    etiket_yazdir(
        "Al-Tut başlangıç sermayesi",
        para_metni(
            al_tut.baslangic_sermayesi
        ),
    )

    etiket_yazdir(
        "Al-Tut bitiş sermayesi",
        para_metni(
            al_tut.bitis_sermayesi
        ),
    )

    etiket_yazdir(
        "Al-Tut maksimum düşüş",
        oran_yuzde_metni(
            al_tut.maksimum_dusus_orani
        ),
    )

    etiket_yazdir(
        "Al-Tut düşüş zirvesi",
        (
            al_tut
            .maksimum_dusus_zirve_tarihi
            .isoformat()
        ),
    )

    etiket_yazdir(
        "Al-Tut düşüş dibi",
        (
            al_tut
            .maksimum_dusus_dip_tarihi
            .isoformat()
        ),
    )

    etiket_yazdir(
        "Al-Tut toparlanma",
        opsiyonel_tarih_metni(
            al_tut
            .maksimum_dusus_toparlanma_tarihi
        ),
    )

    etiket_yazdir(
        "Al-Tut güncel düşüş",
        oran_yuzde_metni(
            al_tut.guncel_dusus_orani
        ),
    )


def strateji_al_tut_ozetini_yazdir(
    benchmark: object,
) -> None:
    karsilastirma = benchmark.karsilastirma

    print()
    print("HİZALANMIŞ STRATEJİ VE AL-TUT ÖZETİ")
    print("-" * SATIR_GENISLIGI)

    print(
        f"{'Ölçüt':<36}"
        f"{'Strateji':>20}"
        f"{'Al-Tut':>20}"
    )

    print("-" * SATIR_GENISLIGI)

    print(
        f"{'Toplam net getiri':<36}"
        f"{oran_yuzde_metni(karsilastirma.strateji_toplam_getiri_orani):>20}"
        f"{oran_yuzde_metni(karsilastirma.al_tut_toplam_getiri_orani):>20}"
    )

    print(
        f"{'Yıllıklandırılmış getiri':<36}"
        f"{oran_yuzde_metni(karsilastirma.strateji_yilliklandirilmis_getiri_orani):>20}"
        f"{oran_yuzde_metni(karsilastirma.al_tut_yilliklandirilmis_getiri_orani):>20}"
    )

    print(
        f"{'Maksimum düşüş (günlük)':<36}"
        f"{oran_yuzde_metni(karsilastirma.strateji_maksimum_dusus_orani):>20}"
        f"{oran_yuzde_metni(karsilastirma.al_tut_maksimum_dusus_orani):>20}"
    )

    print(
        f"{'Getiri / maksimum düşüş':<36}"
        f"{opsiyonel_sayi_metni(karsilastirma.strateji_getiri_dusus_orani):>20}"
        f"{opsiyonel_sayi_metni(karsilastirma.al_tut_getiri_dusus_orani):>20}"
    )

    print(
        f"{'Yıllık getiri / maksimum düşüş':<36}"
        f"{opsiyonel_sayi_metni(karsilastirma.strateji_yillik_getiri_dusus_orani):>20}"
        f"{opsiyonel_sayi_metni(karsilastirma.al_tut_yillik_getiri_dusus_orani):>20}"
    )

    print()

    etiket_yazdir(
        "Stratejinin fazla getirisi",
        oran_yuzde_metni(
            karsilastirma.fazla_getiri_orani
        ),
    )

    etiket_yazdir(
        "Toplam getiri lideri",
        karsilastirma.toplam_getiri_lideri,
    )

    etiket_yazdir(
        "Risk düzeltilmiş lider",
        karsilastirma.risk_duzeltilmis_lider,
    )


def benchmark_karsilastirmasini_yazdir(
    rapor: StockBacktestReport,
) -> None:
    tam_donem = (
        rapor.benchmark_karsilastirmasi
    )

    hizalanmis = (
        rapor
        .hizalanmis_benchmark_karsilastirmasi
    )

    print()
    print("STRATEJİ — AL-TUT KARŞILAŞTIRMASI")
    print("=" * SATIR_GENISLIGI)

    al_tut_detaylarini_yazdir(
        baslik="TAM VERİ DÖNEMİ AL-TUT REFERANSI",
        benchmark=tam_donem,
    )

    if hizalanmis is None:
        print()
        print("ADİL DÖNEM KARŞILAŞTIRMASI")
        print("-" * SATIR_GENISLIGI)
        print(
            "Tamamlanmış işlem bulunmadığı için "
            "ilk giriş ve son çıkış tarihleriyle "
            "hizalanmış karşılaştırma üretilemedi."
        )
        return

    al_tut_detaylarini_yazdir(
        baslik=(
            "ADİL DÖNEM AL-TUT PERFORMANSI "
            "(İLK GİRİŞ — SON ÇIKIŞ)"
        ),
        benchmark=hizalanmis,
    )

    strateji_al_tut_ozetini_yazdir(
        hizalanmis
    )

def raporu_yazdir(
    rapor: StockBacktestReport,
    yapilandirma: BacktestServiceConfig,
    islem_goster: int,
) -> None:
    sinyal_ayarlari = (
        yapilandirma.sinyal_ayarlari
    )

    backtest_ayarlari = (
        yapilandirma.backtest_ayarlari
    )

    sonuc = rapor.backtest_sonucu
    metrikler = sonuc.metrikler

    (
        skor_nedeniyle_atlananlar,
        cakisma_nedeniyle_atlananlar,
        diger_nedenlerle_atlananlar,
    ) = atlanan_sinyalleri_ayir(
        rapor
    )

    cakisma_filtresi_metni = (
        "Aktif"
        if yapilandirma
        .pozisyon_cakismalarini_engelle
        else "Kapalı"
    )

    print()
    print("=" * SATIR_GENISLIGI)
    print("HİSSE ROBOTU — GERÇEK VERİ BACKTEST RAPORU")
    print("=" * SATIR_GENISLIGI)

    etiket_yazdir(
        "Sembol",
        rapor.sembol,
    )

    etiket_yazdir(
        "Fiyat tarihi",
        (
            f"{rapor.ilk_fiyat_tarihi} — "
            f"{rapor.son_fiyat_tarihi}"
        ),
    )

    etiket_yazdir(
        "Fiyat barı",
        rapor.fiyat_bar_sayisi,
    )

    if rapor.analiz_baglami is not None:
        etiket_yazdir(
            "Analiz kimliği",
            rapor.analiz_baglami.analiz_kimligi,
        )
        etiket_yazdir(
            "Veri kimliği",
            rapor.analiz_baglami.veri_kimligi,
        )
        etiket_yazdir(
            "Ayar kimliği",
            rapor.analiz_baglami.ayar_kimligi,
        )

    print()
    print("BACKTEST AYARLARI")
    print("-" * SATIR_GENISLIGI)

    etiket_yazdir(
        "Minimum analiz barı",
        sinyal_ayarlari.minimum_bar_sayisi,
    )

    etiket_yazdir(
        "Teknik görünüm",
        ", ".join(
            sinyal_ayarlari
            .izin_verilen_gorunumler
        ),
    )

    etiket_yazdir(
        "Minimum sinyal skoru",
        backtest_ayarlari.minimum_skor,
    )

    etiket_yazdir(
        "Elde tutma süresi",
        (
            f"{backtest_ayarlari.elde_tutma_gunu} "
            "bar"
        ),
    )

    etiket_yazdir(
        "Pozisyon oranı",
        oran_yuzde_metni(
            backtest_ayarlari.pozisyon_orani
        ),
    )

    etiket_yazdir(
        "İşlem maliyeti",
        (
            oran_yuzde_metni(
                backtest_ayarlari
                .islem_maliyeti_orani
            )
            + " alış + satış"
        ),
    )

    etiket_yazdir(
        "Zarar durdur",
        opsiyonel_oran_metni(
            backtest_ayarlari
            .zarar_durdur_orani
        ),
    )

    etiket_yazdir(
        "Hedef",
        opsiyonel_oran_metni(
            backtest_ayarlari.hedef_orani
        ),
    )

    etiket_yazdir(
        "Pozisyon çakışma filtresi",
        cakisma_filtresi_metni,
    )

    print()
    print("SİNYAL ÜRETİMİ")
    print("-" * SATIR_GENISLIGI)

    etiket_yazdir(
        "Değerlendirilen gün",
        (
            rapor.sinyal_uretimi
            .degerlendirilen_gun_sayisi
        ),
    )

    etiket_yazdir(
        "Üretilen sinyal",
        rapor.uretilen_sinyal_sayisi,
    )

    etiket_yazdir(
        "Analizde atlanan gün",
        rapor.analizde_atlanan_gun_sayisi,
    )

    etiket_yazdir(
        "Motorun atladığı sinyal",
        sonuc.atlanan_sinyal_sayisi,
    )

    etiket_yazdir(
        "Skor nedeniyle atlanan",
        len(
            skor_nedeniyle_atlananlar
        ),
    )

    etiket_yazdir(
        "Çakışma nedeniyle atlanan",
        len(
            cakisma_nedeniyle_atlananlar
        ),
    )

    etiket_yazdir(
        "Diğer nedenle atlanan",
        len(
            diger_nedenlerle_atlananlar
        ),
    )

    print()
    print("GENEL PERFORMANS")
    print("-" * SATIR_GENISLIGI)

    etiket_yazdir(
        "Tamamlanan işlem",
        metrikler.islem_sayisi,
    )

    etiket_yazdir(
        "Kazanan işlem",
        metrikler.kazanan_islem_sayisi,
    )

    etiket_yazdir(
        "Kaybeden işlem",
        metrikler.kaybeden_islem_sayisi,
    )

    etiket_yazdir(
        "Başabaş işlem",
        metrikler.basabas_islem_sayisi,
    )

    etiket_yazdir(
        "Kazanma oranı",
        oran_yuzde_metni(
            metrikler.kazanma_orani
        ),
    )

    etiket_yazdir(
        "Ortalama net getiri",
        oran_yuzde_metni(
            metrikler
            .ortalama_net_getiri_orani
        ),
    )

    etiket_yazdir(
        "Toplam bileşik getiri",
        oran_yuzde_metni(
            metrikler.toplam_net_getiri_orani
        ),
    )

    etiket_yazdir(
        "Başlangıç sermayesi",
        para_metni(
            metrikler.baslangic_sermayesi
        ),
    )

    etiket_yazdir(
        "Bitiş sermayesi",
        para_metni(
            metrikler.bitis_sermayesi
        ),
    )

    etiket_yazdir(
        "En iyi işlem",
        opsiyonel_oran_metni(
            metrikler.en_iyi_islem_orani
        ),
    )

    etiket_yazdir(
        "En kötü işlem",
        opsiyonel_oran_metni(
            metrikler.en_kotu_islem_orani
        ),
    )

    etiket_yazdir(
        "Kâr faktörü",
        opsiyonel_sayi_metni(
            metrikler.kar_faktoru
        ),
    )

    etiket_yazdir(
        "Maks. ardışık kayıp",
        metrikler.maksimum_ardisik_kayip,
    )

    yillik_performansi_yazdir(
        rapor
    )

    cikis_nedeni_analizini_yazdir(
        rapor
    )

    ozsermaye_ve_dusus_analizini_yazdir(
        rapor
    )

    gunluk_mark_to_market_analizini_yazdir(
        rapor
    )

    benchmark_karsilastirmasini_yazdir(
        rapor
    )

    islemler = sonuc.islemler

    print()
    print("İŞLEM AYRINTILARI")
    print("-" * SATIR_GENISLIGI)

    if not islemler:
        print(
            "Filtre koşullarına uygun tamamlanmış "
            "işlem bulunamadı."
        )

    else:
        print(
            f"{'No':<5}"
            f"{'Sinyal':<13}"
            f"{'Giriş':<13}"
            f"{'Çıkış':<13}"
            f"{'Skor':>7}"
            f"{'Giriş F.':>12}"
            f"{'Çıkış F.':>12}"
            f"{'Net':>10}"
            f"{'Bar':>7}"
            f"{'Çıkış Nedeni':>20}"
        )

        print("-" * SATIR_GENISLIGI)

        gosterilecek_islemler = islemler[
            :islem_goster
        ]

        for sira, islem in enumerate(
            gosterilecek_islemler,
            start=1,
        ):
            print(
                f"{sira:<5}"
                f"{islem.sinyal_tarihi.isoformat():<13}"
                f"{islem.giris_tarihi.isoformat():<13}"
                f"{islem.cikis_tarihi.isoformat():<13}"
                f"{islem.skor:>7}"
                f"{islem.giris_fiyati:>12.2f}"
                f"{islem.cikis_fiyati:>12.2f}"
                f"{oran_yuzde_metni(islem.net_getiri_orani):>10}"
                f"{islem.elde_tutulan_bar:>7}"
                f"{islem.cikis_nedeni:>20}"
            )

        if len(islemler) > islem_goster:
            print()
            print(
                f"İlk {islem_goster} işlem gösterildi. "
                f"Toplam işlem: {len(islemler)}"
            )

    if sonuc.atlanan_sinyaller:
        print()
        print("ATLANAN SİNYAL ÖRNEKLERİ")
        print("-" * SATIR_GENISLIGI)

        atlanan_grubu_yazdir(
            baslik=(
                "Skor nedeniyle atlanan sinyaller:"
            ),
            kayitlar=(
                skor_nedeniyle_atlananlar
            ),
        )

        atlanan_grubu_yazdir(
            baslik=(
                "Çakışma nedeniyle atlanan sinyaller:"
            ),
            kayitlar=(
                cakisma_nedeniyle_atlananlar
            ),
        )

        atlanan_grubu_yazdir(
            baslik=(
                "Diğer nedenlerle atlanan sinyaller:"
            ),
            kayitlar=(
                diger_nedenlerle_atlananlar
            ),
        )

    print()
    print("=" * SATIR_GENISLIGI)

    if (
        yapilandirma
        .pozisyon_cakismalarini_engelle
    ):
        print(
            "Not: Pozisyon çakışma filtresi aktiftir. "
            "Aynı sembolde açık pozisyon varken oluşan "
            "yeni sinyaller işleme alınmaz."
        )
        print(
            "Yıllık performans, işlemlerin çıkış yılına "
            "göre sınıflandırılmıştır."
        )
        print(
            "Bileşik performans yalnızca kabul edilen "
            "ve tarih sırasına göre tamamlanan işlemler "
            "üzerinden hesaplanır."
        )
        print(
            "Düşüş analizi tamamlanan işlemler sonrası "
            "özsermaye noktalarına dayanır; açık işlem "
            "içi fiyat dalgalanmalarını içermez."
        )
        print(
            "Tam dönem Al-Tut referansı veri setinin "
            "ilk ve son fiyat günlerini kullanır."
        )
        print(
            "Adil dönem karşılaştırması ilk kabul edilen "
            "işlem girişinden son kabul edilen işlem "
            "çıkışına kadar hizalanır."
        )
        print(
            "Tamamlanan işlem özsermaye analizi yalnızca "
            "işlem kapanışlarını gösterir."
        )
        print(
            "Günlük mark-to-market analizinde açık pozisyonlar "
            "kapanış fiyatıyla, gerçek çıkış günleri backtest "
            "çıkış fiyatıyla değerlenir."
        )
        print(
            "Hizalanmış risk karşılaştırmasında strateji ve "
            "Al-Tut maksimum düşüşleri günlük fiyat noktalarına "
            "dayanır."
        )

    else:
        print(
            "Not: Pozisyon çakışma filtresi kapalıdır. "
            "Her sinyal bağımsız işlem olarak hesaplanır."
        )

    print("=" * SATIR_GENISLIGI)


def main() -> None:
    argumanlar = argumanlari_al()

    try:
        if argumanlar.islem_goster <= 0:
            raise ValueError(
                "Gösterilecek işlem sayısı "
                "pozitif olmalıdır."
            )

        yapilandirma = yapilandirma_olustur(
            argumanlar
        )

        print()
        print(
            f"{argumanlar.sembol.upper()} için "
            "gerçek veri backtest’i başlatılıyor..."
        )
        print(
            "Geçmiş günler tek tek analiz edildiği "
            "için işlem biraz sürebilir."
        )

        rapor = StockBacktestService().calistir(
            sembol=argumanlar.sembol,
            yapilandirma=yapilandirma,
        )

        raporu_yazdir(
            rapor=rapor,
            yapilandirma=yapilandirma,
            islem_goster=(
                argumanlar.islem_goster
            ),
        )

    except (
        ValueError,
        BacktestServiceError,
    ) as hata:
        print(f"\nHATA: {hata}")


if __name__ == "__main__":
    main()