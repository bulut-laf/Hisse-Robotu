from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean, median
from typing import Iterable

from .backtest_history import (
    PORTFOY_ANALIZI,
    TEK_HISSE_ANALIZI,
    BacktestHistoryRecord,
)


@dataclass(frozen=True)
class BacktestHistorySummary:
    """Filtrelenmiş analiz geçmişinin betimleyici performans özeti."""

    toplam_kayit: int
    tek_hisse_kaydi: int
    portfoy_kaydi: int
    benzersiz_sembol_sayisi: int
    toplam_tamamlanan_islem: int
    ortalama_getiri_yuzde: float | None
    medyan_getiri_yuzde: float | None
    ortalama_maksimum_dusus_yuzde: float | None
    medyan_maksimum_dusus_yuzde: float | None
    ortalama_kar_faktoru: float | None
    ortalama_kazanma_yuzde: float | None
    en_yuksek_getiri_kaydi: BacktestHistoryRecord | None
    en_dusuk_dusus_kaydi: BacktestHistoryRecord | None


@dataclass(frozen=True)
class BacktestHistoryPerformancePoint:
    """Risk-getiri görünümünde kullanılan tek analiz noktası."""

    kayit_kimligi: str
    etiket: str
    analiz_turu: str
    toplam_getiri_yuzde: float
    maksimum_dusus_yuzde: float
    tamamlanan_islem_sayisi: int


def gecmis_ozeti_hesapla(
    kayitlar: Iterable[BacktestHistoryRecord],
) -> BacktestHistorySummary:
    """Geçmiş kayıtlarını birleştirmeden betimleyici özet üretir."""

    kayit_listesi = _kayitlari_dogrula(kayitlar)
    if not kayit_listesi:
        return BacktestHistorySummary(
            toplam_kayit=0,
            tek_hisse_kaydi=0,
            portfoy_kaydi=0,
            benzersiz_sembol_sayisi=0,
            toplam_tamamlanan_islem=0,
            ortalama_getiri_yuzde=None,
            medyan_getiri_yuzde=None,
            ortalama_maksimum_dusus_yuzde=None,
            medyan_maksimum_dusus_yuzde=None,
            ortalama_kar_faktoru=None,
            ortalama_kazanma_yuzde=None,
            en_yuksek_getiri_kaydi=None,
            en_dusuk_dusus_kaydi=None,
        )

    getiriler = tuple(kayit.toplam_getiri_yuzde for kayit in kayit_listesi)
    dususler = tuple(kayit.maksimum_dusus_yuzde for kayit in kayit_listesi)
    kar_faktorleri = tuple(
        kayit.kar_faktoru
        for kayit in kayit_listesi
        if kayit.kar_faktoru is not None
    )
    kazanma_oranlari = tuple(
        kayit.kazanma_yuzde
        for kayit in kayit_listesi
        if kayit.kazanma_yuzde is not None
    )

    return BacktestHistorySummary(
        toplam_kayit=len(kayit_listesi),
        tek_hisse_kaydi=sum(
            kayit.analiz_turu == TEK_HISSE_ANALIZI
            for kayit in kayit_listesi
        ),
        portfoy_kaydi=sum(
            kayit.analiz_turu == PORTFOY_ANALIZI
            for kayit in kayit_listesi
        ),
        benzersiz_sembol_sayisi=len(
            {
                sembol.casefold()
                for kayit in kayit_listesi
                for sembol in kayit.semboller
            }
        ),
        toplam_tamamlanan_islem=sum(
            kayit.tamamlanan_islem_sayisi for kayit in kayit_listesi
        ),
        ortalama_getiri_yuzde=fmean(getiriler),
        medyan_getiri_yuzde=float(median(getiriler)),
        ortalama_maksimum_dusus_yuzde=fmean(dususler),
        medyan_maksimum_dusus_yuzde=float(median(dususler)),
        ortalama_kar_faktoru=(
            fmean(kar_faktorleri) if kar_faktorleri else None
        ),
        ortalama_kazanma_yuzde=(
            fmean(kazanma_oranlari) if kazanma_oranlari else None
        ),
        en_yuksek_getiri_kaydi=max(
            kayit_listesi,
            key=lambda kayit: (
                kayit.toplam_getiri_yuzde,
                -kayit.maksimum_dusus_yuzde,
                kayit.kayit_kimligi,
            ),
        ),
        en_dusuk_dusus_kaydi=min(
            kayit_listesi,
            key=lambda kayit: (
                kayit.maksimum_dusus_yuzde,
                -kayit.toplam_getiri_yuzde,
                kayit.kayit_kimligi,
            ),
        ),
    )


def gecmis_performans_noktalari(
    kayitlar: Iterable[BacktestHistoryRecord],
) -> tuple[BacktestHistoryPerformancePoint, ...]:
    """Her geçmiş kaydını risk-getiri grafiği için tek noktaya dönüştürür."""

    kayit_listesi = _kayitlari_dogrula(kayitlar)
    return tuple(
        BacktestHistoryPerformancePoint(
            kayit_kimligi=kayit.kayit_kimligi,
            etiket=_kayit_etiketi(kayit),
            analiz_turu=(
                "Tek Hisse"
                if kayit.analiz_turu == TEK_HISSE_ANALIZI
                else "Portföy"
            ),
            toplam_getiri_yuzde=kayit.toplam_getiri_yuzde,
            maksimum_dusus_yuzde=kayit.maksimum_dusus_yuzde,
            tamamlanan_islem_sayisi=kayit.tamamlanan_islem_sayisi,
        )
        for kayit in kayit_listesi
    )


def _kayit_etiketi(kayit: BacktestHistoryRecord) -> str:
    semboller = ", ".join(kayit.semboller)
    return f"{semboller} · {kayit.kayit_kimligi[:8]}"


def _kayitlari_dogrula(
    kayitlar: Iterable[BacktestHistoryRecord],
) -> tuple[BacktestHistoryRecord, ...]:
    if isinstance(kayitlar, (str, bytes)):
        raise TypeError("Geçmiş kayıtları koleksiyon olmalıdır.")

    sonuc = tuple(kayitlar)
    if any(not isinstance(kayit, BacktestHistoryRecord) for kayit in sonuc):
        raise TypeError("Geçmiş kayıtları BacktestHistoryRecord olmalıdır.")
    return sonuc
