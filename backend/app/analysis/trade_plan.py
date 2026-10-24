from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import math

from ..data.multi_timeframe_data import (
    GUNLUK,
    MultiTimeframeDataBundle,
)
from ..indicators.technical_indicators import (
    IndicatorError,
    teknik_gostergeleri_ekle,
)
from .technical_confirmation import (
    NEGATIF,
    NOTR,
    POZITIF,
    TEYITLI_ASAGI_KIRILIM,
    TEYITLI_YUKARI_KIRILIM,
    MultiTimeframeTechnicalConfirmation,
    TechnicalConfirmationError,
    teknik_teyit_analizi_yap,
)


ISLEM_VAR = "İşlem Var"
ISLEM_YOK = "İşlem Yok"
ONAYLI_ALIM_PLANI = "Onaylı Alım Planı"
KOSULLU_ALIM_PLANI = "Koşullu Alım Planı"
PLAN_OLUSTURULMADI = "Plan Oluşturulmadı"


class TradePlanError(Exception):
    """Güncel alış-satış işlem planı üretilemediğinde kullanılır."""


@dataclass(frozen=True)
class PositionSizeResult:
    """Sermaye ve işlem başına risk bütçesine göre lot hesabı."""

    sermaye: float
    azami_risk_orani: float
    risk_butcesi: float
    hisse_basina_risk: float
    risk_bazli_lot: int
    sermaye_bazli_lot: int
    lot_sayisi: int
    pozisyon_tutari: float
    planlanan_risk: float
    sermaye_kullanim_orani: float


@dataclass(frozen=True)
class TradePlan:
    """Çoklu zaman dilimi teyidinden üretilen güncel uzun işlem planı."""

    sembol: str
    veri_kimligi: str
    teknik_analiz_kimligi: str
    plan_kimligi: str
    karar: str
    plan_tipi: str
    teyit_skoru: int
    son_kapanis: float
    atr14: float
    atr_yuzde: float
    izleme_tetik_fiyati: float | None
    giris_alt: float | None
    giris_ust: float | None
    referans_giris: float | None
    stop_loss: float | None
    hedef_1: float | None
    hedef_2: float | None
    risk_odul_1: float | None
    risk_odul_2: float | None
    pozisyon: PositionSizeResult | None
    giris_kaynagi: str | None
    stop_kaynagi: str | None
    hedef_1_kaynagi: str | None
    hedef_2_kaynagi: str | None
    beklenen_teyitler: tuple[str, ...]
    gecersizlik_kosullari: tuple[str, ...]
    notlar: tuple[str, ...]


@dataclass(frozen=True)
class _PlanLevels:
    izleme_tetik_fiyati: float
    giris_alt: float
    giris_ust: float
    referans_giris: float
    stop_loss: float
    hedef_1: float
    hedef_2: float
    risk_odul_1: float
    risk_odul_2: float
    giris_kaynagi: str
    stop_kaynagi: str
    hedef_1_kaynagi: str
    hedef_2_kaynagi: str


def pozisyon_boyutunu_hesapla(
    sermaye: float,
    giris_fiyati: float,
    stop_loss: float,
    azami_risk_orani: float = 0.01,
) -> PositionSizeResult:
    """
    Sermaye ve stop mesafesine göre tam lot sayısını hesaplar.

    Sonuç hem risk bütçesi hem de mevcut nakit ile sınırlandırılır;
    kaldıraç veya kesirli lot kullanılmaz.
    """
    _pozisyon_girdilerini_dogrula(
        sermaye=sermaye,
        giris_fiyati=giris_fiyati,
        stop_loss=stop_loss,
        azami_risk_orani=azami_risk_orani,
    )

    hisse_basina_risk = giris_fiyati - stop_loss
    risk_butcesi = sermaye * azami_risk_orani
    risk_bazli_lot = math.floor(risk_butcesi / hisse_basina_risk)
    sermaye_bazli_lot = math.floor(sermaye / giris_fiyati)
    lot_sayisi = min(risk_bazli_lot, sermaye_bazli_lot)
    pozisyon_tutari = lot_sayisi * giris_fiyati
    planlanan_risk = lot_sayisi * hisse_basina_risk
    sermaye_kullanim_orani = pozisyon_tutari / sermaye

    return PositionSizeResult(
        sermaye=float(sermaye),
        azami_risk_orani=float(azami_risk_orani),
        risk_butcesi=float(risk_butcesi),
        hisse_basina_risk=float(hisse_basina_risk),
        risk_bazli_lot=int(risk_bazli_lot),
        sermaye_bazli_lot=int(sermaye_bazli_lot),
        lot_sayisi=int(lot_sayisi),
        pozisyon_tutari=float(pozisyon_tutari),
        planlanan_risk=float(planlanan_risk),
        sermaye_kullanim_orani=float(sermaye_kullanim_orani),
    )


