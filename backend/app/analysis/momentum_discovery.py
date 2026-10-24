from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Callable, Iterable

import numpy as np
import pandas as pd

from ..data.batch_market_data import (
    BatchMarketDataResult,
    referans_fiyat_verisi_getir,
    toplu_fiyat_verisi_getir,
)
from ..data.data_freshness import BatchDataFreshnessResult, toplu_veri_tazeligini_degerlendir
from ..history.momentum_history import MomentumHistoryStore
from .bist_universe import BistUniverseRepository
from .market_scanner import (
    EVREN_IZLEME_LISTESI,
    EVREN_OZEL_LISTE,
    TARAMA_EVRENLERI,
    MarketScanRequest,
    tarama_evreni_yukle,
)
from .stock_analyzer import StockAnalyzer, StockAnalyzerError
from .trend_scan_policy import (
    REJIM_POZITIF,
    REJIM_RISKLI,
    REJIM_SECICI,
    rejime_gore_trend_politikasi,
    trend_adayini_degerlendir,
)


SINIF_SIKISMA = "E0 — Sıkışma Oluşuyor"
SINIF_HACIM_BIRIKIMI = "E1 — Hacim Birikimi Başladı"
SINIF_DIRENCE_YAKLASIYOR = "E2 — Dirence Yaklaşıyor"
SINIF_ERKEN_UYARI = "E3 — Kırılım Öncesi Erken Uyarı"
# Geriye dönük içe aktarma uyumluluğu.
SINIF_ERKEN_KESIF = SINIF_ERKEN_UYARI
SINIF_KIRILIM = "B — Kırılım Başladı"
SINIF_ISLEME_HAZIR = "C — İşleme Hazır Aday"
SINIF_ASIRI_YUKSELMIS = "D — Aşırı Yükselmiş"
SINIF_KALICI_HAZIRLIK = "K — Kalıcı Hazırlık Adayı"
SINIF_IZLEME_DISI = "İzleme Dışı"

HAZIRLIK_SINIFLARI = (
    SINIF_SIKISMA,
    SINIF_HACIM_BIRIKIMI,
    SINIF_DIRENCE_YAKLASIYOR,
    SINIF_ERKEN_UYARI,
    SINIF_KALICI_HAZIRLIK,
)
GORUNEN_SINIFLAR = (
    SINIF_ISLEME_HAZIR,
    SINIF_KIRILIM,
    SINIF_ERKEN_UYARI,
    SINIF_DIRENCE_YAKLASIYOR,
    SINIF_HACIM_BIRIKIMI,
    SINIF_SIKISMA,
    SINIF_KALICI_HAZIRLIK,
)


class MomentumDiscoveryError(Exception):
    """Momentum keşif taraması hazırlanamadığında kullanılır."""


@dataclass(frozen=True)
class MomentumDiscoveryRequest:
    evren: str = "BIST Tüm"
    maksimum_aday: int = 25
    minimum_skor: int = 55
    ozel_semboller: tuple[str, ...] = ()
    internetten_evren_guncelle: bool = True
    piyasa_rejimi: str | None = None

    def __post_init__(self) -> None:
        if self.evren not in TARAMA_EVRENLERI:
            raise ValueError(f"Geçersiz tarama evreni: {self.evren}")
        if not 1 <= self.maksimum_aday <= 100:
            raise ValueError("Maksimum aday sayısı 1 ile 100 arasında olmalıdır.")
        if not 0 <= self.minimum_skor <= 100:
            raise ValueError("Minimum momentum skoru 0 ile 100 arasında olmalıdır.")
        if self.piyasa_rejimi not in (
            None,
            REJIM_POZITIF,
            REJIM_SECICI,
            REJIM_RISKLI,
        ):
            raise ValueError(
                f"Desteklenmeyen piyasa rejimi: {self.piyasa_rejimi}"
            )


@dataclass(frozen=True)
class MomentumCandidate:
    sembol: str
    analiz_tarihi: str
    kapanis: float
    momentum_skoru: int
    sinif: str
    goreceli_guc_puani: int
    fiyat_ivmesi_puani: int
    hacim_birikimi_puani: int
    kirilim_hazirligi_puani: int
    trend_puani: int
    likidite_puani: int
    risk_kalitesi_puani: int
    getiri_5g: float
    getiri_20g: float
    getiri_60g: float
    hacim_orani: float
    yirmi_gunluk_zirve_uzakligi: float
    ortalama_tl_hacim: float
    rsi14: float
    atr_yuzde: float
    teknik_skor: int
    teknik_gorunum: str
    risk_odul_orani: float
    risk_odul_uygun: bool
    kirilim: bool
    sikisma: bool
    asiri_uzamis: bool
    pozitif_nedenler: tuple[str, ...]
    riskler: tuple[str, ...]
    yakin_direnc: float = 0.0
    goreceli_guc_egimi: float = 0.0
    hacim_egimi: float = 0.0
    rsi_egimi: float = 0.0
    macd_histogram_egimi: float = 0.0
    hazirlik_durumu: str = ""
    listedeki_gun: int = 1
    ilk_gorulme_tarihi: str = ""
    ilk_gorulme_fiyati: float = 0.0
    ilk_gorulmeden_getiri: float = 0.0
    kirilim_tetik_seviyesi: float = 0.0
    sinyal_gecmisi: tuple[str, ...] = ()
    kalici_hazirlik: bool = False
    son_hazirlik_sinyali_tarihi: str = ""
    son_guclu_sinyal_tarihi: str = ""
    izleme_disi_nedeni: str = ""


