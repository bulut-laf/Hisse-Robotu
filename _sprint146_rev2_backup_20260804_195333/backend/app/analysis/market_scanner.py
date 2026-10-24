from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable

import pandas as pd

from .bist_universe import (
    EVREN_KODLARI,
    BistUniverse,
    BistUniverseRepository,
)
from .scan_filter import FilteredScanResult, tarama_sonucunu_filtrele
from .scan_profiles import ScanProfile, profil_al
from .stock_analyzer import StockAnalysisResult
from .stock_scanner import BatchStockScanner
from .watchlist import izleme_listesi_yukle
from ..compliance.vbts_scan_filter import (
    VbtsDatasetNotUsableError,
    VbtsScanFilter,
)
from ..data.data_freshness import (
    BatchDataFreshnessResult,
    toplu_veri_tazeligini_degerlendir,
)


EVREN_IZLEME_LISTESI = "Kayıtlı İzleme Listesi"
EVREN_OZEL_LISTE = "Özel Liste"

TARAMA_EVRENLERI = (
    EVREN_IZLEME_LISTESI,
    "BIST 30",
    "BIST 100",
    "BIST 500",
    "BIST Tüm",
    EVREN_OZEL_LISTE,
)


class MarketScannerError(Exception):
    """BIST toplu tarama işlemi hazırlanamadığında kullanılır."""


@dataclass(frozen=True)
class MarketScanRequest:
    """Güncel BIST taraması için kullanıcı tercihleri."""

    evren: str = EVREN_IZLEME_LISTESI
    profil_adi: str = "dengeli"
    maksimum_aday: int = 15
    ozel_semboller: tuple[str, ...] = ()
    internetten_evren_guncelle: bool = True

    def __post_init__(self) -> None:
        if self.evren not in TARAMA_EVRENLERI:
            raise ValueError(f"Geçersiz tarama evreni: {self.evren}")

        if not 1 <= self.maksimum_aday <= 100:
            raise ValueError(
                "Maksimum aday sayısı 1 ile 100 arasında olmalıdır."
            )

        profil_al(self.profil_adi)


@dataclass(frozen=True)
class MarketScanResult:
    """Kullanıcıya gösterilecek toplu tarama sonucu."""

    evren_adi: str
    evren_kaynagi: str
    evren_tarihi: str
    evren_sembol_sayisi: int
    profil: ScanProfile
    filtrelenmis: FilteredScanResult
    adaylar: tuple[StockAnalysisResult, ...]
    veri_tazeligi: BatchDataFreshnessResult | None = None
    vbts_engellenen_semboller: tuple[str, ...] = ()
    vbts_engelleme_nedenleri: dict[str, tuple[str, ...]] | None = None
    vbts_dogrulama_uyarisi: str | None = None

    @property
    def gosterilen_aday_sayisi(self) -> int:
        return len(self.adaylar)


ProgressCallback = Callable[[int, int, str], None]


