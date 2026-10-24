from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd

from ..data.batch_market_data import BatchMarketDataResult, toplu_fiyat_verisi_getir
from .bist_universe import BistUniverseRepository
from .market_scanner import MarketScanRequest, tarama_evreni_yukle
from .momentum_discovery import (
    HAZIRLIK_SINIFLARI,
    SINIF_ERKEN_UYARI,
    SINIF_ISLEME_HAZIR,
    SINIF_IZLEME_DISI,
    SINIF_KALICI_HAZIRLIK,
    SINIF_KIRILIM,
    MomentumCandidate,
    MomentumDiscoveryEngine,
    MomentumFailure,
)


class MomentumWalkForwardError(Exception):
    """Tarihsel momentum yeniden oynatması hazırlanamadığında kullanılır."""


@dataclass(frozen=True)
class MomentumWalkForwardRequest:
    evren: str = "BIST 100"
    kesim_tarihi: str = ""
    maksimum_aday: int = 25
    minimum_skor: int = 50
    ozel_semboller: tuple[str, ...] = ()
    internetten_evren_guncelle: bool = True
    ufuklar: tuple[int, ...] = (5, 10, 20)
    sinyal_gecmisi_adim_sayisi: int = 6
    sinyal_gecmisi_adim_bari: int = 5

    def __post_init__(self) -> None:
        if not self.kesim_tarihi:
            raise ValueError("Tarihsel yeniden oynatma için kesim tarihi gereklidir.")
        try:
            date.fromisoformat(self.kesim_tarihi)
        except ValueError as hata:
            raise ValueError("Kesim tarihi YYYY-AA-GG biçiminde olmalıdır.") from hata
        if not 1 <= self.maksimum_aday <= 100:
            raise ValueError("Maksimum aday sayısı 1 ile 100 arasında olmalıdır.")
        if not 0 <= self.minimum_skor <= 100:
            raise ValueError("Minimum momentum skoru 0 ile 100 arasında olmalıdır.")
        if not self.ufuklar or any(gun < 1 for gun in self.ufuklar):
            raise ValueError("İleri performans ufukları pozitif olmalıdır.")
        if not 1 <= self.sinyal_gecmisi_adim_sayisi <= 12:
            raise ValueError("Sinyal geçmişi adım sayısı 1 ile 12 arasında olmalıdır.")
        if not 1 <= self.sinyal_gecmisi_adim_bari <= 20:
            raise ValueError("Sinyal geçmişi bar aralığı 1 ile 20 arasında olmalıdır.")


@dataclass(frozen=True)
class MomentumSignalSnapshot:
    tarih: str
    sinif: str
    momentum_skoru: int
    kapanis: float
    yakin_direnc: float
    kirilim_tetik_seviyesi: float
    dirence_uzaklik: float
    izleme_disi_nedeni: str = ""


@dataclass(frozen=True)
class MomentumWalkForwardOutcome:
    aday: MomentumCandidate
    ileri_getiriler: tuple[tuple[int, float | None], ...]
    maksimum_olumlu_hareket: float | None
    maksimum_ters_hareket: float | None
    ileri_bar_sayisi: int = 0
    maksimum_fiyat: float | None = None
    maksimum_fiyat_tarihi: str = ""
    minimum_fiyat: float | None = None
    minimum_fiyat_tarihi: str = ""
    sinyal_gecmisi: tuple[MomentumSignalSnapshot, ...] = ()

    def getiri(self, gun: int) -> float | None:
        return dict(self.ileri_getiriler).get(gun)


@dataclass(frozen=True)
class MomentumWalkForwardResult:
    evren_adi: str
    evren_kaynagi: str
    evren_tarihi: str
    kesim_tarihi: str
    evren_sembol_sayisi: int
    basarili_sayisi: int
    sonuclar: tuple[MomentumWalkForwardOutcome, ...]
    izleme_disi: tuple[MomentumWalkForwardOutcome, ...]
    hatalar: tuple[MomentumFailure, ...]
    sinyal_gecmisi_hesaplandi: bool = False

    @property
    def guclu_hareket_sayisi(self) -> int:
        return sum(
            sonuc.maksimum_olumlu_hareket is not None
            and sonuc.maksimum_olumlu_hareket >= 0.10
            for sonuc in self.sonuclar
        )