@dataclass(frozen=True)
class MomentumFailure:
    sembol: str
    hata: str


@dataclass(frozen=True)
class MomentumDiscoveryResult:
    evren_adi: str
    evren_kaynagi: str
    evren_tarihi: str
    evren_sembol_sayisi: int
    basarili_sayisi: int
    adaylar: tuple[MomentumCandidate, ...]
    asiri_yukselmisler: tuple[MomentumCandidate, ...]
    izleme_disi: tuple[MomentumCandidate, ...]
    hatalar: tuple[MomentumFailure, ...]
    kayit_yolu: str | None = None
    veri_tazeligi: BatchDataFreshnessResult | None = None
    piyasa_rejimi: str | None = None
    trend_politikasi_elenenler: tuple[MomentumCandidate, ...] = ()
    on_tazelik_kontrolu: bool = False
    on_tazelik_referans_sembol: str | None = None
    toplu_tarama_baslatildi: bool = False
    indirilen_sembol_sayisi: int = 0
    analiz_edilen_sembol_sayisi: int = 0
    veri_hatasi_sayisi: int = 0
    toplam_sure_saniye: float = 0.0
    yeniden_deneme_sayisi: int = 0
    veri_kaynagi: str = "birincil"
    tazelik_kilit_asamasi: str = ""
    sonraki_kontrol_zamani: str = ""

    @property
    def erken_kesif_sayisi(self) -> int:
        return sum(a.sinif in HAZIRLIK_SINIFLARI for a in self.adaylar)

    def sinif_sayisi(self, sinif: str) -> int:
        return sum(a.sinif == sinif for a in self.adaylar)

    @property
    def kirilim_sayisi(self) -> int:
        return sum(a.sinif == SINIF_KIRILIM for a in self.adaylar)

    @property
    def isleme_hazir_sayisi(self) -> int:
        return sum(a.sinif == SINIF_ISLEME_HAZIR for a in self.adaylar)


ProgressCallback = Callable[[int, int, str], None]
StatusCallback = Callable[[str], None]
DataFetcher = Callable[..., BatchMarketDataResult]


class MomentumDiscoveryEngine:
    """OHLCV verilerinden kesitsel momentum ve erken kırılım skoru üretir."""

    def __init__(self, analiz_motoru: StockAnalyzer | None = None) -> None:
        self._analiz_motoru = analiz_motoru or StockAnalyzer()

    def analiz_et(
        self,
        veriler: dict[str, pd.DataFrame],
        ilerleme_bildirimi: ProgressCallback | None = None,
    ) -> tuple[tuple[MomentumCandidate, ...], tuple[MomentumFailure, ...]]:
        if not veriler:
            return (), ()

        hamlar: dict[str, dict[str, object]] = {}
        hatalar: list[MomentumFailure] = []
        semboller = tuple(sorted(veriler))

        for sira, sembol in enumerate(semboller, start=1):
            if ilerleme_bildirimi is not None:
                ilerleme_bildirimi(sira, len(semboller), sembol)
            try:
                hamlar[sembol] = _ham_momentum_olcutleri(veriler[sembol])
            except (ValueError, KeyError, TypeError) as hata:
                hatalar.append(MomentumFailure(sembol=sembol, hata=str(hata)))

        if not hamlar:
            return (), tuple(hatalar)

        goreceli_seri = pd.Series(
            {sembol: float(ham["goreceli_ham"]) for sembol, ham in hamlar.items()},
            dtype=float,
        )
        goreceli_egim_seri = pd.Series(
            {
                sembol: float(ham["goreceli_egim_ham"])
                for sembol, ham in hamlar.items()
            },
            dtype=float,
        )
        yuzdelikler = goreceli_seri.rank(pct=True, method="average")
        egim_yuzdelikleri = goreceli_egim_seri.rank(pct=True, method="average")

        adaylar: list[MomentumCandidate] = []
        for sembol, ham in hamlar.items():
            try:
                teknik = self._analiz_motoru.veriden_analiz_et(
                    sembol=sembol,
                    fiyat_verisi=veriler[sembol],
                )
                adaylar.append(
                    _adayi_olustur(
                        sembol=sembol,
                        ham=ham,
                        goreceli_yuzdelik=float(yuzdelikler.loc[sembol]),
                        goreceli_egim_yuzdelik=float(egim_yuzdelikleri.loc[sembol]),
                        teknik=teknik,
                    )
                )
            except (ValueError, StockAnalyzerError) as hata:
                hatalar.append(MomentumFailure(sembol=sembol, hata=str(hata)))

        adaylar.sort(
            key=lambda aday: (
                _sinif_onceligi(aday.sinif),
                -aday.momentum_skoru,
                -aday.teknik_skor,
                aday.sembol,
            )
        )
        return tuple(adaylar), tuple(hatalar)