class BistMarketScannerService:
    """Evren yükleme, toplu analiz, filtreleme ve aday sıralamasını birleştirir."""

    def __init__(
        self,
        evren_repository: BistUniverseRepository | None = None,
        tarayici: BatchStockScanner | None = None,
        izleme_listesi_yolu: str | Path | None = None,
        vbts_scan_filter: VbtsScanFilter | None = None,
        vbts_control_date: date | None = None,
        vbts_control_time: datetime | None = None,
        vbts_hard_block: bool = True,
        vbts_warning: str | None = None,
    ) -> None:
        backend = Path(__file__).resolve().parents[2]

        self._evren_repository = (
            evren_repository or BistUniverseRepository()
        )
        self._tarayici = tarayici or BatchStockScanner()

        self._izleme_listesi_yolu = (
            Path(izleme_listesi_yolu)
            if izleme_listesi_yolu is not None
            else backend / "watchlists" / "favoriler.txt"
        )

        self._vbts_scan_filter = vbts_scan_filter
        self._vbts_control_date = vbts_control_date
        self._vbts_control_time = vbts_control_time
        self._vbts_hard_block = bool(vbts_hard_block)
        self._vbts_warning = vbts_warning.strip() if vbts_warning else None

    def calistir(
        self,
        istek: MarketScanRequest,
        ilerleme_bildirimi: ProgressCallback | None = None,
    ) -> MarketScanResult:
        vbts_engellenen_semboller: tuple[str, ...] = ()
        vbts_engelleme_nedenleri: dict[str, tuple[str, ...]] = {}
        vbts_dogrulama_uyarisi = self._vbts_warning

        try:
            semboller, evren_kaynagi, evren_tarihi = (
                tarama_evreni_yukle(
                    istek,
                    evren_repository=self._evren_repository,
                    izleme_listesi_yolu=self._izleme_listesi_yolu,
                )
            )

            if self._vbts_scan_filter is not None:
                if self._vbts_control_date is None:
                    raise ValueError(
                        "VBTS kontrol tarihi belirtilmelidir."
                    )

                if self._vbts_control_time is None:
                    raise ValueError(
                        "VBTS kontrol zamanı belirtilmelidir."
                    )

                try:
                    vbts_sonucu = self._vbts_scan_filter.apply(
                        symbols=semboller,
                        control_date=self._vbts_control_date,
                        control_time=self._vbts_control_time,
                    )
                except VbtsDatasetNotUsableError as hata:
                    if self._vbts_hard_block:
                        raise
                    vbts_dogrulama_uyarisi = (
                        f"{hata} Tarama VBTS doğrulaması olmadan devam etti."
                    )
                else:
                    vbts_engellenen_semboller = vbts_sonucu.blocked_symbols
                    vbts_engelleme_nedenleri = dict(vbts_sonucu.block_reasons)
                    if self._vbts_hard_block:
                        semboller = vbts_sonucu.allowed_symbols

            profil = profil_al(istek.profil_adi)

            tarama = self._tarayici.tara(
                semboller=semboller,
                ilerleme_bildirimi=ilerleme_bildirimi,
            )

            filtrelenmis = tarama_sonucunu_filtrele(
                tarama=tarama,
                kriterler=profil.kriterler,
            )

        except Exception as hata:
            if isinstance(hata, (KeyboardInterrupt, SystemExit)):
                raise

            raise MarketScannerError(str(hata)) from hata

        adaylar = tuple(
            filtrelenmis.adaylar[: istek.maksimum_aday]
        )

        tum_sonuclar = tuple(tarama.basarili_sonuclar)

        tazelik_verileri = {
            sonuc.sembol: pd.DataFrame(
                {"Close": [sonuc.kapanis]},
                index=pd.to_datetime([sonuc.analiz_tarihi]),
            )
            for sonuc in tum_sonuclar
        }

        veri_tazeligi = toplu_veri_tazeligini_degerlendir(
            tazelik_verileri
        )

        return MarketScanResult(
            evren_adi=istek.evren,
            evren_kaynagi=evren_kaynagi,
            evren_tarihi=evren_tarihi,
            evren_sembol_sayisi=len(semboller),
            profil=profil,
            filtrelenmis=filtrelenmis,
            adaylar=adaylar,
            veri_tazeligi=veri_tazeligi,
            vbts_engellenen_semboller=vbts_engellenen_semboller,
            vbts_engelleme_nedenleri=vbts_engelleme_nedenleri,
            vbts_dogrulama_uyarisi=vbts_dogrulama_uyarisi,
        )