def islem_plani_olustur(
    paket: MultiTimeframeDataBundle,
    teknik_teyit: MultiTimeframeTechnicalConfirmation | None = None,
    sermaye: float = 100_000.0,
    azami_risk_orani: float = 0.01,
    minimum_teyit_skoru: int = 60,
    kosullu_plan_skoru: int = 40,
    stop_atr_katsayisi: float = 1.50,
    minimum_risk_odul: float = 2.00,
) -> TradePlan:
    """
    Haftalık trend, günlük yön ve saatlik zamanlamadan uzun işlem planı üretir.

    Plan yalnızca tamamlanmış mumlara dayanır. Negatif günlük yapı,
    negatif haftalık trend veya teyitli aşağı kırılım işlem açılmasını engeller.
    """
    _plan_girdilerini_dogrula(
        sermaye=sermaye,
        azami_risk_orani=azami_risk_orani,
        minimum_teyit_skoru=minimum_teyit_skoru,
        kosullu_plan_skoru=kosullu_plan_skoru,
        stop_atr_katsayisi=stop_atr_katsayisi,
        minimum_risk_odul=minimum_risk_odul,
    )

    analiz = teknik_teyit or teknik_teyit_analizi_yap(paket)
    _paket_ve_analizi_dogrula(paket, analiz)

    kapanis, atr14 = _gunluk_fiyat_ve_atr(paket)
    atr_yuzde = atr14 / kapanis * 100.0
    engeller = _islem_engellerini_bul(analiz)
    plan_tipi = _plan_tipini_belirle(
        analiz=analiz,
        engeller=engeller,
        minimum_teyit_skoru=minimum_teyit_skoru,
        kosullu_plan_skoru=kosullu_plan_skoru,
    )
    beklenen_teyitler = _beklenen_teyitleri_olustur(
        analiz=analiz,
        minimum_teyit_skoru=minimum_teyit_skoru,
        engeller=engeller,
    )
    gecersizlik_kosullari = _gecersizlik_kosullarini_olustur(
        analiz=analiz,
    )

    if plan_tipi == PLAN_OLUSTURULMADI:
        tetik = _izleme_tetik_fiyati(analiz, kapanis, atr14)
        return _bos_plan(
            paket=paket,
            analiz=analiz,
            kapanis=kapanis,
            atr14=atr14,
            atr_yuzde=atr_yuzde,
            izleme_tetik_fiyati=tetik,
            beklenen_teyitler=beklenen_teyitler,
            gecersizlik_kosullari=gecersizlik_kosullari,
            notlar=tuple(engeller) or (
                "Teknik uyum işlem planı için yeterli değil.",
            ),
            sermaye=sermaye,
            azami_risk_orani=azami_risk_orani,
        )

    seviyeler = _plan_seviyelerini_hesapla(
        analiz=analiz,
        kapanis=kapanis,
        atr14=atr14,
        stop_atr_katsayisi=stop_atr_katsayisi,
        minimum_risk_odul=minimum_risk_odul,
        kosullu=(plan_tipi == KOSULLU_ALIM_PLANI),
    )
    pozisyon = pozisyon_boyutunu_hesapla(
        sermaye=sermaye,
        giris_fiyati=seviyeler.referans_giris,
        stop_loss=seviyeler.stop_loss,
        azami_risk_orani=azami_risk_orani,
    )

    if pozisyon.lot_sayisi < 1:
        return _bos_plan(
            paket=paket,
            analiz=analiz,
            kapanis=kapanis,
            atr14=atr14,
            atr_yuzde=atr_yuzde,
            izleme_tetik_fiyati=seviyeler.izleme_tetik_fiyati,
            beklenen_teyitler=beklenen_teyitler,
            gecersizlik_kosullari=gecersizlik_kosullari,
            notlar=(
                "Sermaye ve risk bütçesi en az bir lot için yetersiz.",
            ),
            sermaye=sermaye,
            azami_risk_orani=azami_risk_orani,
        )

    karar = ISLEM_VAR if plan_tipi == ONAYLI_ALIM_PLANI else ISLEM_YOK
    notlar = (
        "Pozisyon büyüklüğü giriş bölgesinin üst sınırı kullanılarak hesaplandı.",
        "Hedef 1 kısmi kâr, hedef 2 ana risk/getiri hedefidir.",
    )
    plan_kimligi = _plan_kimligi_uret(
        analiz=analiz,
        karar=karar,
        plan_tipi=plan_tipi,
        seviyeler=seviyeler,
        sermaye=sermaye,
        azami_risk_orani=azami_risk_orani,
    )

    return TradePlan(
        sembol=paket.sembol,
        veri_kimligi=paket.veri_kimligi,
        teknik_analiz_kimligi=analiz.analiz_kimligi,
        plan_kimligi=plan_kimligi,
        karar=karar,
        plan_tipi=plan_tipi,
        teyit_skoru=analiz.teyit_skoru,
        son_kapanis=float(kapanis),
        atr14=float(atr14),
        atr_yuzde=float(atr_yuzde),
        izleme_tetik_fiyati=seviyeler.izleme_tetik_fiyati,
        giris_alt=seviyeler.giris_alt,
        giris_ust=seviyeler.giris_ust,
        referans_giris=seviyeler.referans_giris,
        stop_loss=seviyeler.stop_loss,
        hedef_1=seviyeler.hedef_1,
        hedef_2=seviyeler.hedef_2,
        risk_odul_1=seviyeler.risk_odul_1,
        risk_odul_2=seviyeler.risk_odul_2,
        pozisyon=pozisyon,
        giris_kaynagi=seviyeler.giris_kaynagi,
        stop_kaynagi=seviyeler.stop_kaynagi,
        hedef_1_kaynagi=seviyeler.hedef_1_kaynagi,
        hedef_2_kaynagi=seviyeler.hedef_2_kaynagi,
        beklenen_teyitler=beklenen_teyitler,
        gecersizlik_kosullari=gecersizlik_kosullari,
        notlar=notlar,
    )


