from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import math

import pandas as pd

from ..data.multi_timeframe_data import GUNLUK, MultiTimeframeDataBundle
from ..indicators.technical_indicators import IndicatorError, teknik_gostergeleri_ekle
from .technical_confirmation import (
    NEGATIF,
    NOTR,
    POZITIF,
    TEYITLI_ASAGI_KIRILIM,
    MultiTimeframeTechnicalConfirmation,
    TechnicalConfirmationError,
    teknik_teyit_analizi_yap,
)


AKTIF = "Aktif"
UYARI = "Uyarı"
RISK = "Risk"
CIKIS = "Çıkış"

POZISYONU_TASI = "Pozisyonu Taşı"
YENI_ALIM_YAPMA = "Yeni Alım Yapma"
STOPU_YAKINDAN_IZLE = "Stopu Yakından İzle"
POZISYONU_KAPAT = "Pozisyonu Kapat"

HEDEF_ULASILDI = "Ulaşıldı"
HEDEF_YAKLASIYOR = "Yaklaşıyor"
HEDEF_BEKLENIYOR = "Bekleniyor"


class PositionMonitorError(Exception):
    """Açık pozisyon izleme sonucu üretilemediğinde kullanılır."""


@dataclass(frozen=True)
class OpenPosition:
    """İzlenecek uzun yönlü açık pozisyonun değişmez giriş bilgileri."""

    giris_tarihi: pd.Timestamp | str
    giris_fiyati: float
    lot_sayisi: int
    ilk_stop: float
    hedef_1: float
    hedef_2: float
    mevcut_stop: float | None = None
    hedef_1_gerceklesti: bool = False


@dataclass(frozen=True)
class TargetProgress:
    """Bir hedefin güncel fiyat karşısındaki ilerleme durumu."""

    hedef: float
    durum: str
    kalan_fiyat: float
    kalan_yuzde: float


@dataclass(frozen=True)
class PositionMonitoringResult:
    """Açık pozisyonun fiyat, risk ve teknik yapı açısından güncel özeti."""

    sembol: str
    veri_kimligi: str
    teknik_analiz_kimligi: str
    izleme_kimligi: str
    durum: str
    eylem: str
    son_tarih: pd.Timestamp
    son_kapanis: float
    giris_tarihi: pd.Timestamp
    giris_fiyati: float
    lot_sayisi: int
    acik_kar_zarar: float
    acik_kar_zarar_yuzde: float
    r_katsayisi: float
    ilk_stop: float
    onceki_stop: float
    dinamik_stop: float
    stop_kaynagi: str
    stop_mesafesi: float
    stop_mesafesi_yuzde: float
    en_yuksek_kapanis: float
    en_yuksek_fiyat: float
    atr14: float
    hedef_1: TargetProgress
    hedef_2: TargetProgress
    kismi_kar_onerisi: bool
    onerilen_kismi_kar_lotu: int
    pozitif_nedenler: tuple[str, ...]
    riskler: tuple[str, ...]
    notlar: tuple[str, ...]