class MomentumDiscoveryService:
    """Evren, toplu veri, momentum analizi ve geçmiş kaydını birleştirir."""

    def __init__(
        self,
        evren_repository: BistUniverseRepository | None = None,
        veri_getirici: DataFetcher = toplu_fiyat_verisi_getir,
        motor: MomentumDiscoveryEngine | None = None,
        izleme_listesi_yolu: str | Path | None = None,
        gecmis_deposu: MomentumHistoryStore | None = None,
        veri_tazeligi_kilidi_aktif: bool | None = None,
        on_tazelik_getirici: DataFetcher | None = None,
        on_tazelik_azami_yeniden_deneme: int = 2,
    ) -> None:
        backend = Path(__file__).resolve().parents[2]
        self._evren_repository = evren_repository or BistUniverseRepository()
        self._veri_getirici = veri_getirici
        self._veri_tazeligi_kilidi_aktif = (
            veri_getirici is toplu_fiyat_verisi_getir
            if veri_tazeligi_kilidi_aktif is None
            else bool(veri_tazeligi_kilidi_aktif)
        )
        self._motor = motor or MomentumDiscoveryEngine()
        self._on_tazelik_getirici = (
            on_tazelik_getirici or referans_fiyat_verisi_getir
        )
        self._izleme_listesi_yolu = Path(izleme_listesi_yolu) if (
            izleme_listesi_yolu is not None
        ) else backend / "watchlists" / "favoriler.txt"
        self._gecmis_deposu = gecmis_deposu or MomentumHistoryStore()
        if on_tazelik_azami_yeniden_deneme < 0:
            raise ValueError(
                "Ön tazelik azami yeniden deneme sayısı negatif olamaz."
            )
        self._on_tazelik_azami_yeniden_deneme = int(
            on_tazelik_azami_yeniden_deneme
        )

    def calistir(
        self,
        istek: MomentumDiscoveryRequest,
        ilerleme_bildirimi: ProgressCallback | None = None,
        durum_bildirimi: StatusCallback | None = None,
    ) -> MomentumDiscoveryResult:
        baslangic_zamani = perf_counter()

        def durum_bildir(mesaj: str) -> None:
            if durum_bildirimi is not None:
                durum_bildirimi(mesaj)

        try:
            durum_bildir("Tarama evreni hazırlanıyor...")
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
            on_tazelik_referans_sembol: str | None = None
            if self._veri_tazeligi_kilidi_aktif:
                on_tazelik_referans_sembol = semboller[0]
                durum_bildir(
                    f"{on_tazelik_referans_sembol} ile ön tazelik kontrolü yapılıyor..."
                )
                on_yeniden_deneme = 0
                while True:
                    on_veri_sonucu = self._on_tazelik_getirici(
                        on_tazelik_referans_sembol,
                        islem_gunu=5,
                        indirme_donemi="1mo",
                    )
                    on_veri_tazeligi = toplu_veri_tazeligini_degerlendir(
                        on_veri_sonucu.veriler
                    )
                    if not on_veri_tazeligi.kilitli:
                        break
                    if (
                        on_yeniden_deneme
                        >= self._on_tazelik_azami_yeniden_deneme
                    ):
                        break
                    on_yeniden_deneme += 1
                    durum_bildir(
                        "Referans sembol verisi güncel değil; "
                        f"kontrollü yeniden deneme "
                        f"{on_yeniden_deneme}/"
                        f"{self._on_tazelik_azami_yeniden_deneme}..."
                    )

                if on_veri_tazeligi.kilitli:
                    on_hatalar = tuple(
                        MomentumFailure(
                            sembol=hata.sembol,
                            hata=hata.hata,
                        )
                        for hata in on_veri_sonucu.hatalar
                    )
                    return MomentumDiscoveryResult(
                        evren_adi=istek.evren,
                        evren_kaynagi=kaynak,
                        evren_tarihi=tarih,
                        evren_sembol_sayisi=len(semboller),
                        basarili_sayisi=0,
                        adaylar=(),
                        asiri_yukselmisler=(),
                        izleme_disi=(),
                        hatalar=on_hatalar,
                        veri_tazeligi=on_veri_tazeligi,
                        piyasa_rejimi=istek.piyasa_rejimi,
                        on_tazelik_kontrolu=True,
                        on_tazelik_referans_sembol=(
                            on_tazelik_referans_sembol
                        ),
                        toplu_tarama_baslatildi=False,
                        indirilen_sembol_sayisi=len(
                            on_veri_sonucu.veriler
                        ),
                        analiz_edilen_sembol_sayisi=0,
                        veri_hatasi_sayisi=len(on_veri_sonucu.hatalar),
                        toplam_sure_saniye=round(
                            perf_counter() - baslangic_zamani,
                            3,
                        ),
                        yeniden_deneme_sayisi=on_yeniden_deneme,
                        veri_kaynagi="birincil referans veri yolu",
                        tazelik_kilit_asamasi=(
                            on_veri_tazeligi.kilit_asamasi
                        ),
                        sonraki_kontrol_zamani=(
                            on_veri_tazeligi.sonraki_kontrol_zamani.isoformat()
                            if on_veri_tazeligi.sonraki_kontrol_zamani
                            is not None
                            else ""
                        ),
                    )

            durum_bildir(
                f"{len(semboller)} sembol için toplu fiyat verisi indiriliyor..."
            )
            veri_sonucu = self._veri_getirici(
                semboller,
                islem_gunu=160,
                indirme_donemi="1y",
            )
            veri_tazeligi = toplu_veri_tazeligini_degerlendir(
                veri_sonucu.veriler
            )

            kullanilabilir_veriler = dict(veri_sonucu.veriler)
            tazelik_hatalari: list[MomentumFailure] = []

            if self._veri_tazeligi_kilidi_aktif:
                kullanilabilir_veriler = {}
                for sembol, veri in veri_sonucu.veriler.items():
                    sembol_tazeligi = toplu_veri_tazeligini_degerlendir(
                        {sembol: veri}
                    )
                    if sembol_tazeligi.kilitli:
                        tazelik_hatalari.append(
                            MomentumFailure(
                                sembol=sembol,
                                hata=(
                                    "Tazelik nedeniyle analiz dışı bırakıldı. "
                                    f"Son veri: {sembol_tazeligi.en_yeni_tarih or '-'}; "
                                    f"beklenen: {sembol_tazeligi.beklenen_tarih}."
                                ),
                            )
                        )
                        continue
                    kullanilabilir_veriler[sembol] = veri

            if (
                self._veri_tazeligi_kilidi_aktif
                and veri_tazeligi.kilitli
            ):
                tum_adaylar: tuple[MomentumCandidate, ...] = ()
                motor_hatalari: tuple[MomentumFailure, ...] = tuple(
                    tazelik_hatalari
                )
            else:
                if tazelik_hatalari:
                    durum_bildir(
                        f"{len(tazelik_hatalari)} sembol tazelik nedeniyle "
                        "analiz dışı bırakıldı; güncel sembollerle devam ediliyor..."
                    )
                durum_bildir("Momentum motoru çalışıyor...")
                tum_adaylar, motor_hatalari = self._motor.analiz_et(
                    kullanilabilir_veriler,
                    ilerleme_bildirimi=ilerleme_bildirimi,
                )
                motor_hatalari = tuple(tazelik_hatalari) + motor_hatalari
        except Exception as hata:
            if isinstance(hata, (KeyboardInterrupt, SystemExit)):
                raise
            raise MomentumDiscoveryError(str(hata)) from hata

        # Tüm adaylar geçmişle zenginleştirilir. Böylece bir hisse günlük
        # koşullarda kısa süreli İzleme Dışı kalsa bile önceki E0-E3
        # hazırlık sinyalleri kaybolmaz ve Kalıcı Hazırlık adayı olabilir.
        zengin = tuple(self._gecmis_deposu.zenginlestir(tum_adaylar))

        gorunen_adaylar = tuple(
            aday
            for aday in zengin
            if aday.sinif in GORUNEN_SINIFLAR
            and (
                aday.momentum_skoru >= istek.minimum_skor
                or aday.sinif == SINIF_KALICI_HAZIRLIK
            )
        )

        politika_elenenler: tuple[MomentumCandidate, ...] = ()
        if istek.piyasa_rejimi is not None:
            durum_bildir(
                f"{istek.piyasa_rejimi} piyasa rejimi filtresi uygulanıyor..."
            )
            politika = rejime_gore_trend_politikasi(istek.piyasa_rejimi)
            uygun_adaylar: list[MomentumCandidate] = []
            elenen_adaylar: list[MomentumCandidate] = []

            for aday in gorunen_adaylar:
                karar = trend_adayini_degerlendir(aday, politika)
                if karar.uygun:
                    uygun_adaylar.append(aday)
                    continue

                politika_nedeni = " ".join(karar.nedenler)
                mevcut_neden = aday.izleme_disi_nedeni.strip()
                birlesik_neden = " ".join(
                    parca
                    for parca in (mevcut_neden, politika_nedeni)
                    if parca
                )
                elenen_adaylar.append(
                    replace(
                        aday,
                        izleme_disi_nedeni=birlesik_neden,
                    )
                )

            gorunen_adaylar = tuple(uygun_adaylar)
            politika_elenenler = tuple(elenen_adaylar)

        adaylar = gorunen_adaylar[: istek.maksimum_aday]
        asiri = tuple(
            aday for aday in zengin if aday.sinif == SINIF_ASIRI_YUKSELMIS
        )[: istek.maksimum_aday]
        izleme_disi = tuple(
            aday for aday in zengin if aday.sinif == SINIF_IZLEME_DISI
        )

        kayit_yolu: str | None = None
        try:
            if zengin:
                kayit_yolu = str(self._gecmis_deposu.kaydet(zengin))
        except OSError:
            kayit_yolu = None

        veri_hatalari = tuple(
            MomentumFailure(sembol=hata.sembol, hata=hata.hata)
            for hata in veri_sonucu.hatalar
        )
        return MomentumDiscoveryResult(
            evren_adi=istek.evren,
            evren_kaynagi=kaynak,
            evren_tarihi=tarih,
            evren_sembol_sayisi=len(semboller),
            basarili_sayisi=len(zengin),
            adaylar=adaylar,
            asiri_yukselmisler=asiri,
            izleme_disi=izleme_disi,
            hatalar=veri_hatalari + motor_hatalari,
            kayit_yolu=kayit_yolu,
            veri_tazeligi=veri_tazeligi,
            piyasa_rejimi=istek.piyasa_rejimi,
            trend_politikasi_elenenler=politika_elenenler,
            on_tazelik_kontrolu=(
                self._veri_tazeligi_kilidi_aktif
            ),
            on_tazelik_referans_sembol=on_tazelik_referans_sembol,
            toplu_tarama_baslatildi=True,
            indirilen_sembol_sayisi=len(veri_sonucu.veriler),
            analiz_edilen_sembol_sayisi=len(zengin),
            veri_hatasi_sayisi=len(veri_hatalari + motor_hatalari),
            toplam_sure_saniye=round(
                perf_counter() - baslangic_zamani,
                3,
            ),
            yeniden_deneme_sayisi=(
                on_yeniden_deneme
                if self._veri_tazeligi_kilidi_aktif
                else 0
            ),
            veri_kaynagi="birincil toplu veri yolu",
            tazelik_kilit_asamasi=veri_tazeligi.kilit_asamasi,
            sonraki_kontrol_zamani=(
                veri_tazeligi.sonraki_kontrol_zamani.isoformat()
                if veri_tazeligi.sonraki_kontrol_zamani is not None
                else ""
            ),
        )


