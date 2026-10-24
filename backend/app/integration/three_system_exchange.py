from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

DEFAULT_EXCHANGE_DIR = Path(r"D:\Projects\3-Sistem-Ortak-Degerlendirme\data")


def write_scan_row_opinion(
    row: Mapping[str, Any],
    *,
    as_of: str,
    exchange_dir: Path = DEFAULT_EXCHANGE_DIR,
) -> Path:
    symbol = str(row.get("Hisse", "")).strip().upper()
    if symbol.endswith(".IS"):
        symbol = symbol[:-3]
    if not symbol:
        raise ValueError("Hisse is required")
    if not str(row.get("Durum", "")).strip():
        raise ValueError("Durum is required")

    payload = {
        "symbol": symbol,
        "as_of": str(as_of),
        "status": str(row["Durum"]),
        "score": None if row.get("Skor") is None else float(row["Skor"]),
        "rank": None if row.get("Sıra") is None else int(row["Sıra"]),
    }

    exchange_dir.mkdir(parents=True, exist_ok=True)
    path = exchange_dir / f"{symbol}__HISSE_ROBOTU.json"
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path