DataFetcher = Callable[..., BatchMarketDataResult]


class MomentumWalkForwardEngine:
    """Gelecek barları gizleyerek tarihsel momentum adaylarını yeniden üretir."""

    def __init__(self, motor: MomentumDiscoveryEngine | None = None) -> None:
        self._motor = motor or MomentumDiscoveryEngine()

    def calistir(
        self,
        veriler: dict[str, pd.DataFrame],
        *,
        kesim_tarihi: str,
        ufuklar: Iterable[int] = (5, 10, 20),
        sinyal_gecmisi_olustur: bool = False,
        sinyal_gecmisi_adim_sayisi: int = 6,
        sinyal_gecmisi_adim_bari: int = 5,
    ) -> tuple[tuple[MomentumWalkForwardOutcome, ...], tuple[MomentumFailure, ...]]:
        kesim = pd.Timestamp(kesim_tarihi)
        ufuk = tuple(sorted(set(int(gun) for gun in ufuklar)))
        gecmisler: dict[str, pd.DataFrame] = {}
        tam_veriler: dict[str, pd.DataFrame] = {}
        hatalar: list[MomentumFailure] = []

        for sembol, veri in veriler.items():
            sirali = veri.sort_index().copy()
            tarih_indexi = pd.to_datetime(sirali.index)
            gecmis = sirali.loc[tarih_indexi <= kesim]
            gelecek = sirali.loc[tarih_indexi > kesim]
            if len(gecmis) < 80:
                hatalar.append(
                    MomentumFailure(
                        sembol=sembol,
                        hata=(
                            f"{kesim_tarihi} kesiminde yalnızca {len(gecmis)} "
                            "işlem günü var; en az 80 gerekli."
                        ),
                    )
                )
                continue
            if gelecek.empty:
                hatalar.append(
                    MomentumFailure(
                        sembol=sembol,
                        hata=f"{kesim_tarihi} sonrasında ileri performans verisi yok.",
                    )
                )
                continue
            gecmisler[sembol] = gecmis
            tam_veriler[sembol] = sirali

        adaylar, motor_hatalari = self._motor.analiz_et(gecmisler)
        hatalar.extend(motor_hatalari)
        gecmis_haritasi: dict[str, tuple[MomentumSignalSnapshot, ...]] = {}
        if sinyal_gecmisi_olustur and gecmisler:
            gecmis_haritasi = self._sinyal_gecmisi_olustur(
                gecmisler,
                adim_sayisi=sinyal_gecmisi_adim_sayisi,
                adim_bari=sinyal_gecmisi_adim_bari,
            )

        sonuclar: list[MomentumWalkForwardOutcome] = []
        azami_ufuk = max(ufuk)
        for aday in adaylar:
            sinyal_gecmisi = gecmis_haritasi.get(aday.sembol, ())
            aday = self._gecmisle_zenginlestir(aday, sinyal_gecmisi)
            tam = tam_veriler[aday.sembol]
            ileri = tam.loc[pd.to_datetime(tam.index) > kesim].head(azami_ufuk)
            kapanislar = pd.to_numeric(ileri["Close"], errors="coerce").dropna()
            baslangic = float(aday.kapanis)
            getiriler: list[tuple[int, float | None]] = []
            for gun in ufuk:
                deger = (
                    float(kapanislar.iloc[gun - 1] / baslangic - 1.0)
                    if len(kapanislar) >= gun and baslangic > 0
                    else None
                )
                getiriler.append((gun, deger))

            yuksekler = pd.to_numeric(
                ileri["High"] if "High" in ileri.columns else ileri["Close"],
                errors="coerce",
            ).dropna()
            dusukler = pd.to_numeric(
                ileri["Low"] if "Low" in ileri.columns else ileri["Close"],
                errors="coerce",
            ).dropna()
            if yuksekler.empty or dusukler.empty or baslangic <= 0:
                mfe = None
                mae = None
                maksimum_fiyat = None
                minimum_fiyat = None
                maksimum_tarih = ""
                minimum_tarih = ""
            else:
                maksimum_fiyat = float(yuksekler.max())
                minimum_fiyat = float(dusukler.min())
                mfe = float(maksimum_fiyat / baslangic - 1.0)
                # Azami ters hareket kullanıcıya pozitif risk büyüklüğü olarak gösterilir.
                mae = max(0.0, float(1.0 - minimum_fiyat / baslangic))
                maksimum_tarih = str(pd.Timestamp(yuksekler.idxmax()).date())
                minimum_tarih = str(pd.Timestamp(dusukler.idxmin()).date())

            sonuclar.append(
                MomentumWalkForwardOutcome(
                    aday=aday,
                    ileri_getiriler=tuple(getiriler),
                    maksimum_olumlu_hareket=mfe,
                    maksimum_ters_hareket=mae,
                    ileri_bar_sayisi=len(ileri),
                    maksimum_fiyat=maksimum_fiyat,
                    maksimum_fiyat_tarihi=maksimum_tarih,
                    minimum_fiyat=minimum_fiyat,
                    minimum_fiyat_tarihi=minimum_tarih,
                    sinyal_gecmisi=sinyal_gecmisi,
                )
            )

        sonuclar.sort(
            key=lambda sonuc: (
                _sinif_onceligi(sonuc.aday.sinif),
                -sonuc.aday.momentum_skoru,
                sonuc.aday.sembol,
            )
        )
        return tuple(sonuclar), tuple(hatalar)

    def _sinyal_gecmisi_olustur(
        self,
        gecmisler: dict[str, pd.DataFrame],
        *,
        adim_sayisi: int,
        adim_bari: int,
    ) -> dict[str, tuple[MomentumSignalSnapshot, ...]]:
        tum_tarihler = sorted(
            {
                pd.Timestamp(tarih)
                for veri in gecmisler.values()
                for tarih in pd.to_datetime(veri.index)
            }
        )
        if not tum_tarihler:
            return {}
        secili_tarihler: list[pd.Timestamp] = []
        son = len(tum_tarihler) - 1
        for sira in range(adim_sayisi - 1, -1, -1):
            indeks = son - sira * adim_bari
            if indeks >= 0:
                secili_tarihler.append(tum_tarihler[indeks])

        harita: dict[str, list[MomentumSignalSnapshot]] = {
            sembol: [] for sembol in gecmisler
        }
        for tarih in secili_tarihler:
            kesit = {
                sembol: veri.loc[pd.to_datetime(veri.index) <= tarih]
                for sembol, veri in gecmisler.items()
                if len(veri.loc[pd.to_datetime(veri.index) <= tarih]) >= 80
            }
            adaylar, _ = self._motor.analiz_et(kesit)
            for aday in adaylar:
                harita.setdefault(aday.sembol, []).append(
                    MomentumSignalSnapshot(
                        tarih=aday.analiz_tarihi,
                        sinif=aday.sinif,
                        momentum_skoru=aday.momentum_skoru,
                        kapanis=aday.kapanis,
                        yakin_direnc=aday.yakin_direnc,
                        kirilim_tetik_seviyesi=aday.kirilim_tetik_seviyesi,
                        dirence_uzaklik=aday.yirmi_gunluk_zirve_uzakligi,
                        izleme_disi_nedeni=aday.izleme_disi_nedeni,
                    )
                )
        return {sembol: tuple(kayitlar) for sembol, kayitlar in harita.items()}

    @staticmethod
    def _gecmisle_zenginlestir(
        aday: MomentumCandidate,
        gecmis: tuple[MomentumSignalSnapshot, ...],
    ) -> MomentumCandidate:
        if not gecmis:
            return aday
        sinyal_gecmisi = tuple(f"{x.tarih} · {x.sinif}" for x in gecmis)
        son_hazirlik = ""
        son_guclu = ""
        for kayit in gecmis:
            if kayit.sinif in HAZIRLIK_SINIFLARI:
                son_hazirlik = kayit.tarih
            if kayit.sinif in {SINIF_ERKEN_UYARI, SINIF_KIRILIM, SINIF_ISLEME_HAZIR}:
                son_guclu = kayit.tarih

        kalici = False
        if aday.sinif == SINIF_IZLEME_DISI:
            hazirliklar = [x for x in gecmis if x.sinif in HAZIRLIK_SINIFLARI]
            if len(hazirliklar) >= 2:
                son_tarih = pd.Timestamp(hazirliklar[-1].tarih)
                kalici = (pd.Timestamp(aday.analiz_tarihi) - son_tarih).days <= 10
        if kalici:
            return replace(
                aday,
                sinif=SINIF_KALICI_HAZIRLIK,
                kalici_hazirlik=True,
                sinyal_gecmisi=sinyal_gecmisi,
                son_hazirlik_sinyali_tarihi=son_hazirlik,
                son_guclu_sinyal_tarihi=son_guclu,
                hazirlik_durumu=(
                    "Kalıcı hazırlık: son haftalarda tekrarlayan E0-E3 sinyalleri "
                    "nedeniyle günlük sınıf kaybına rağmen izleme sürüyor."
                ),
            )
        return replace(
            aday,
            sinyal_gecmisi=sinyal_gecmisi,
            son_hazirlik_sinyali_tarihi=son_hazirlik,
            son_guclu_sinyal_tarihi=son_guclu,
        )