def acik_pozisyonu_izle(
    paket: MultiTimeframeDataBundle,
    pozisyon: OpenPosition,
    teknik_teyit: MultiTimeframeTechnicalConfirmation | None = None,
    iz_suren_atr_katsayisi: float = 2.0,
    basa_bas_r_esigi: float = 1.0,
    kar_koruma_r_esigi: float = 1.5,
    hedef_yaklasma_orani: float = 0.02,
    kismi_kar_orani: float = 0.50,
) -> PositionMonitoringResult:
    """
    Açık uzun pozisyonu tamamlanmış günlük mumlar ve çoklu zaman dilimi
    teknik teyidiyle değerlendirir.

    Dinamik stop hiçbir zaman ilk/mevcut stopun altına indirilmez. Başa baş,
    ATR tabanlı iz süren stop ve yakın günlük destek adayları yalnızca mevcut
    kapanışın altında kaldıklarında kullanılır.
    """
    _ayarları_dogrula(
        iz_suren_atr_katsayisi=iz_suren_atr_katsayisi,
        basa_bas_r_esigi=basa_bas_r_esigi,
        kar_koruma_r_esigi=kar_koruma_r_esigi,
        hedef_yaklasma_orani=hedef_yaklasma_orani,
        kismi_kar_orani=kismi_kar_orani,
    )
    giris_tarihi = _pozisyonu_dogrula(pozisyon)

    analiz = teknik_teyit or teknik_teyit_analizi_yap(paket)
    _paket_ve_analizi_dogrula(paket, analiz)

    (
        gunluk,
        son_tarih,
        son_kapanis,
        atr14,
        en_yuksek_kapanis,
        en_yuksek_fiyat,
    ) = _gunluk_pozisyon_verisini_hazirla(paket, giris_tarihi)
    del gunluk  # Gelecekte işlem günlüğü ayrıntıları için saklı genişleme noktası.

    ilk_risk = pozisyon.giris_fiyati - pozisyon.ilk_stop
    r_katsayisi = (son_kapanis - pozisyon.giris_fiyati) / ilk_risk
    onceki_stop = max(
        pozisyon.ilk_stop,
        pozisyon.mevcut_stop
        if pozisyon.mevcut_stop is not None
        else pozisyon.ilk_stop,
    )

    dinamik_stop, stop_kaynagi = _dinamik_stop_hesapla(
        pozisyon=pozisyon,
        analiz=analiz,
        son_kapanis=son_kapanis,
        atr14=atr14,
        en_yuksek_kapanis=en_yuksek_kapanis,
        onceki_stop=onceki_stop,
        r_katsayisi=r_katsayisi,
        iz_suren_atr_katsayisi=iz_suren_atr_katsayisi,
        basa_bas_r_esigi=basa_bas_r_esigi,
        kar_koruma_r_esigi=kar_koruma_r_esigi,
    )

    hedef_1 = _hedef_ilerlemesini_hesapla(
        son_kapanis=son_kapanis,
        en_yuksek_fiyat=en_yuksek_fiyat,
        hedef=pozisyon.hedef_1,
        hedef_yaklasma_orani=hedef_yaklasma_orani,
    )
    hedef_2 = _hedef_ilerlemesini_hesapla(
        son_kapanis=son_kapanis,
        en_yuksek_fiyat=en_yuksek_fiyat,
        hedef=pozisyon.hedef_2,
        hedef_yaklasma_orani=hedef_yaklasma_orani,
    )

    kismi_kar_onerisi = (
        hedef_1.durum == HEDEF_ULASILDI
        and hedef_2.durum != HEDEF_ULASILDI
        and not pozisyon.hedef_1_gerceklesti
    )
    onerilen_kismi_kar_lotu = (
        max(1, math.floor(pozisyon.lot_sayisi * kismi_kar_orani))
        if kismi_kar_onerisi
        else 0
    )

    durum, eylem, pozitif_nedenler, riskler, notlar = _durumu_belirle(
        pozisyon=pozisyon,
        analiz=analiz,
        son_kapanis=son_kapanis,
        atr14=atr14,
        dinamik_stop=dinamik_stop,
        r_katsayisi=r_katsayisi,
        hedef_1=hedef_1,
        hedef_2=hedef_2,
        kismi_kar_onerisi=kismi_kar_onerisi,
    )

    acik_kar_zarar = (
        son_kapanis - pozisyon.giris_fiyati
    ) * pozisyon.lot_sayisi
    acik_kar_zarar_yuzde = (
        son_kapanis / pozisyon.giris_fiyati - 1.0
    ) * 100.0
    stop_mesafesi = son_kapanis - dinamik_stop
    stop_mesafesi_yuzde = stop_mesafesi / son_kapanis * 100.0

    izleme_kimligi = _izleme_kimligi_uret(
        paket=paket,
        analiz=analiz,
        pozisyon=pozisyon,
        giris_tarihi=giris_tarihi,
        son_tarih=son_tarih,
        son_kapanis=son_kapanis,
        dinamik_stop=dinamik_stop,
        durum=durum,
    )

    return PositionMonitoringResult(
        sembol=paket.sembol,
        veri_kimligi=paket.veri_kimligi,
        teknik_analiz_kimligi=analiz.analiz_kimligi,
        izleme_kimligi=izleme_kimligi,
        durum=durum,
        eylem=eylem,
        son_tarih=son_tarih,
        son_kapanis=float(son_kapanis),
        giris_tarihi=giris_tarihi,
        giris_fiyati=float(pozisyon.giris_fiyati),
        lot_sayisi=int(pozisyon.lot_sayisi),
        acik_kar_zarar=float(acik_kar_zarar),
        acik_kar_zarar_yuzde=float(acik_kar_zarar_yuzde),
        r_katsayisi=float(r_katsayisi),
        ilk_stop=float(pozisyon.ilk_stop),
        onceki_stop=float(onceki_stop),
        dinamik_stop=float(dinamik_stop),
        stop_kaynagi=stop_kaynagi,
        stop_mesafesi=float(stop_mesafesi),
        stop_mesafesi_yuzde=float(stop_mesafesi_yuzde),
        en_yuksek_kapanis=float(en_yuksek_kapanis),
        en_yuksek_fiyat=float(en_yuksek_fiyat),
        atr14=float(atr14),
        hedef_1=hedef_1,
        hedef_2=hedef_2,
        kismi_kar_onerisi=kismi_kar_onerisi,
        onerilen_kismi_kar_lotu=onerilen_kismi_kar_lotu,
        pozitif_nedenler=tuple(pozitif_nedenler),
        riskler=tuple(riskler),
        notlar=tuple(notlar),
    )


