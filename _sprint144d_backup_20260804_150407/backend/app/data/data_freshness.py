from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Mapping
from zoneinfo import ZoneInfo

import pandas as pd

ISTANBUL = ZoneInfo("Europe/Istanbul")
GUNCEL = "Güncel"
BEKLEMEDE = "Kapanış verisi bekleniyor"
ESKI = "Eski veri"
GELECEK = "Gelecek tarihli veri"
VERI_YOK = "Veri yok"


@dataclass(frozen=True)
class DataFreshnessPolicy:
    saat_dilimi: str = "Europe/Istanbul"
    seans_kapanisi: time = time(18, 10)
    saglayici_bekleme_dakikasi: int = 20
    kapali_tarihler: tuple[date, ...] = ()

    def __post_init__(self) -> None:
        if self.saglayici_bekleme_dakikasi < 0:
            raise ValueError("Sağlayıcı bekleme süresi negatif olamaz.")
        ZoneInfo(self.saat_dilimi)

    @property
    def zaman_bolgesi(self) -> ZoneInfo:
        return ZoneInfo(self.saat_dilimi)


@dataclass(frozen=True)
class DataFreshnessResult:
    durum: str
    son_veri_tarihi: date | None
    beklenen_tarih: date
    is_gunu_gecikmesi: int
    kilitli: bool
    aciklama: str
    kilit_asamasi: str = "günlük veri doğrulaması"
    sonraki_kontrol_zamani: datetime | None = None

    @property
    def guncel(self) -> bool:
        return self.durum in (GUNCEL, BEKLEMEDE) and not self.kilitli


@dataclass(frozen=True)
class BatchDataFreshnessResult:
    durum: str
    beklenen_tarih: date
    en_eski_tarih: date | None
    en_yeni_tarih: date | None
    toplam_sembol: int
    guncel_sembol: int
    eski_sembol: int
    veri_yok_sembol: int
    kilitli: bool
    aciklama: str
    kilit_asamasi: str = "toplu veri doğrulaması"
    sonraki_kontrol_zamani: datetime | None = None


def beklenen_son_tamamlanmis_islem_gunu(
    simdi: datetime | None = None,
    politika: DataFreshnessPolicy = DataFreshnessPolicy(),
) -> date:
    an = _yerel_zaman(simdi, politika)
    bugun = an.date()
    kapanis_esigi = datetime.combine(
        bugun,
        politika.seans_kapanisi,
        tzinfo=politika.zaman_bolgesi,
    ) + timedelta(minutes=politika.saglayici_bekleme_dakikasi)

    if _is_gunu_mu(bugun, politika) and an >= kapanis_esigi:
        return bugun
    return _onceki_is_gunu(bugun, politika)


def sonraki_tazelik_kontrol_zamani(
    *,
    simdi: datetime | None = None,
    politika: DataFreshnessPolicy = DataFreshnessPolicy(),
) -> datetime:
    """Kullanıcıya önerilecek en erken anlamlı yeniden kontrol zamanını üretir."""
    an = _yerel_zaman(simdi, politika)
    bugun = an.date()
    bugun_esigi = datetime.combine(
        bugun,
        politika.seans_kapanisi,
        tzinfo=politika.zaman_bolgesi,
    ) + timedelta(minutes=politika.saglayici_bekleme_dakikasi)

    if _is_gunu_mu(bugun, politika) and an < bugun_esigi:
        return bugun_esigi

    aday = bugun + timedelta(days=1)
    while not _is_gunu_mu(aday, politika):
        aday += timedelta(days=1)
    return datetime.combine(
        aday,
        politika.seans_kapanisi,
        tzinfo=politika.zaman_bolgesi,
    ) + timedelta(minutes=politika.saglayici_bekleme_dakikasi)


