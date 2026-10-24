from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from backend.app.analysis.bist_universe import BistUniverseRepository


OZEL_LISTE = "Özel Liste"
ON_YUKSELIS_EVRENLERI = (
    "BIST 30",
    "BIST 50",
    "BIST 100",
    "BIST Tüm",
    OZEL_LISTE,
)
SONUC_LIMITLERI = ("İlk 10", "İlk 25", "İlk 50", "Tümü")
SONUC_LIMIT_DEGERLERI = {
    "İlk 10": 10,
    "İlk 25": 25,
    "İlk 50": 50,
    "Tümü": None,
}


@dataclass(frozen=True)
class PreBreakoutUniverseSelection:
    ad: str
    semboller: tuple[str, ...]
    kaynak: str
    tarih: str


def sembolleri_hazirla(raw: str | Iterable[str]) -> tuple[str, ...]:
    if isinstance(raw, str):
        items = raw.replace("\n", ",").split(",")
    else:
        items = raw

    symbols: list[str] = []
    seen: set[str] = set()
    for item in items:
        symbol = str(item).strip().upper()
        if not symbol:
            continue
        if not symbol.endswith(".IS"):
            symbol = f"{symbol}.IS"
        if symbol not in seen:
            symbols.append(symbol)
            seen.add(symbol)
    return tuple(symbols)


def on_yukselis_evrenini_yukle(
    evren_adi: str,
    ozel_liste: str = "",
    *,
    repository: BistUniverseRepository | None = None,
    internetten_guncelle: bool = True,
) -> PreBreakoutUniverseSelection:
    if evren_adi == OZEL_LISTE:
        semboller = sembolleri_hazirla(ozel_liste)
        if not semboller:
            raise ValueError("Özel liste için en az bir hisse sembolü girilmelidir.")
        return PreBreakoutUniverseSelection(
            ad=OZEL_LISTE,
            semboller=semboller,
            kaynak="Kullanıcı girdisi",
            tarih="Anlık",
        )

    if evren_adi not in ON_YUKSELIS_EVRENLERI:
        raise ValueError(f"Bilinmeyen ön yükseliş evreni: {evren_adi}")

    universe = (repository or BistUniverseRepository()).evreni_yukle(
        evren_adi,
        internetten_guncelle=internetten_guncelle,
    )
    return PreBreakoutUniverseSelection(
        ad=universe.ad,
        semboller=universe.semboller,
        kaynak=universe.kaynak,
        tarih=universe.tarih,
    )


def sonuc_limitini_uygula(
    table: pd.DataFrame,
    limit_adi: str,
) -> pd.DataFrame:
    if limit_adi not in SONUC_LIMIT_DEGERLERI:
        raise ValueError(f"Bilinmeyen sonuç limiti: {limit_adi}")
    limit = SONUC_LIMIT_DEGERLERI[limit_adi]
    return table.copy() if limit is None else table.head(limit).copy()


def sonuc_limitini_kesim_bazinda_uygula(
    table: pd.DataFrame,
    limit_adi: str,
    *,
    kesim_sutunu: str = "cutoff_date",
) -> pd.DataFrame:
    if limit_adi not in SONUC_LIMIT_DEGERLERI:
        raise ValueError(f"Bilinmeyen sonuç limiti: {limit_adi}")
    limit = SONUC_LIMIT_DEGERLERI[limit_adi]
    if limit is None or table.empty:
        return table.copy()
    return table.groupby(kesim_sutunu, sort=False, group_keys=False).head(limit).copy()