def _gunluk_fiyat_ve_atr(
    paket: MultiTimeframeDataBundle,
) -> tuple[float, float]:
    try:
        gunluk = paket.getir(GUNLUK)
        gostergeli = teknik_gostergeleri_ekle(gunluk.veri)
    except (KeyError, IndicatorError, ValueError) as hata:
        raise TradePlanError(
            f"Günlük fiyat ve ATR hazırlanamadı: {hata}"
        ) from hata

    gecerli = gostergeli.dropna(subset=["Close", "ATR14"])
    if gecerli.empty:
        raise TradePlanError("Günlük ATR için yeterli geçerli veri yok.")

    son = gecerli.iloc[-1]
    kapanis = float(son["Close"])
    atr14 = float(son["ATR14"])
    if kapanis <= 0 or atr14 <= 0:
        raise TradePlanError("Kapanış ve ATR pozitif olmalıdır.")
    return kapanis, atr14


def _islem_engellerini_bul(
    analiz: MultiTimeframeTechnicalConfirmation,
) -> list[str]:
    engeller: list[str] = []
    if analiz.haftalik.yon == NEGATIF:
        engeller.append("Haftalık ana trend negatif.")
    if analiz.gunluk.yon == NEGATIF:
        engeller.append("Günlük yön teyidi negatif.")
    if analiz.gunluk.kirilim.durum == TEYITLI_ASAGI_KIRILIM:
        engeller.append("Günlük teyitli aşağı kırılım var.")
    if analiz.saatlik.kirilim.durum == TEYITLI_ASAGI_KIRILIM:
        engeller.append("Saatlik teyitli aşağı kırılım var.")
    if analiz.gunluk.ortalamalar.death_cross:
        engeller.append("Günlük Death Cross oluştu.")
    return engeller


def _plan_tipini_belirle(
    analiz: MultiTimeframeTechnicalConfirmation,
    engeller: list[str],
    minimum_teyit_skoru: int,
    kosullu_plan_skoru: int,
) -> str:
    if engeller:
        return PLAN_OLUSTURULMADI

    saatlik_giris_teyidi = (
        analiz.saatlik.yon == POZITIF
        or analiz.saatlik.kirilim.durum == TEYITLI_YUKARI_KIRILIM
    )
    if (
        analiz.teyit_skoru >= minimum_teyit_skoru
        and analiz.gunluk.yon == POZITIF
        and saatlik_giris_teyidi
        and analiz.haftalik.yon != NEGATIF
    ):
        return ONAYLI_ALIM_PLANI

    if (
        analiz.teyit_skoru >= kosullu_plan_skoru
        and analiz.gunluk.yon != NEGATIF
        and analiz.haftalik.yon != NEGATIF
    ):
        return KOSULLU_ALIM_PLANI

    return PLAN_OLUSTURULMADI


