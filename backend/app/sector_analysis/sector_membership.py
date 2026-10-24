from __future__ import annotations

from typing import Any


def map_sector_members(
    sector: dict[str, Any],
    symbols: list[str],
) -> dict[str, Any]:
    """Sektör ile hisse üyelerini ilişkilendirir.

    Sadece bağlam ilişkisi oluşturur.
    İşlem sinyali üretmez.
    """

    return {
        "sector": sector.get("name"),
        "status": sector.get("status"),
        "symbols": list(symbols),
        "symbol_count": len(symbols),
    }