def _ayarları_dogrula(
    iz_suren_atr_katsayisi: float,
    basa_bas_r_esigi: float,
    kar_koruma_r_esigi: float,
    hedef_yaklasma_orani: float,
    kismi_kar_orani: float,
) -> None:
    if iz_suren_atr_katsayisi <= 0:
        raise ValueError("İz süren ATR katsayısı pozitif olmalıdır.")
    if basa_bas_r_esigi <= 0:
        raise ValueError("Başa baş R eşiği pozitif olmalıdır.")
    if kar_koruma_r_esigi < basa_bas_r_esigi:
        raise ValueError(
            "Kâr koruma R eşiği başa baş eşiğinden küçük olamaz."
        )
    if not 0 < hedef_yaklasma_orani < 1:
        raise ValueError("Hedef yaklaşma oranı 0 ile 1 arasında olmalıdır.")
    if not 0 < kismi_kar_orani <= 1:
        raise ValueError("Kısmi kâr oranı 0 ile 1 arasında olmalıdır.")


def _pozisyonu_dogrula(pozisyon: OpenPosition) -> pd.Timestamp:
    try:
        giris_tarihi = pd.Timestamp(pozisyon.giris_tarihi).normalize()
    except Exception as hata:
        raise ValueError("Geçerli bir giriş tarihi gereklidir.") from hata

    if pd.isna(giris_tarihi):
        raise ValueError("Geçerli bir giriş tarihi gereklidir.")
    if pozisyon.giris_fiyati <= 0:
        raise ValueError("Giriş fiyatı pozitif olmalıdır.")
    if pozisyon.lot_sayisi < 1:
        raise ValueError("Lot sayısı en az 1 olmalıdır.")
    if not 0 < pozisyon.ilk_stop < pozisyon.giris_fiyati:
        raise ValueError("İlk stop giriş fiyatının altında ve pozitif olmalıdır.")
    if not pozisyon.giris_fiyati < pozisyon.hedef_1 < pozisyon.hedef_2:
        raise ValueError(
            "Hedef 1 girişin üzerinde, hedef 2 ise hedef 1'in üzerinde olmalıdır."
        )
    if pozisyon.mevcut_stop is not None:
        if pozisyon.mevcut_stop <= 0:
            raise ValueError("Mevcut stop pozitif olmalıdır.")
        if pozisyon.mevcut_stop < pozisyon.ilk_stop:
            raise ValueError("Mevcut stop ilk stopun altına indirilemez.")
    return giris_tarihi


def _paket_ve_analizi_dogrula(
    paket: MultiTimeframeDataBundle,
    analiz: MultiTimeframeTechnicalConfirmation,
) -> None:
    if paket.sembol != analiz.sembol:
        raise PositionMonitorError("Paket ve teknik analiz sembolü eşleşmiyor.")
    if paket.veri_kimligi != analiz.veri_kimligi:
        raise PositionMonitorError(
            "Paket ve teknik analiz veri kimliği eşleşmiyor."
        )


