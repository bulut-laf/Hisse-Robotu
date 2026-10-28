"""Strict CSV reader for fund holdings; source evidence is retained per row."""
from __future__ import annotations
import csv
from pathlib import Path
from .overlap import Holding


REQUIRED_COLUMNS = {"fund_isin", "asset_id", "weight_pct"}


def load_holdings_csv(path: str | Path) -> list[Holding]:
    with open(path, "r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise ValueError(f"Missing required holdings columns: {', '.join(sorted(missing))}")
        result = []
        for line_number, row in enumerate(reader, start=2):
            try:
                result.append(Holding(
                    fund_isin=(row.get("fund_isin") or "").strip().upper(),
                    asset_id=(row.get("asset_id") or "").strip(),
                    weight_pct=float(row["weight_pct"]),
                    asset_type=(row.get("asset_type") or "equity").strip() or "equity",
                    sector=(row.get("sector") or "").strip() or None,
                    country=(row.get("country") or "").strip() or None,
                    currency=(row.get("currency") or "").strip() or None,
                    source_url=(row.get("source_url") or "").strip() or None,
                ))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid holdings row at line {line_number}: {exc}") from exc
        return result