def _plan_seviyelerini_hesapla(
    analiz: MultiTimeframeTechnicalConfirmation,
    kapanis: float,
    atr14: float,
    stop_atr_katsayisi: float,
    minimum_risk_odul: float,
    kosullu: bool,
) -> _PlanLevels:
    yukari_kirilim = (
        analiz.gunluk.kirilim.durum == TEYITLI_YUKARI_KIRILIM
        or analiz.saatlik.kirilim.durum == TEYITLI_YUKARI_KIRILIM
    )
    direncler = _pozitif_seviyeleri_sirala(
        kapanis,
        analiz.saatlik.direnc,
        analiz.gunluk.direnc,
        analiz.haftalik.direnc,
    )

    if kosullu:
        taban = direncler[0] if direncler else kapanis + atr14 * 0.50
        izleme_tetik = max(kapanis, taban) + atr14 * 0.05
        giris_alt = izleme_tetik
        giris_ust = izleme_tetik + atr14 * 0.15
        giris_kaynagi = "Direnç üzeri kapanış teyidi"
    elif yukari_kirilim:
        izleme_tetik = kapanis
        giris_alt = kapanis
        giris_ust = kapanis + atr14 * 0.15
        giris_kaynagi = "Teyitli yukarı kırılım"
    else:
        izleme_tetik = kapanis
        giris_alt = max(0.01, kapanis - atr14 * 0.05)
        giris_ust = kapanis + atr14 * 0.15
        giris_kaynagi = "Pozitif çoklu zaman dilimi uyumu"

    referans_giris = giris_ust
    destekler = _negatif_seviyeleri_sirala(
        referans_giris,
        analiz.saatlik.destek,
        analiz.gunluk.destek,
        analiz.haftalik.destek,
    )
    atr_stop = referans_giris - atr14 * stop_atr_katsayisi
    stop_loss = atr_stop
    stop_kaynagi = f"{stop_atr_katsayisi:.2f} ATR"

    if destekler:
        yakin_destek = destekler[0]
        destek_mesafesi = referans_giris - yakin_destek
        if destek_mesafesi <= atr14 * 2.50:
            stop_loss = min(atr_stop, yakin_destek - atr14 * 0.20)
            stop_kaynagi = "Yakın destek altı + ATR payı"

    if stop_loss <= 0 or stop_loss >= referans_giris:
        raise TradePlanError("Geçerli stop-loss seviyesi hesaplanamadı.")

    risk = referans_giris - stop_loss
    hedef_adaylari = _pozitif_seviyeleri_sirala(
        referans_giris,
        analiz.saatlik.direnc,
        analiz.gunluk.direnc,
        analiz.haftalik.direnc,
    )
    asgari_hedef_1 = referans_giris + risk
    yapisal_hedef_1 = next(
        (seviye for seviye in hedef_adaylari if seviye >= asgari_hedef_1),
        None,
    )
    if yapisal_hedef_1 is not None:
        hedef_1 = yapisal_hedef_1
        hedef_1_kaynagi = "İlk uygun teknik direnç"
    else:
        hedef_1 = referans_giris + risk * 1.50
        hedef_1_kaynagi = "1.50R ara hedef"

    asgari_hedef_2 = referans_giris + risk * minimum_risk_odul
    yapisal_hedef_2 = next(
        (
            seviye
            for seviye in hedef_adaylari
            if seviye > hedef_1 and seviye >= asgari_hedef_2
        ),
        None,
    )
    if yapisal_hedef_2 is not None:
        hedef_2 = yapisal_hedef_2
        hedef_2_kaynagi = "Üst teknik direnç"
    else:
        hedef_2 = max(asgari_hedef_2, hedef_1 + risk * 0.50)
        hedef_2_kaynagi = f"{minimum_risk_odul:.2f}R ana hedef"

    risk_odul_1 = (hedef_1 - referans_giris) / risk
    risk_odul_2 = (hedef_2 - referans_giris) / risk

    return _PlanLevels(
        izleme_tetik_fiyati=float(izleme_tetik),
        giris_alt=float(giris_alt),
        giris_ust=float(giris_ust),
        referans_giris=float(referans_giris),
        stop_loss=float(stop_loss),
        hedef_1=float(hedef_1),
        hedef_2=float(hedef_2),
        risk_odul_1=float(risk_odul_1),
        risk_odul_2=float(risk_odul_2),
        giris_kaynagi=giris_kaynagi,
        stop_kaynagi=stop_kaynagi,
        hedef_1_kaynagi=hedef_1_kaynagi,
        hedef_2_kaynagi=hedef_2_kaynagi,
    )