def momentum_aday_tablosu(
    sonuc: MomentumDiscoveryResult,
) -> tuple[dict[str, object], ...]:
    kayitlar: list[dict[str, object]] = []
    for sira, aday in enumerate(sonuc.adaylar, start=1):
        kayitlar.append(
            {
                "Sıra": sira,
                "Hisse": aday.sembol.removesuffix(".IS"),
                "Sınıf": aday.sinif,
                "Momentum": aday.momentum_skoru,
                "Teknik": aday.teknik_skor,
                "Son kapanış": round(aday.kapanis, 2),
                "5G (%)": round(aday.getiri_5g * 100, 2),
                "20G (%)": round(aday.getiri_20g * 100, 2),
                "Hacim": round(aday.hacim_orani, 2),
                "Yakın direnç": round(aday.yakin_direnc, 2),
                "Kırılım tetiği": round(aday.kirilim_tetik_seviyesi, 2),
                "Dirence uzaklık (%)": round(aday.yirmi_gunluk_zirve_uzakligi * 100, 2),
                "Hacim eğimi": round(aday.hacim_egimi, 2),
                "Göreceli güç eğimi (%)": round(aday.goreceli_guc_egimi * 100, 2),
                "Risk/Getiri": round(aday.risk_odul_orani, 2),
                "Listede gün": aday.listedeki_gun,
                "İlk görülmeden (%)": round(aday.ilk_gorulmeden_getiri * 100, 2),
                "Sinyal geçmişi": " → ".join(_yalin_sinif(item) for item in aday.sinyal_gecmisi),
                "Kalıcı hazırlık": "Evet" if aday.kalici_hazirlik else "Hayır",
            }
        )
    return tuple(kayitlar)



