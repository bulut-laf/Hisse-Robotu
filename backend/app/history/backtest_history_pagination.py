from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import ceil
from typing import Iterable

from .backtest_history import BACKTEST_ANALIZ_TURLERI, BacktestHistoryRecord


SIRALAMA_EN_YENI = "en-yeni"
SIRALAMA_EN_ESKI = "en-eski"
SIRALAMA_GETIRI_AZALAN = "getiri-azalan"
SIRALAMA_DUSUS_ARTAN = "dusus-artan"
SIRALAMA_SEMBOL_ARTAN = "sembol-artan"

DESTEKLENEN_SIRALAMALAR = frozenset(
    {
        SIRALAMA_EN_YENI,
        SIRALAMA_EN_ESKI,
        SIRALAMA_GETIRI_AZALAN,
        SIRALAMA_DUSUS_ARTAN,
        SIRALAMA_SEMBOL_ARTAN,
    }
)


@dataclass(frozen=True)
class BacktestHistoryPage:
    """Filtrelenmiş geçmiş kayıtlarının tek sayfalık görünümü."""

    kayitlar: tuple[BacktestHistoryRecord, ...]
    toplam_kayit: int
    sayfa: int
    sayfa_boyutu: int
    toplam_sayfa: int
    ilk_sira: int
    son_sira: int


def gecmis_kayitlarini_sirala(
    kayitlar: Iterable[BacktestHistoryRecord],
    siralama: str,
) -> tuple[BacktestHistoryRecord, ...]:
    """Geçmiş kayıtlarını seçilen görünüm ölçütüne göre kararlı sıralar."""

    kayit_listesi = _kayitlari_dogrula(kayitlar)
    if siralama not in DESTEKLENEN_SIRALAMALAR:
        raise ValueError("Desteklenmeyen analiz geçmişi sıralaması.")

    if siralama == SIRALAMA_EN_YENI:
        return tuple(
            sorted(
                kayit_listesi,
                key=_en_yeni_anahtari,
            )
        )
    if siralama == SIRALAMA_EN_ESKI:
        return tuple(
            sorted(
                kayit_listesi,
                key=_en_eski_anahtari,
            )
        )
    if siralama == SIRALAMA_GETIRI_AZALAN:
        return tuple(
            sorted(
                kayit_listesi,
                key=lambda kayit: (
                    kayit.analiz_turu not in BACKTEST_ANALIZ_TURLERI,
                    -kayit.toplam_getiri_yuzde,
                    *_en_yeni_anahtari(kayit),
                ),
            )
        )
    if siralama == SIRALAMA_DUSUS_ARTAN:
        return tuple(
            sorted(
                kayit_listesi,
                key=lambda kayit: (
                    kayit.analiz_turu not in BACKTEST_ANALIZ_TURLERI,
                    kayit.maksimum_dusus_yuzde,
                    *_en_yeni_anahtari(kayit),
                ),
            )
        )

    return tuple(
        sorted(
            kayit_listesi,
            key=lambda kayit: (
                tuple(sembol.casefold() for sembol in kayit.semboller),
                *_en_yeni_anahtari(kayit),
            ),
        )
    )


def gecmis_kayitlarini_sayfala(
    kayitlar: Iterable[BacktestHistoryRecord],
    *,
    sayfa: int,
    sayfa_boyutu: int,
) -> BacktestHistoryPage:
    """Kayıtları sayfalara böler; taşan sayfa isteğini son sayfaya çeker."""

    kayit_listesi = _kayitlari_dogrula(kayitlar)
    if not isinstance(sayfa, int) or isinstance(sayfa, bool) or sayfa <= 0:
        raise ValueError("Geçmiş sayfa numarası pozitif tam sayı olmalıdır.")
    if (
        not isinstance(sayfa_boyutu, int)
        or isinstance(sayfa_boyutu, bool)
        or sayfa_boyutu <= 0
    ):
        raise ValueError("Geçmiş sayfa boyutu pozitif tam sayı olmalıdır.")

    toplam_kayit = len(kayit_listesi)
    toplam_sayfa = max(1, ceil(toplam_kayit / sayfa_boyutu))
    gercek_sayfa = min(sayfa, toplam_sayfa)
    baslangic = (gercek_sayfa - 1) * sayfa_boyutu
    bitis = min(baslangic + sayfa_boyutu, toplam_kayit)
    sayfa_kayitlari = kayit_listesi[baslangic:bitis]

    return BacktestHistoryPage(
        kayitlar=sayfa_kayitlari,
        toplam_kayit=toplam_kayit,
        sayfa=gercek_sayfa,
        sayfa_boyutu=sayfa_boyutu,
        toplam_sayfa=toplam_sayfa,
        ilk_sira=baslangic + 1 if sayfa_kayitlari else 0,
        son_sira=bitis if sayfa_kayitlari else 0,
    )


def _kayitlari_dogrula(
    kayitlar: Iterable[BacktestHistoryRecord],
) -> tuple[BacktestHistoryRecord, ...]:
    if isinstance(kayitlar, (str, bytes)):
        raise TypeError("Geçmiş kayıtları koleksiyon olmalıdır.")

    sonuc = tuple(kayitlar)
    if any(not isinstance(kayit, BacktestHistoryRecord) for kayit in sonuc):
        raise TypeError("Geçmiş kayıtları BacktestHistoryRecord olmalıdır.")
    return sonuc


def _zaman_damgasi(kayit: BacktestHistoryRecord) -> float | None:
    try:
        return datetime.fromisoformat(kayit.kaydedilme_zamani).timestamp()
    except (ValueError, OverflowError, OSError):
        return None


def _en_yeni_anahtari(kayit: BacktestHistoryRecord) -> tuple[object, ...]:
    zaman = _zaman_damgasi(kayit)
    return (
        zaman is None,
        -(zaman or 0.0),
        kayit.kayit_kimligi,
    )


def _en_eski_anahtari(kayit: BacktestHistoryRecord) -> tuple[object, ...]:
    zaman = _zaman_damgasi(kayit)
    return (
        zaman is None,
        zaman or 0.0,
        kayit.kayit_kimligi,
    )