class MomentumWalkForwardService:
    """Evren ve toplu veri katmanını tarihsel yeniden oynatmayla birleştirir."""

    def __init__(
        self,
        evren_repository: BistUniverseRepository | None = None,
        veri_getirici: DataFetcher = toplu_fiyat_verisi_getir,
        motor: MomentumWalkForwardEngine | None = None,
        izleme_listesi_yolu: str | Path | None = None,
    ) -> None:
        backend = Path(__file__).resolve().parents[2]
        self._evren_repository = evren_repository or BistUniverseRepository()
        self._veri_getirici = veri_getirici
        self._motor = motor or MomentumWalkForwardEngine()
        self._izleme_listesi_yolu = Path(izleme_listesi_yolu) if (
            izleme_listesi_yolu is not None
        ) else backend / "watchlists" / "favoriler.txt"

    def calistir(self, istek: MomentumWalkForwardRequest) -> MomentumWalkForwardResult:
        try:
            market_istegi = MarketScanRequest(
                evren=istek.evren,
                profil_adi="gevsek",
                maksimum_aday=istek.maksimum_aday,
                ozel_semboller=istek.ozel_semboller,
                internetten_evren_guncelle=istek.internetten_evren_guncelle,
            )
            semboller, kaynak, tarih = tarama_evreni_yukle(
                market_istegi,
                evren_repository=self._evren_repository,
                izleme_listesi_yolu=self._izleme_listesi_yolu,
            )
            veri_sonucu = self._veri_getirici(
                semboller,
                islem_gunu=420,
                indirme_donemi="2y",
            )
            # Otomatik sınıf zinciri, hesap yükünü sınırlamak için küçük özel/
            # kayıtlı listelerde hazırlanır. Büyük evrenlerde kesim sınıfı ve
            # ileri performans yine eksiksiz hesaplanır.
            gecmis_olustur = len(semboller) <= 10
            tum_sonuclar, motor_hatalari = self._motor.calistir(
                veri_sonucu.veriler,
                kesim_tarihi=istek.kesim_tarihi,
                ufuklar=istek.ufuklar,
                sinyal_gecmisi_olustur=gecmis_olustur,
                sinyal_gecmisi_adim_sayisi=istek.sinyal_gecmisi_adim_sayisi,
                sinyal_gecmisi_adim_bari=istek.sinyal_gecmisi_adim_bari,
            )
        except Exception as hata:
            if isinstance(hata, (KeyboardInterrupt, SystemExit)):
                raise
            raise MomentumWalkForwardError(str(hata)) from hata

        gorunen = tuple(
            sonuc
            for sonuc in tum_sonuclar
            if sonuc.aday.sinif != SINIF_IZLEME_DISI
            and (
                sonuc.aday.momentum_skoru >= istek.minimum_skor
                or sonuc.aday.sinif == SINIF_KALICI_HAZIRLIK
            )
        )[: istek.maksimum_aday]
        izleme_disi = tuple(
            sonuc for sonuc in tum_sonuclar if sonuc.aday.sinif == SINIF_IZLEME_DISI
        )
        veri_hatalari = tuple(
            MomentumFailure(sembol=hata.sembol, hata=hata.hata)
            for hata in veri_sonucu.hatalar
        )
        return MomentumWalkForwardResult(
            evren_adi=istek.evren,
            evren_kaynagi=kaynak,
            evren_tarihi=tarih,
            kesim_tarihi=istek.kesim_tarihi,
            evren_sembol_sayisi=len(semboller),
            basarili_sayisi=len(tum_sonuclar),
            sonuclar=gorunen,
            izleme_disi=izleme_disi,
            hatalar=veri_hatalari + motor_hatalari,
            sinyal_gecmisi_hesaplandi=gecmis_olustur,
        )