def gunluk_veri_tazeligini_degerlendir(
    veri: pd.DataFrame,
    *,
    simdi: datetime | None = None,
    politika: DataFreshnessPolicy = DataFreshnessPolicy(),
) -> DataFreshnessResult:
    an = _yerel_zaman(simdi, politika)
    bugun = an.date()
    beklenen = beklenen_son_tamamlanmis_islem_gunu(an, politika)

    if veri is None or veri.empty:
        return DataFreshnessResult(
            durum=VERI_YOK,
            son_veri_tarihi=None,
            beklenen_tarih=beklenen,
            is_gunu_gecikmesi=0,
            kilitli=True,
            aciklama="Günlük fiyat verisi bulunamadı; analiz güvenlik nedeniyle durduruldu.",
            kilit_asamasi="günlük veri indirme",
            sonraki_kontrol_zamani=sonraki_tazelik_kontrol_zamani(
                simdi=an,
                politika=politika,
            ),
        )

    son = pd.Timestamp(veri.index[-1]).date()

    # Seans içinde sağlayıcı bugüne ait kısmi günlük bar yayımlayabilir.
    # Bu bar beklenen son TAMAMLANMIŞ işlem gününden daha yeni olsa da
    # artık veri akışında bilinçli olarak kullanılır; "gelecek tarihli"
    # sayılıp kilitlenmez. Kapanış eşiğinden sonra beklenen tarih zaten
    # bugüne döneceği için aynı bar normal GÜNCEL statüsüne geçer.
    if son > beklenen:
        kapanis_esigi = datetime.combine(
            bugun,
            politika.seans_kapanisi,
            tzinfo=politika.zaman_bolgesi,
        ) + timedelta(minutes=politika.saglayici_bekleme_dakikasi)

        if (
            son == bugun
            and _is_gunu_mu(bugun, politika)
            and an < kapanis_esigi
        ):
            return DataFreshnessResult(
                durum=BEKLEMEDE,
                son_veri_tarihi=son,
                beklenen_tarih=beklenen,
                is_gunu_gecikmesi=0,
                kilitli=False,
                aciklama=(
                    f"Son günlük bar {son} gün içi/kısmi veridir ve analize "
                    f"yansıtılmaktadır. Son tamamlanmış işlem günü beklentisi "
                    f"{beklenen}; kapanış verisi bekleniyor."
                ),
                kilit_asamasi="gün içi veri doğrulandı",
                sonraki_kontrol_zamani=sonraki_tazelik_kontrol_zamani(
                    simdi=an,
                    politika=politika,
                ),
            )

        return DataFreshnessResult(
            durum=GELECEK,
            son_veri_tarihi=son,
            beklenen_tarih=beklenen,
            is_gunu_gecikmesi=0,
            kilitli=True,
            aciklama=(
                f"Son günlük bar {son}; beklenen tamamlanmış işlem günü {beklenen}. "
                "Bugünün gün içi barı dışında gelecekte tarihli/uyumsuz veri "
                "analize karışmış olabilir."
            ),
            kilit_asamasi="tarih doğrulaması",
            sonraki_kontrol_zamani=sonraki_tazelik_kontrol_zamani(
                simdi=an,
                politika=politika,
            ),
        )

    gecikme = _is_gunu_mesafesi(son, beklenen, politika)
    if gecikme > 0:
        return DataFreshnessResult(
            durum=ESKI,
            son_veri_tarihi=son,
            beklenen_tarih=beklenen,
            is_gunu_gecikmesi=gecikme,
            kilitli=True,
            aciklama=(
                f"Son günlük bar {son}; beklenen {beklenen}. Veri {gecikme} işlem günü geride. "
                "Momentum, teknik analiz ve işlem planı kullanılmamalıdır."
            ),
            kilit_asamasi="sağlayıcı günlük bar tazeliği",
            sonraki_kontrol_zamani=sonraki_tazelik_kontrol_zamani(
                simdi=an,
                politika=politika,
            ),
        )

    if son == beklenen and beklenen != bugun and _is_gunu_mu(bugun, politika):
        durum = BEKLEMEDE
        aciklama = (
            f"Son tamamlanmış günlük bar {son}. Bugünkü seans henüz kapanmadığı veya "
            "sağlayıcıya düşmediği için bu tarih beklenen değerdir."
        )
    else:
        durum = GUNCEL
        aciklama = (
            f"Son günlük bar {son}; beklenen tamamlanmış işlem günüyle eşleşiyor."
        )

    return DataFreshnessResult(
        durum=durum,
        son_veri_tarihi=son,
        beklenen_tarih=beklenen,
        is_gunu_gecikmesi=0,
        kilitli=False,
        aciklama=aciklama,
        kilit_asamasi="doğrulandı",
        sonraki_kontrol_zamani=None,
    )