def _gunluk_pozisyon_verisini_hazirla(
    paket: MultiTimeframeDataBundle,
    giris_tarihi: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.Timestamp, float, float, float, float]:
    try:
        gunluk = paket.getir(GUNLUK).veri
        gostergeli = teknik_gostergeleri_ekle(gunluk)
    except (KeyError, IndicatorError, ValueError) as hata:
        raise PositionMonitorError(
            f"Günlük pozisyon verisi hazırlanamadı: {hata}"
        ) from hata

    gecerli = gostergeli.dropna(subset=["High", "Close", "ATR14"])
    if gecerli.empty:
        raise PositionMonitorError("Günlük ATR için yeterli geçerli veri yok.")

    son_tarih = pd.Timestamp(gecerli.index[-1]).normalize()
    if giris_tarihi > son_tarih:
        raise PositionMonitorError(
            "Giriş tarihi mevcut son tamamlanmış günlük mumdan sonra olamaz."
        )

    pozisyon_donemi = gecerli.loc[
        pd.DatetimeIndex(gecerli.index).normalize() >= giris_tarihi
    ]
    if pozisyon_donemi.empty:
        raise PositionMonitorError(
            "Giriş tarihinden sonra tamamlanmış günlük veri bulunamadı."
        )

    son = pozisyon_donemi.iloc[-1]
    son_kapanis = float(son["Close"])
    atr14 = float(son["ATR14"])
    en_yuksek_kapanis = float(pozisyon_donemi["Close"].max())
    en_yuksek_fiyat = float(pozisyon_donemi["High"].max())
    if son_kapanis <= 0 or atr14 <= 0 or en_yuksek_fiyat <= 0:
        raise PositionMonitorError("Kapanış ve ATR pozitif olmalıdır.")

    return (
        pozisyon_donemi,
        pd.Timestamp(pozisyon_donemi.index[-1]),
        son_kapanis,
        atr14,
        en_yuksek_kapanis,
        en_yuksek_fiyat,
    )


def _dinamik_stop_hesapla(
    pozisyon: OpenPosition,
    analiz: MultiTimeframeTechnicalConfirmation,
    son_kapanis: float,
    atr14: float,
    en_yuksek_kapanis: float,
    onceki_stop: float,
    r_katsayisi: float,
    iz_suren_atr_katsayisi: float,
    basa_bas_r_esigi: float,
    kar_koruma_r_esigi: float,
) -> tuple[float, str]:
    ilk_risk = pozisyon.giris_fiyati - pozisyon.ilk_stop
    adaylar: list[tuple[float, str]] = [(onceki_stop, "Mevcut/ilk stop")]

    if r_katsayisi >= basa_bas_r_esigi or pozisyon.hedef_1_gerceklesti:
        adaylar.append((pozisyon.giris_fiyati, "Başa baş stopu"))

    if r_katsayisi >= kar_koruma_r_esigi or pozisyon.hedef_1_gerceklesti:
        adaylar.append(
            (
                pozisyon.giris_fiyati + ilk_risk * 0.25,
                "Kâr koruma stopu",
            )
        )
        adaylar.append(
            (
                en_yuksek_kapanis - atr14 * iz_suren_atr_katsayisi,
                f"{iz_suren_atr_katsayisi:.2f} ATR iz süren stop",
            )
        )

    destek = analiz.gunluk.destek
    if destek is not None and destek > onceki_stop:
        adaylar.append((destek - atr14 * 0.20, "Günlük destek altı + ATR payı"))

    gecerli_adaylar = [
        (deger, kaynak)
        for deger, kaynak in adaylar
        if deger > 0 and deger < son_kapanis
    ]
    if not gecerli_adaylar:
        return float(onceki_stop), "Mevcut/ilk stop"

    deger, kaynak = max(gecerli_adaylar, key=lambda oge: oge[0])
    return float(max(onceki_stop, deger)), kaynak


def _hedef_ilerlemesini_hesapla(
    son_kapanis: float,
    en_yuksek_fiyat: float,
    hedef: float,
    hedef_yaklasma_orani: float,
) -> TargetProgress:
    hedef_tarihsel_olarak_goruldu = en_yuksek_fiyat >= hedef
    kalan_fiyat = (
        0.0
        if hedef_tarihsel_olarak_goruldu
        else max(0.0, hedef - son_kapanis)
    )
    kalan_yuzde = kalan_fiyat / son_kapanis * 100.0
    if hedef_tarihsel_olarak_goruldu:
        durum = HEDEF_ULASILDI
    elif kalan_fiyat / hedef <= hedef_yaklasma_orani:
        durum = HEDEF_YAKLASIYOR
    else:
        durum = HEDEF_BEKLENIYOR
    return TargetProgress(
        hedef=float(hedef),
        durum=durum,
        kalan_fiyat=float(kalan_fiyat),
        kalan_yuzde=float(kalan_yuzde),
    )