def walk_forward_tablosu(
    sonuc: MomentumWalkForwardResult,
) -> tuple[dict[str, object], ...]:
    kayitlar: list[dict[str, object]] = []
    for sira, item in enumerate(sonuc.sonuclar, start=1):
        aday = item.aday
        kayitlar.append(
            {
                "Sıra": sira,
                "Hisse": aday.sembol.removesuffix(".IS"),
                "Kesim sınıfı": aday.sinif,
                "Momentum": aday.momentum_skoru,
                "Sinyal fiyatı": round(aday.kapanis, 2),
                "Yakın direnç": round(aday.yakin_direnc, 2),
                "Kırılım tetiği": round(aday.kirilim_tetik_seviyesi, 2),
                "Dirence uzaklık (%)": _yuzde(aday.yirmi_gunluk_zirve_uzakligi),
                "5G kapanış (%)": _yuzde(item.getiri(5)),
                "10G kapanış (%)": _yuzde(item.getiri(10)),
                "20G kapanış (%)": _yuzde(item.getiri(20)),
                "İleri bar": item.ileri_bar_sayisi,
                "Dönem içi en yüksek": _yuvarla(item.maksimum_fiyat),
                "En yüksek tarih": item.maksimum_fiyat_tarihi or None,
                "Gerçek azami yükseliş (%)": _yuzde(item.maksimum_olumlu_hareket),
                "Dönem içi en düşük": _yuvarla(item.minimum_fiyat),
                "En düşük tarih": item.minimum_fiyat_tarihi or None,
                "Azami ters hareket (%)": _yuzde(item.maksimum_ters_hareket),
                "Sinyal geçmişi": " → ".join(
                    _kisa_sinif(x.sinif) for x in item.sinyal_gecmisi
                ),
                "İzleme dışı nedeni": aday.izleme_disi_nedeni or None,
            }
        )
    return tuple(kayitlar)