def _izleme_tetik_fiyati(
    analiz: MultiTimeframeTechnicalConfirmation,
    kapanis: float,
    atr14: float,
) -> float:
    direncler = _pozitif_seviyeleri_sirala(
        kapanis,
        analiz.saatlik.direnc,
        analiz.gunluk.direnc,
        analiz.haftalik.direnc,
    )
    taban = direncler[0] if direncler else kapanis + atr14 * 0.50
    return float(taban + atr14 * 0.05)


def _pozitif_seviyeleri_sirala(
    referans: float,
    *seviyeler: float | None,
) -> list[float]:
    return sorted(
        {
            float(seviye)
            for seviye in seviyeler
            if seviye is not None and float(seviye) > referans
        }
    )


def _negatif_seviyeleri_sirala(
    referans: float,
    *seviyeler: float | None,
) -> list[float]:
    return sorted(
        {
            float(seviye)
            for seviye in seviyeler
            if seviye is not None and 0 < float(seviye) < referans
        },
        reverse=True,
    )


def _beklenen_teyitleri_olustur(
    analiz: MultiTimeframeTechnicalConfirmation,
    minimum_teyit_skoru: int,
    engeller: list[str],
) -> tuple[str, ...]:
    teyitler: list[str] = []
    if analiz.teyit_skoru < minimum_teyit_skoru:
        teyitler.append(
            f"Teknik teyit skoru en az {minimum_teyit_skoru}/100 olmalı."
        )
    if analiz.haftalik.yon == NEGATIF:
        teyitler.append("Haftalık ana trend nötr veya pozitif olmalı.")
    if analiz.gunluk.yon != POZITIF:
        teyitler.append("Günlük yön pozitif teyit vermeli.")
    if analiz.saatlik.yon != POZITIF:
        teyitler.append("Saatlik giriş zamanlaması pozitif olmalı.")
    if not analiz.gunluk.kirilim.hacim_teyidi:
        teyitler.append("Yukarı hareket hacimle teyit edilmeli.")
    if engeller:
        teyitler.append("Mevcut teknik engeller ortadan kalkmalı.")
    return tuple(dict.fromkeys(teyitler))


def _gecersizlik_kosullarini_olustur(
    analiz: MultiTimeframeTechnicalConfirmation,
) -> tuple[str, ...]:
    kosullar = [
        "Günlük veya saatlik mumun teyitli aşağı kırılım yapması.",
        "Günlük yönün negatif teknik görünüme dönmesi.",
        "Haftalık ana trendin negatife dönmesi.",
    ]
    destekler = [
        seviye
        for seviye in (
            analiz.saatlik.destek,
            analiz.gunluk.destek,
            analiz.haftalik.destek,
        )
        if seviye is not None
    ]
    if destekler:
        kosullar.append(
            f"En yakın izlenen desteğin ({max(destekler):.2f}) altında kapanış."
        )
    return tuple(kosullar)


def _bos_plan(
    paket: MultiTimeframeDataBundle,
    analiz: MultiTimeframeTechnicalConfirmation,
    kapanis: float,
    atr14: float,
    atr_yuzde: float,
    izleme_tetik_fiyati: float,
    beklenen_teyitler: tuple[str, ...],
    gecersizlik_kosullari: tuple[str, ...],
    notlar: tuple[str, ...],
    sermaye: float,
    azami_risk_orani: float,
) -> TradePlan:
    plan_kimligi = _bos_plan_kimligi_uret(
        analiz=analiz,
        izleme_tetik_fiyati=izleme_tetik_fiyati,
        sermaye=sermaye,
        azami_risk_orani=azami_risk_orani,
    )
    return TradePlan(
        sembol=paket.sembol,
        veri_kimligi=paket.veri_kimligi,
        teknik_analiz_kimligi=analiz.analiz_kimligi,
        plan_kimligi=plan_kimligi,
        karar=ISLEM_YOK,
        plan_tipi=PLAN_OLUSTURULMADI,
        teyit_skoru=analiz.teyit_skoru,
        son_kapanis=float(kapanis),
        atr14=float(atr14),
        atr_yuzde=float(atr_yuzde),
        izleme_tetik_fiyati=float(izleme_tetik_fiyati),
        giris_alt=None,
        giris_ust=None,
        referans_giris=None,
        stop_loss=None,
        hedef_1=None,
        hedef_2=None,
        risk_odul_1=None,
        risk_odul_2=None,
        pozisyon=None,
        giris_kaynagi=None,
        stop_kaynagi=None,
        hedef_1_kaynagi=None,
        hedef_2_kaynagi=None,
        beklenen_teyitler=beklenen_teyitler,
        gecersizlik_kosullari=gecersizlik_kosullari,
        notlar=notlar,
    )


