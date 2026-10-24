from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any


ReplayRunner = Callable[..., Any]
RowsExtractor = Callable[[Any], Sequence[Mapping[str, object]]]


@dataclass(frozen=True)
class ReplayBatchAdapter:
    """
    Mevcut tek-gün tarihsel replay fonksiyonunu Sprint-133'ün scan_day
    sözleşmesine dönüştürür.

    runner: mevcut tarihsel yeniden oynatma servisi/fonksiyonu
    rows_extractor: runner sonucundan export satırlarını çıkaran fonksiyon
    """

    runner: ReplayRunner
    rows_extractor: RowsExtractor
    universe_mapper: Callable[[str], str] | None = None

    def __post_init__(self) -> None:
        if not callable(self.runner):
            raise TypeError("runner çağrılabilir olmalıdır.")
        if not callable(self.rows_extractor):
            raise TypeError("rows_extractor çağrılabilir olmalıdır.")
        if self.universe_mapper is not None and not callable(self.universe_mapper):
            raise TypeError("universe_mapper çağrılabilir olmalıdır.")

    def scan_day(self, cut_date: date, universe: str) -> Sequence[Mapping[str, object]]:
        mapped_universe = (
            self.universe_mapper(universe)
            if self.universe_mapper is not None
            else universe
        )
        result = self.runner(
            cut_date=cut_date,
            universe=mapped_universe,
        )
        rows = self.rows_extractor(result)
        return tuple(dict(row) for row in rows)


def common_universe_mapper(universe: str) -> str:
    """
    UI etiketlerini projedeki yaygın Türkçe evren adlarına eşler.
    """
    normalized = universe.strip().casefold().replace(" ", "")
    mapping = {
        "bist100": "BIST 100",
        "bisttüm": "BIST Tüm",
        "bisttum": "BIST Tüm",
        "bist30": "BIST 30",
        "bist500": "BIST 500",
    }
    return mapping.get(normalized, universe.strip())


def rows_from_mapping_result(result: Any) -> Sequence[Mapping[str, object]]:
    """
    Replay sonucu zaten satır listesi/tuple ise doğrudan kullanır.
    """
    if isinstance(result, (list, tuple)):
        if all(isinstance(row, Mapping) for row in result):
            return result
    raise TypeError("Replay sonucu export satır listesi değil.")


def rows_from_attribute(
    attribute_name: str,
) -> RowsExtractor:
    if not attribute_name.strip():
        raise ValueError("attribute_name boş olamaz.")

    def extract(result: Any) -> Sequence[Mapping[str, object]]:
        rows = getattr(result, attribute_name, None)
        if not isinstance(rows, (list, tuple)):
            raise TypeError(
                f"Replay sonucunda {attribute_name!r} satır koleksiyonu bulunamadı."
            )
        if not all(isinstance(row, Mapping) for row in rows):
            raise TypeError("Replay export satırları mapping olmalıdır.")
        return rows

    return extract