def walk_forward_izleme_disi_tablosu(
    sonuc: MomentumWalkForwardResult,
) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "Hisse": item.aday.sembol.removesuffix(".IS"),
            "Momentum": item.aday.momentum_skoru,
            "Sinyal fiyatı": round(item.aday.kapanis, 2),
            "Yakın direnç": round(item.aday.yakin_direnc, 2),
            "Dirence uzaklık (%)": _yuzde(item.aday.yirmi_gunluk_zirve_uzakligi),
            "Neden": item.aday.izleme_disi_nedeni,
            "Sinyal geçmişi": " → ".join(
                _kisa_sinif(x.sinif) for x in item.sinyal_gecmisi
            ),
        }
        for item in sonuc.izleme_disi
    )


def sinyal_gecmisi_tablosu(
    item: MomentumWalkForwardOutcome,
) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "Tarih": kayit.tarih,
            "Sınıf": kayit.sinif,
            "Momentum": kayit.momentum_skoru,
            "Fiyat": round(kayit.kapanis, 2),
            "Yakın direnç": round(kayit.yakin_direnc, 2),
            "Kırılım tetiği": round(kayit.kirilim_tetik_seviyesi, 2),
            "Dirence uzaklık (%)": _yuzde(kayit.dirence_uzaklik),
            "İzleme dışı nedeni": kayit.izleme_disi_nedeni or None,
        }
        for kayit in item.sinyal_gecmisi
    )


def _kisa_sinif(sinif: str) -> str:
    return sinif.split(" — ", 1)[0]


def _sinif_onceligi(sinif: str) -> int:
    return {
        SINIF_ISLEME_HAZIR: 0,
        SINIF_KIRILIM: 1,
        SINIF_ERKEN_UYARI: 2,
        SINIF_KALICI_HAZIRLIK: 3,
        SINIF_IZLEME_DISI: 9,
    }.get(sinif, 4)


def _yuzde(deger: float | None) -> float | None:
    return round(deger * 100.0, 2) if deger is not None else None


def _yuvarla(deger: float | None) -> float | None:
    return round(deger, 2) if deger is not None else None