def _yalin_sinif(kayit: str) -> str:
    """Tarih içeren geçmiş kaydından yalnızca sınıf adını ayırır."""
    return kayit.split(" · ", 1)[-1] if " · " in kayit else kayit

def _ham_momentum_olcutleri(veri: pd.DataFrame) -> dict[str, object]:
    gerekli = {"High", "Low", "Close", "Volume"}
    eksik = gerekli.difference(veri.columns)
    if eksik:
        raise ValueError("Eksik fiyat sütunları: " + ", ".join(sorted(eksik)))
    if len(veri) < 80:
        raise ValueError("Momentum analizi için en az 80 işlem günü gereklidir.")

    close = pd.to_numeric(veri["Close"], errors="coerce")
    high = pd.to_numeric(veri["High"], errors="coerce")
    low = pd.to_numeric(veri["Low"], errors="coerce")
    volume = pd.to_numeric(veri["Volume"], errors="coerce")
    if close.isna().any() or high.isna().any() or low.isna().any() or volume.isna().any():
        raise ValueError("Fiyat veya hacim verisinde geçersiz değer var.")

    returns = close.pct_change()
    ema9 = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    ema55 = close.ewm(span=55, adjust=False).mean()

    delta = close.diff()
    kazanc = delta.clip(lower=0).rolling(14).mean()
    kayip = (-delta.clip(upper=0)).rolling(14).mean()
    rs = kazanc / kayip.replace(0, np.nan)
    rsi = (100 - (100 / (1 + rs))).fillna(50.0)

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    macd_sinyal = macd.ewm(span=9, adjust=False).mean()
    macd_hist = macd - macd_sinyal

    onceki_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - onceki_close).abs(),
            (low - onceki_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr14 = tr.rolling(14).mean()

    getiri_5 = float(close.iloc[-1] / close.iloc[-6] - 1)
    onceki_getiri_5 = float(close.iloc[-6] / close.iloc[-11] - 1)
    getiri_20 = float(close.iloc[-1] / close.iloc[-21] - 1)
    getiri_60 = float(close.iloc[-1] / close.iloc[-61] - 1)
    goreceli_egim = getiri_5 - onceki_getiri_5

    hacim20 = float(volume.tail(20).mean())
    hacim_orani = float(volume.iloc[-1] / hacim20) if hacim20 > 0 else 0.0
    yukselis_gunleri = returns.tail(10) > 0
    yukselis_hacim_orani = float(
        volume.tail(10)[yukselis_gunleri].mean() / hacim20
    ) if yukselis_gunleri.any() and hacim20 > 0 else 0.0
    son5_hacim_orani = float(volume.tail(5).mean() / hacim20) if hacim20 > 0 else 0.0
    onceki10_hacim = float(volume.iloc[-15:-5].mean())
    hacim_egimi = float(volume.tail(5).mean() / onceki10_hacim) if onceki10_hacim > 0 else 0.0

    yakin_direnc = float(high.shift(1).tail(20).max())
    zirve_uzakligi = max(0.0, yakin_direnc / float(close.iloc[-1]) - 1.0)
    kirilim = bool(float(close.iloc[-1]) > yakin_direnc * 1.002)

    son10_aralik = float((high.tail(10).max() - low.tail(10).min()) / close.iloc[-1])
    onceki20 = veri.iloc[-30:-10]
    onceki20_aralik = float(
        (pd.to_numeric(onceki20["High"]).max() - pd.to_numeric(onceki20["Low"]).min())
        / pd.to_numeric(onceki20["Close"]).iloc[-1]
    )
    sikisma_orani = son10_aralik / onceki20_aralik if onceki20_aralik > 0 else 1.0
    son5_atr = float(tr.tail(5).mean())
    onceki20_atr = float(tr.iloc[-25:-5].mean())
    atr_sikisma_orani = son5_atr / onceki20_atr if onceki20_atr > 0 else 1.0
    sikisma = bool(sikisma_orani <= 0.75 or atr_sikisma_orani <= 0.75)

    ema21_deger = float(ema21.iloc[-1])
    uzama = float(close.iloc[-1] / ema21_deger - 1) if ema21_deger > 0 else 0.0
    ema_farki = float(ema9.iloc[-1] / ema21_deger - 1.0) if ema21_deger > 0 else 0.0
    onceki_ema_farki = ema9 - ema21
    yakin_ema_kesisimi = bool(
        abs(ema_farki) <= 0.015
        or ((onceki_ema_farki.tail(4).shift(1) <= 0) & (onceki_ema_farki.tail(4) > 0)).any()
    )
    atr_yuzde = float(atr14.iloc[-1] / close.iloc[-1] * 100)
    ortalama_tl_hacim = float((close.tail(20) * volume.tail(20)).mean())
    yukselen_dip = bool(low.tail(10).min() > low.iloc[-20:-10].min())
    rsi_egimi = float(rsi.iloc[-1] - rsi.iloc[-4])
    macd_hist_egimi = float(macd_hist.iloc[-1] - macd_hist.iloc[-4])

    return {
        "analiz_tarihi": str(pd.Timestamp(veri.index[-1]).date()),
        "kapanis": float(close.iloc[-1]),
        "getiri_5": getiri_5,
        "onceki_getiri_5": onceki_getiri_5,
        "getiri_20": getiri_20,
        "getiri_60": getiri_60,
        "goreceli_ham": 0.45 * getiri_5 + 0.40 * getiri_20 + 0.15 * getiri_60,
        "goreceli_egim_ham": goreceli_egim,
        "hacim_orani": hacim_orani,
        "yukselis_hacim_orani": yukselis_hacim_orani,
        "son5_hacim_orani": son5_hacim_orani,
        "hacim_egimi": hacim_egimi,
        "yakin_direnc": yakin_direnc,
        "zirve_uzakligi": zirve_uzakligi,
        "kirilim": kirilim,
        "sikisma": sikisma,
        "sikisma_orani": sikisma_orani,
        "atr_sikisma_orani": atr_sikisma_orani,
        "ema9": float(ema9.iloc[-1]),
        "ema21": ema21_deger,
        "ema55": float(ema55.iloc[-1]),
        "ema_farki": ema_farki,
        "yakin_ema_kesisimi": yakin_ema_kesisimi,
        "rsi14": float(rsi.iloc[-1]),
        "rsi_egimi": rsi_egimi,
        "macd_histogram": float(macd_hist.iloc[-1]),
        "macd_histogram_egimi": macd_hist_egimi,
        "atr_yuzde": atr_yuzde,
        "ortalama_tl_hacim": ortalama_tl_hacim,
        "uzama": uzama,
        "yukselen_dip": yukselen_dip,
    }


def _adayi_olustur(
    sembol: str,
    ham: dict[str, object],
    goreceli_yuzdelik: float,
    goreceli_egim_yuzdelik: float,
    teknik: object,
) -> MomentumCandidate:
    pozitif: list[str] = []
    riskler: list[str] = []

    guc_yuzdelik = max(0.0, min(1.0, goreceli_yuzdelik))
    egim_yuzdelik = max(0.0, min(1.0, goreceli_egim_yuzdelik))
    goreceli = int(round(guc_yuzdelik * 14 + egim_yuzdelik * 6))
    goreceli_egim = float(ham["goreceli_egim_ham"])
    if goreceli >= 14:
        pozitif.append("BIST evrenine göre göreceli güç ve güç eğimi yüksek.")

    g5 = float(ham["getiri_5"])
    g20 = float(ham["getiri_20"])
    g60 = float(ham["getiri_60"])
    fiyat = 0
    fiyat += 4 if g5 > 0 else 0
    fiyat += 4 if g20 > 0 else 0
    fiyat += 3 if g60 > 0 else 0
    fiyat += 2 if goreceli_egim > 0 else 0
    fiyat += 2 if bool(ham["kirilim"]) else 0
    if fiyat >= 9:
        pozitif.append("Fiyat ivmesi kısa ve orta vadede olumlu.")

    hacim_orani = float(ham["hacim_orani"])
    son5_hacim = float(ham["son5_hacim_orani"])
    yukselis_hacim = float(ham["yukselis_hacim_orani"])
    hacim_egimi = float(ham["hacim_egimi"])
    hacim = 6 if hacim_orani >= 1.5 else 4 if hacim_orani >= 1.2 else 2 if hacim_orani >= 1.0 else 0
    hacim += 3 if yukselis_hacim >= 1.10 else 2 if yukselis_hacim >= 0.95 else 0
    hacim += 3 if son5_hacim >= 1.10 else 2 if son5_hacim >= 0.95 else 0
    hacim += 3 if hacim_egimi >= 1.20 else 2 if hacim_egimi >= 1.05 else 0
    hacim = min(hacim, 15)
    if hacim >= 8:
        pozitif.append("Hacim birikimi kademeli biçimde güçleniyor.")
    elif hacim_orani < 0.8 and hacim_egimi < 1.0:
        riskler.append("Güncel hacim ve hacim eğimi zayıf.")

    zirve = float(ham["zirve_uzakligi"])
    setup = 8 if bool(ham["kirilim"]) else 0
    setup += 5 if zirve <= 0.015 else 4 if zirve <= 0.03 else 2 if zirve <= 0.05 else 0
    setup += 4 if bool(ham["sikisma"]) else 0
    setup += 2 if bool(ham["yakin_ema_kesisimi"]) else 0
    setup = min(setup, 15)
    if bool(ham["kirilim"]):
        pozitif.append("20 günlük direnç üzerinde kırılım oluştu.")
    elif zirve <= 0.03:
        pozitif.append("Fiyat 20 günlük dirence en fazla %3 uzakta.")
    if bool(ham["sikisma"]):
        pozitif.append("Fiyat veya ATR aralığında sıkışma var.")

    kapanis = float(ham["kapanis"])
    ema9 = float(ham["ema9"])
    ema21 = float(ham["ema21"])
    ema55 = float(ham["ema55"])
    trend = 0
    trend += 4 if kapanis > ema21 else 0
    trend += 4 if ema9 > ema21 else 0
    trend += 4 if ema21 > ema55 else 0
    trend += 3 if bool(ham["yukselen_dip"]) else 0
    if trend >= 11:
        pozitif.append("Trend yapısı yükselen ortalamalar ve diplerle destekleniyor.")
    elif trend <= 4:
        riskler.append("Trend yapısı henüz yeterince güçlü değil.")

    tl_hacim = float(ham["ortalama_tl_hacim"])
    likidite = 10 if tl_hacim >= 100_000_000 else 8 if tl_hacim >= 50_000_000 else 6 if tl_hacim >= 20_000_000 else 4 if tl_hacim >= 10_000_000 else 2 if tl_hacim >= 5_000_000 else 0
    if likidite <= 2:
        riskler.append("Ortalama TL hacmi düşük; giriş ve çıkış riski yüksek.")

    atr = float(ham["atr_yuzde"])
    uzama = float(ham["uzama"])
    rsi = float(ham["rsi14"])
    rsi_egimi = float(ham["rsi_egimi"])
    macd_egimi = float(ham["macd_histogram_egimi"])
    risk_kalitesi = 5 if atr <= 2.5 else 4 if atr <= 4 else 2 if atr <= 6 else 0
    risk_kalitesi += 3 if uzama <= 0.05 else 2 if uzama <= 0.10 else 0
    risk_kalitesi += 2 if 48 <= rsi <= 68 else 1 if 35 <= rsi <= 75 else 0
    risk_kalitesi = min(risk_kalitesi, 10)

    asiri = bool(g5 > 0.25 or uzama > 0.15 or rsi > 78)
    if asiri:
        riskler.append("Fiyat kısa vadede aşırı uzamış; peşinden koşma riski var.")

    toplam = int(round(goreceli + fiyat + hacim + setup + trend + likidite + risk_kalitesi))
    toplam = max(0, min(100, toplam))

    teknik_skor = int(getattr(getattr(teknik, "sinyal"), "skor"))
    teknik_gorunum = str(getattr(getattr(teknik, "sinyal"), "karar"))
    risk_plani = getattr(teknik, "risk_plani")
    rr = float(getattr(risk_plani, "risk_odul_orani"))
    rr_uygun = bool(getattr(risk_plani, "filtreyi_gecti"))

    hacim_birikiyor = bool(hacim >= 7 and (hacim_egimi >= 1.05 or son5_hacim >= 1.05))
    momentum_hazir = bool(48 <= rsi <= 68 and rsi_egimi > 0 and macd_egimi > 0)
    guc_hazir = bool(goreceli_egim > 0 and egim_yuzdelik >= 0.55)

    if asiri and toplam >= 55:
        sinif = SINIF_ASIRI_YUKSELMIS
    elif toplam >= 75 and bool(ham["kirilim"]) and teknik_skor >= 60 and rr_uygun:
        sinif = SINIF_ISLEME_HAZIR
    elif toplam >= 65 and bool(ham["kirilim"]):
        sinif = SINIF_KIRILIM
    elif (
        toplam >= 64
        and zirve <= 0.03
        and trend >= 8
        and hacim_birikiyor
        and momentum_hazir
        and guc_hazir
    ):
        sinif = SINIF_ERKEN_UYARI
    elif toplam >= 56 and zirve <= 0.05 and trend >= 8:
        sinif = SINIF_DIRENCE_YAKLASIYOR
    elif toplam >= 50 and hacim_birikiyor:
        sinif = SINIF_HACIM_BIRIKIMI
    elif toplam >= 45 and bool(ham["sikisma"]):
        sinif = SINIF_SIKISMA
    else:
        sinif = SINIF_IZLEME_DISI

    if sinif == SINIF_ERKEN_UYARI:
        hazirlik = "Yüksek: direnç, hacim, momentum ve göreceli güç birlikte hazırlanıyor."
    elif sinif == SINIF_DIRENCE_YAKLASIYOR:
        hazirlik = "Orta-yüksek: fiyat yakın dirence yaklaşıyor; hacim ve momentum teyidi izlenmeli."
    elif sinif == SINIF_HACIM_BIRIKIMI:
        hazirlik = "Orta: hacim birikimi var; fiyat yapısının dirence yaklaşması bekleniyor."
    elif sinif == SINIF_SIKISMA:
        hazirlik = "Başlangıç: fiyat/ATR sıkışması var; yön henüz kesinleşmedi."
    elif sinif == SINIF_KIRILIM:
        hazirlik = "Kırılım başladı; ayrıntılı işlem teyidi gerekli."
    elif sinif == SINIF_ISLEME_HAZIR:
        hazirlik = "Kırılım ve işlem koşulları birlikte doğrulandı."
    else:
        hazirlik = "Erken hazırlık koşulları yeterli değil."

    if not rr_uygun:
        riskler.append("Mevcut işlem planı minimum risk/ödül koşulunu karşılamıyor.")

    yakin_direnc = float(ham["yakin_direnc"])
    kirilim_tetik_seviyesi = yakin_direnc * 1.002 if yakin_direnc > 0 else 0.0
    izleme_disi_nedeni = _izleme_disi_nedeni(
        sinif=sinif,
        toplam=toplam,
        hacim_birikiyor=hacim_birikiyor,
        sikisma=bool(ham["sikisma"]),
        zirve_uzakligi=zirve,
        kirilim=bool(ham["kirilim"]),
        trend=trend,
    )

    return MomentumCandidate(
        sembol=sembol,
        analiz_tarihi=str(ham["analiz_tarihi"]),
        kapanis=kapanis,
        momentum_skoru=toplam,
        sinif=sinif,
        goreceli_guc_puani=goreceli,
        fiyat_ivmesi_puani=fiyat,
        hacim_birikimi_puani=hacim,
        kirilim_hazirligi_puani=setup,
        trend_puani=trend,
        likidite_puani=likidite,
        risk_kalitesi_puani=risk_kalitesi,
        getiri_5g=g5,
        getiri_20g=g20,
        getiri_60g=g60,
        hacim_orani=hacim_orani,
        yirmi_gunluk_zirve_uzakligi=zirve,
        ortalama_tl_hacim=tl_hacim,
        rsi14=rsi,
        atr_yuzde=atr,
        teknik_skor=teknik_skor,
        teknik_gorunum=teknik_gorunum,
        risk_odul_orani=rr,
        risk_odul_uygun=rr_uygun,
        kirilim=bool(ham["kirilim"]),
        sikisma=bool(ham["sikisma"]),
        asiri_uzamis=asiri,
        pozitif_nedenler=tuple(dict.fromkeys(pozitif)),
        riskler=tuple(dict.fromkeys(riskler)),
        yakin_direnc=yakin_direnc,
        goreceli_guc_egimi=goreceli_egim,
        hacim_egimi=hacim_egimi,
        rsi_egimi=rsi_egimi,
        macd_histogram_egimi=macd_egimi,
        hazirlik_durumu=hazirlik,
        kirilim_tetik_seviyesi=kirilim_tetik_seviyesi,
        izleme_disi_nedeni=izleme_disi_nedeni,
    )


def _izleme_disi_nedeni(
    *,
    sinif: str,
    toplam: int,
    hacim_birikiyor: bool,
    sikisma: bool,
    zirve_uzakligi: float,
    kirilim: bool,
    trend: int,
) -> str:
    if sinif != SINIF_IZLEME_DISI:
        return ""
    nedenler: list[str] = []
    if toplam < 45:
        nedenler.append(f"Momentum skoru {toplam}; görünür hazırlık sınıfı için en az 45 gerekli.")
    if not sikisma:
        nedenler.append("Fiyat/ATR sıkışması oluşmadı.")
    if not hacim_birikiyor:
        nedenler.append("Kademeli hacim birikimi koşulu oluşmadı.")
    if zirve_uzakligi > 0.05 and not kirilim:
        nedenler.append(f"Yakın dirence uzaklık %{zirve_uzakligi * 100:.2f}; E2 için en fazla %5 gerekli.")
    if trend < 8:
        nedenler.append(f"Trend puanı {trend}/15; hazırlık için yetersiz.")
    if not nedenler:
        nedenler.append("E0-E3, kırılım veya işleme hazır sınıflarının birleşik koşulları oluşmadı.")
    return " ".join(nedenler)


def _sinif_onceligi(sinif: str) -> int:
    return {
        SINIF_ISLEME_HAZIR: 0,
        SINIF_KIRILIM: 1,
        SINIF_ERKEN_UYARI: 2,
        SINIF_DIRENCE_YAKLASIYOR: 3,
        SINIF_HACIM_BIRIKIMI: 4,
        SINIF_SIKISMA: 5,
        SINIF_KALICI_HAZIRLIK: 6,
        SINIF_ASIRI_YUKSELMIS: 7,
        SINIF_IZLEME_DISI: 8,
    }.get(sinif, 9)