def tarama_evreni_yukle(
    istek: MarketScanRequest,
    *,
    evren_repository: BistUniverseRepository | None = None,
    izleme_listesi_yolu: str | Path | None = None,
) -> tuple[tuple[str, ...], str, str]:
    """BIST, kayıtlı liste veya özel liste evrenini ortak biçimde çözer."""

    backend = Path(__file__).resolve().parents[2]
    repository = evren_repository or BistUniverseRepository()

    watchlist_path = (
        Path(izleme_listesi_yolu)
        if izleme_listesi_yolu
        else backend / "watchlists" / "favoriler.txt"
    )

    if istek.evren in EVREN_KODLARI:
        evren: BistUniverse = repository.evreni_yukle(
            istek.evren,
            internetten_guncelle=istek.internetten_evren_guncelle,
        )

        return evren.semboller, evren.kaynak, evren.tarih

    if istek.evren == EVREN_IZLEME_LISTESI:
        liste = izleme_listesi_yukle(watchlist_path)

        return (
            sembolleri_normalize_et(liste.semboller),
            liste.kaynak,
            "Kişisel liste",
        )

    semboller = sembolleri_normalize_et(
        istek.ozel_semboller
    )

    if not semboller:
        raise ValueError(
            "Özel liste için en az bir hisse sembolü girilmelidir."
        )

    return semboller, "Kullanıcı girdisi", "Anlık"


def ozel_sembol_metinini_ayristir(
    metin: str,
) -> tuple[str, ...]:
    """Virgül, noktalı virgül, boşluk veya satır sonuyla ayrılmış sembolleri alır."""

    return sembolleri_normalize_et(
        parca
        for parca in re.split(
            r"[\s,;]+",
            metin.strip(),
        )
        if parca
    )


def sembolleri_normalize_et(
    semboller: object,
) -> tuple[str, ...]:
    sonuc: list[str] = []
    gorulenler: set[str] = set()

    for ham in semboller:  # type: ignore[union-attr]
        sembol = (
            str(ham)
            .lstrip("\ufeff")
            .strip()
            .upper()
        )

        if not sembol:
            continue

        if sembol.endswith(".E"):
            sembol = sembol.removesuffix(".E")

        if "." not in sembol:
            sembol = f"{sembol}.IS"

        if sembol in gorulenler:
            continue

        gorulenler.add(sembol)
        sonuc.append(sembol)

    return tuple(sonuc)


def aday_tablosu_kayitlari(
    sonuc: MarketScanResult,
) -> tuple[dict[str, object], ...]:
    """Streamlit/CSV tablolarında kullanılacak sade aday kayıtlarını üretir."""

    kayitlar: list[dict[str, object]] = []

    for sira, aday in enumerate(
        sonuc.adaylar,
        start=1,
    ):
        karar = (
            "Teknik aday"
            if aday.sinyal.karar
            == "Pozitif Teknik Görünüm"
            else "Teyit bekliyor"
        )

        kayit = {
            "Sıra": sira,
            "Hisse": aday.sembol.removesuffix(".IS"),
            "Skor": aday.sinyal.skor,
            "Durum": karar,
            "Teknik görünüm": aday.sinyal.karar,
            "Son kapanış": round(aday.kapanis, 2),
            "Giriş": round(
                aday.risk_plani.giris_fiyati,
                2,
            ),
            "Stop": round(
                aday.risk_plani.stop_loss,
                2,
            ),
            "Hedef": round(
                aday.risk_plani.hedef_fiyat,
                2,
            ),
            "Risk/Getiri": round(
                aday.risk_plani.risk_odul_orani,
                2,
            ),
            "Hacim oranı": round(
                aday.hacim_orani,
                2,
            ),
            "RSI14": round(aday.rsi14, 2),
            "ATR (%)": round(aday.atr_yuzde, 2),
            "Risk notu": aday.risk_plani.risk_notu,
            "Analiz tarihi": aday.analiz_tarihi,
        }

        vbts_nedenleri = sonuc.vbts_engelleme_nedenleri or {}
        aday_vbts_nedenleri = vbts_nedenleri.get(
            aday.sembol,
            vbts_nedenleri.get(aday.sembol.removesuffix(".IS"), ()),
        )
        if aday_vbts_nedenleri:
            kayit["VBTS"] = "⚠ " + " | ".join(aday_vbts_nedenleri)

        kayitlar.append(kayit)

    return tuple(kayitlar)