def _durumu_belirle(
    pozisyon: OpenPosition,
    analiz: MultiTimeframeTechnicalConfirmation,
    son_kapanis: float,
    atr14: float,
    dinamik_stop: float,
    r_katsayisi: float,
    hedef_1: TargetProgress,
    hedef_2: TargetProgress,
    kismi_kar_onerisi: bool,
) -> tuple[str, str, list[str], list[str], list[str]]:
    pozitif_nedenler: list[str] = []
    riskler: list[str] = []
    notlar: list[str] = []

    if r_katsayisi > 0:
        pozitif_nedenler.append(f"Pozisyon {r_katsayisi:.2f}R kârda.")
    if analiz.haftalik.yon == POZITIF:
        pozitif_nedenler.append("Haftalık ana trend pozitif.")
    if analiz.gunluk.yon == POZITIF:
        pozitif_nedenler.append("Günlük yön teyidi pozitif.")

    if son_kapanis <= dinamik_stop:
        riskler.append("Son kapanış dinamik stop seviyesine ulaştı veya altına indi.")
        return CIKIS, POZISYONU_KAPAT, pozitif_nedenler, riskler, notlar
    if hedef_2.durum == HEDEF_ULASILDI:
        if son_kapanis >= hedef_2.hedef:
            notlar.append("Ana hedef tamamlanmış mum kapanışıyla gerçekleşti.")
        else:
            notlar.append(
                "Ana hedef tamamlanmış günlük mumun gün içi en yüksek "
                "fiyatıyla gerçekleşti."
            )
        return CIKIS, POZISYONU_KAPAT, pozitif_nedenler, riskler, notlar
    if analiz.gunluk.kirilim.durum == TEYITLI_ASAGI_KIRILIM:
        riskler.append("Günlük teyitli aşağı kırılım oluştu.")
        return CIKIS, POZISYONU_KAPAT, pozitif_nedenler, riskler, notlar
    if analiz.haftalik.yon == NEGATIF and analiz.gunluk.yon == NEGATIF:
        riskler.append("Haftalık ve günlük yön birlikte negatif.")
        return CIKIS, POZISYONU_KAPAT, pozitif_nedenler, riskler, notlar

    stop_mesafesi = son_kapanis - dinamik_stop
    stopa_yakin = stop_mesafesi <= atr14 * 0.50
    if stopa_yakin:
        riskler.append("Kapanış dinamik stopa 0.50 ATR veya daha yakın.")
    if analiz.gunluk.yon == NEGATIF:
        riskler.append("Günlük yön teyidi negatif.")
    if analiz.gunluk.ortalamalar.death_cross:
        riskler.append("Günlük Death Cross riski var.")

    if stopa_yakin or analiz.gunluk.yon == NEGATIF:
        return RISK, STOPU_YAKINDAN_IZLE, pozitif_nedenler, riskler, notlar

    if analiz.saatlik.yon == NEGATIF:
        riskler.append("Saatlik zamanlama negatif.")
    if analiz.gunluk.yon == NOTR:
        riskler.append("Günlük yön teyidi henüz net değil.")
    if r_katsayisi < 0:
        riskler.append("Pozisyon giriş fiyatının altında.")
    if kismi_kar_onerisi:
        notlar.append("Hedef 1 görüldü; kısmi kâr değerlendirilmelidir.")

    if riskler or kismi_kar_onerisi or hedef_1.durum == HEDEF_YAKLASIYOR:
        return UYARI, YENI_ALIM_YAPMA, pozitif_nedenler, riskler, notlar

    if pozisyon.hedef_1_gerceklesti:
        notlar.append("Hedef 1 daha önce gerçekleştirildi; kalan pozisyon izleniyor.")
    return AKTIF, POZISYONU_TASI, pozitif_nedenler, riskler, notlar


def _izleme_kimligi_uret(
    paket: MultiTimeframeDataBundle,
    analiz: MultiTimeframeTechnicalConfirmation,
    pozisyon: OpenPosition,
    giris_tarihi: pd.Timestamp,
    son_tarih: pd.Timestamp,
    son_kapanis: float,
    dinamik_stop: float,
    durum: str,
) -> str:
    parcalar = (
        paket.sembol,
        paket.veri_kimligi,
        analiz.analiz_kimligi,
        giris_tarihi.isoformat(),
        f"{pozisyon.giris_fiyati:.8f}",
        str(pozisyon.lot_sayisi),
        f"{pozisyon.ilk_stop:.8f}",
        f"{pozisyon.hedef_1:.8f}",
        f"{pozisyon.hedef_2:.8f}",
        f"{pozisyon.mevcut_stop or 0.0:.8f}",
        str(pozisyon.hedef_1_gerceklesti),
        pd.Timestamp(son_tarih).isoformat(),
        f"{son_kapanis:.8f}",
        f"{dinamik_stop:.8f}",
        durum,
    )
    return sha256("|".join(parcalar).encode("utf-8")).hexdigest()[:12]