def toplu_veri_tazeligini_degerlendir(
    veriler: Mapping[str, pd.DataFrame],
    *,
    simdi: datetime | None = None,
    politika: DataFreshnessPolicy = DataFreshnessPolicy(),
) -> BatchDataFreshnessResult:
    beklenen = beklenen_son_tamamlanmis_islem_gunu(simdi, politika)
    tarihler: list[date] = []
    guncel = 0
    eski = 0
    veri_yok = 0
    kapanis_bekleyen = 0

    for veri in veriler.values():
        sonuc = gunluk_veri_tazeligini_degerlendir(
            veri,
            simdi=simdi,
            politika=politika,
        )
        if sonuc.son_veri_tarihi is not None:
            tarihler.append(sonuc.son_veri_tarihi)
        if sonuc.durum == VERI_YOK:
            veri_yok += 1
        elif sonuc.kilitli:
            eski += 1
        else:
            guncel += 1
            if sonuc.durum == BEKLEMEDE:
                kapanis_bekleyen += 1

    toplam = len(veriler)
    kullanilabilir = guncel
    kilitli = toplam == 0 or kullanilabilir == 0

    if toplam == 0:
        durum = VERI_YOK
        aciklama = "Toplu taramada doğrulanabilir günlük veri yok."
    elif kilitli:
        durum = ESKI
        aciklama = (
            f"{toplam} sembolün tamamı eski/uyumsuz veya boş. "
            "Tarama güvenlik nedeniyle durdurulmalıdır."
        )
    elif eski > 0 or veri_yok > 0:
        durum = GUNCEL
        aciklama = (
            f"{toplam} sembolün {guncel} tanesi kullanılabilir. "
            f"{eski} eski/uyumsuz ve {veri_yok} boş sembol analiz dışı bırakılmalıdır."
        )
    elif kapanis_bekleyen > 0:
        durum = BEKLEMEDE
        aciklama = (
            f"{toplam} sembolün tamamı kullanılabilir. "
            f"{kapanis_bekleyen} sembolde bugünkü gün içi/kısmi bar analize "
            "yansıtılıyor; tamamlanmış kapanış verisi henüz bekleniyor."
        )
    else:
        durum = GUNCEL
        aciklama = (
            f"{toplam} sembolün tamamı güncel ve kullanılabilir."
        )

    return BatchDataFreshnessResult(
        durum=durum,
        beklenen_tarih=beklenen,
        en_eski_tarih=min(tarihler) if tarihler else None,
        en_yeni_tarih=max(tarihler) if tarihler else None,
        toplam_sembol=toplam,
        guncel_sembol=guncel,
        eski_sembol=eski,
        veri_yok_sembol=veri_yok,
        kilitli=kilitli,
        aciklama=aciklama,
        kilit_asamasi=(
            "referans/toplu günlük veri tazeliği"
            if kilitli
            else (
                "kısmi sembol izolasyonu"
                if eski > 0 or veri_yok > 0
                else "doğrulandı"
            )
        ),
        sonraki_kontrol_zamani=(
            sonraki_tazelik_kontrol_zamani(
                simdi=simdi,
                politika=politika,
            )
            if kilitli or kapanis_bekleyen > 0
            else None
        ),
    )


def _yerel_zaman(
    simdi: datetime | None,
    politika: DataFreshnessPolicy,
) -> datetime:
    if simdi is None:
        return datetime.now(politika.zaman_bolgesi)
    if simdi.tzinfo is None:
        return simdi.replace(tzinfo=politika.zaman_bolgesi)
    return simdi.astimezone(politika.zaman_bolgesi)


def _is_gunu_mu(gun: date, politika: DataFreshnessPolicy) -> bool:
    return gun.weekday() < 5 and gun not in set(politika.kapali_tarihler)


def _onceki_is_gunu(gun: date, politika: DataFreshnessPolicy) -> date:
    aday = gun - timedelta(days=1)
    while not _is_gunu_mu(aday, politika):
        aday -= timedelta(days=1)
    return aday


def _is_gunu_mesafesi(
    baslangic: date,
    bitis: date,
    politika: DataFreshnessPolicy,
) -> int:
    if baslangic >= bitis:
        return 0
    sayi = 0
    aday = baslangic + timedelta(days=1)
    while aday <= bitis:
        if _is_gunu_mu(aday, politika):
            sayi += 1
        aday += timedelta(days=1)
    return sayi