def _plan_kimligi_uret(
    analiz: MultiTimeframeTechnicalConfirmation,
    karar: str,
    plan_tipi: str,
    seviyeler: _PlanLevels,
    sermaye: float,
    azami_risk_orani: float,
) -> str:
    metin = "|".join(
        (
            analiz.analiz_kimligi,
            karar,
            plan_tipi,
            f"{seviyeler.giris_alt:.8f}",
            f"{seviyeler.giris_ust:.8f}",
            f"{seviyeler.stop_loss:.8f}",
            f"{seviyeler.hedef_1:.8f}",
            f"{seviyeler.hedef_2:.8f}",
            f"{sermaye:.2f}",
            f"{azami_risk_orani:.8f}",
        )
    )
    return sha256(metin.encode("utf-8")).hexdigest()[:12]


def _bos_plan_kimligi_uret(
    analiz: MultiTimeframeTechnicalConfirmation,
    izleme_tetik_fiyati: float,
    sermaye: float,
    azami_risk_orani: float,
) -> str:
    metin = "|".join(
        (
            analiz.analiz_kimligi,
            ISLEM_YOK,
            f"{izleme_tetik_fiyati:.8f}",
            f"{sermaye:.2f}",
            f"{azami_risk_orani:.8f}",
        )
    )
    return sha256(metin.encode("utf-8")).hexdigest()[:12]


def _paket_ve_analizi_dogrula(
    paket: MultiTimeframeDataBundle,
    analiz: MultiTimeframeTechnicalConfirmation,
) -> None:
    if paket.sembol != analiz.sembol:
        raise TradePlanError(
            "Veri paketi ile teknik teyit sembolü eşleşmiyor."
        )
    if paket.veri_kimligi != analiz.veri_kimligi:
        raise TradePlanError(
            "Veri paketi ile teknik teyit veri kimliği eşleşmiyor."
        )


def _pozisyon_girdilerini_dogrula(
    sermaye: float,
    giris_fiyati: float,
    stop_loss: float,
    azami_risk_orani: float,
) -> None:
    if sermaye <= 0:
        raise ValueError("Sermaye sıfırdan büyük olmalıdır.")
    if giris_fiyati <= 0:
        raise ValueError("Giriş fiyatı sıfırdan büyük olmalıdır.")
    if stop_loss <= 0:
        raise ValueError("Stop-loss sıfırdan büyük olmalıdır.")
    if stop_loss >= giris_fiyati:
        raise ValueError("Stop-loss giriş fiyatının altında olmalıdır.")
    if not 0 < azami_risk_orani <= 1:
        raise ValueError("Azami risk oranı 0 ile 1 arasında olmalıdır.")


def _plan_girdilerini_dogrula(
    sermaye: float,
    azami_risk_orani: float,
    minimum_teyit_skoru: int,
    kosullu_plan_skoru: int,
    stop_atr_katsayisi: float,
    minimum_risk_odul: float,
) -> None:
    if sermaye <= 0:
        raise ValueError("Sermaye sıfırdan büyük olmalıdır.")
    if not 0 < azami_risk_orani <= 1:
        raise ValueError("Azami risk oranı 0 ile 1 arasında olmalıdır.")
    if not 0 <= kosullu_plan_skoru <= minimum_teyit_skoru <= 100:
        raise ValueError(
            "Koşullu ve minimum teyit skorları 0-100 aralığında olmalı."
        )
    if stop_atr_katsayisi <= 0:
        raise ValueError("Stop ATR katsayısı sıfırdan büyük olmalıdır.")
    if minimum_risk_odul <= 0:
        raise ValueError("Minimum risk/ödül sıfırdan büyük olmalıdır.")
