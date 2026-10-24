from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

from .backtest_history import BacktestHistoryRecord


@dataclass(frozen=True)
class BacktestHistoryFilter:
    """Analiz geçmişi için birlikte uygulanabilen görünüm filtreleri."""

    arama: str = ""
    semboller: tuple[str, ...] = ()
    baslangic_tarihi: date | None = None
    bitis_tarihi: date | None = None
    limit: int | None = None

    def __post_init__(self) -> None:
        if (
            self.baslangic_tarihi is not None
            and self.bitis_tarihi is not None
            and self.baslangic_tarihi > self.bitis_tarihi
        ):
            raise ValueError("Başlangıç tarihi bitiş tarihinden sonra olamaz.")
        if self.limit is not None and self.limit <= 0:
            raise ValueError("Geçmiş filtre limiti pozitif olmalıdır.")


def gecmis_kayitlarini_filtrele(
    kayitlar: Iterable[BacktestHistoryRecord],
    filtre: BacktestHistoryFilter,
) -> tuple[BacktestHistoryRecord, ...]:
    """Kayıt sırasını koruyarak arama, sembol ve tarih filtrelerini uygular."""

    if isinstance(kayitlar, (str, bytes)):
        raise TypeError("Geçmiş kayıtları koleksiyon olmalıdır.")
    if not isinstance(filtre, BacktestHistoryFilter):
        raise TypeError("Geçmiş filtresi BacktestHistoryFilter olmalıdır.")

    arama = filtre.arama.strip().casefold()
    secili_semboller = {
        _sembol_normalize(sembol)
        for sembol in filtre.semboller
        if str(sembol).strip()
    }

    sonuc: list[BacktestHistoryRecord] = []
    for kayit in kayitlar:
        if not isinstance(kayit, BacktestHistoryRecord):
            raise TypeError("Geçmiş kayıtları BacktestHistoryRecord olmalıdır.")
        if arama and arama not in _aranabilir_metin(kayit):
            continue
        if secili_semboller and not (
            secili_semboller
            & {_sembol_normalize(sembol) for sembol in kayit.semboller}
        ):
            continue
        if not _tarih_uygun(kayit, filtre):
            continue

        sonuc.append(kayit)
        if filtre.limit is not None and len(sonuc) >= filtre.limit:
            break

    return tuple(sonuc)


def kayit_tarihi(kayit: BacktestHistoryRecord) -> date | None:
    """Kaydedilme zamanını yerel takvim tarihine dönüştürür."""

    try:
        return datetime.fromisoformat(kayit.kaydedilme_zamani).date()
    except ValueError:
        return None


def kayit_sembolleri(
    kayitlar: Iterable[BacktestHistoryRecord],
) -> tuple[str, ...]:
    """Filtre seçenekleri için benzersiz sembolleri sıralı döndürür."""

    semboller = {
        str(sembol).strip().upper()
        for kayit in kayitlar
        for sembol in kayit.semboller
        if str(sembol).strip()
    }
    return tuple(sorted(semboller))


def kayit_tarih_araligi(
    kayitlar: Iterable[BacktestHistoryRecord],
) -> tuple[date, date] | None:
    """Geçerli kaydedilme tarihlerinin en küçük ve en büyük değerini döndürür."""

    tarihler = tuple(
        tarih
        for kayit in kayitlar
        if (tarih := kayit_tarihi(kayit)) is not None
    )
    if not tarihler:
        return None
    return min(tarihler), max(tarihler)


def _aranabilir_metin(kayit: BacktestHistoryRecord) -> str:
    parcalar = (
        kayit.baslik,
        " ".join(kayit.semboller),
        kayit.donem,
        kayit.kayit_kimligi,
        kayit.analiz_turu,
        kayit.analiz_kimligi or "",
        kayit.veri_kimligi,
        kayit.ayar_kimligi,
    )
    return " ".join(parcalar).casefold()


def _sembol_normalize(sembol: object) -> str:
    deger = str(sembol).strip().upper()
    return deger if deger.endswith(".IS") else f"{deger}.IS"


def _tarih_uygun(
    kayit: BacktestHistoryRecord,
    filtre: BacktestHistoryFilter,
) -> bool:
    if filtre.baslangic_tarihi is None and filtre.bitis_tarihi is None:
        return True

    tarih = kayit_tarihi(kayit)
    if tarih is None:
        return False
    if filtre.baslangic_tarihi is not None and tarih < filtre.baslangic_tarihi:
        return False
    if filtre.bitis_tarihi is not None and tarih > filtre.bitis_tarihi:
        return False
    return True
