from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd

from backend.app.data.bist_official_daily import (
    DEFAULT_SUFFIX_CANDIDATES,
    OfficialDailyBatchResult,
    official_daily_data_get,
)


@dataclass(frozen=True)
class OfficialArchiveSnapshot:
    islem_tarihi: date
    sembol_sayisi: int
    kaynak_url: str
    raw_zip: Path
    canonical_csv: Path
    manifest_json: Path
    sha256: str


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        os.replace(temp_name, path)
    finally:
        try:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        except OSError:
            pass


def _canonical_rows(
    data: dict[str, pd.DataFrame],
    islem_tarihi: date,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for symbol in sorted(data):
        df = data[symbol]
        if df is None or df.empty:
            continue

        row = df.iloc[-1]
        rows.append(
            {
                "Date": islem_tarihi.isoformat(),
                "Symbol": symbol,
                "Open": format(float(row["Open"]), ".10g"),
                "High": format(float(row["High"]), ".10g"),
                "Low": format(float(row["Low"]), ".10g"),
                "Close": format(float(row["Close"]), ".10g"),
                "Volume": format(float(row["Volume"]), ".15g"),
            }
        )
    return rows


def _canonical_csv_text(rows: list[dict[str, str]]) -> str:
    from io import StringIO

    buffer = StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "Date",
            "Symbol",
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
        ],
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def archive_official_daily_snapshot(
    islem_tarihi: date,
    *,
    archive_root: Path | str,
    symbols: Iterable[str] | None = None,
    fetcher: Callable[[str], bytes] | None = None,
    suffix_candidates: Iterable[str] = DEFAULT_SUFFIX_CANDIDATES,
) -> OfficialArchiveSnapshot:
    root = Path(archive_root)

    raw_root = root / "raw"
    result: OfficialDailyBatchResult = official_daily_data_get(
        symbols,
        islem_tarihi,
        archive_root=raw_root,
        fetcher=fetcher,
        suffix_candidates=suffix_candidates,
    )

    if result.arsiv_dosyasi is None:
        raise RuntimeError("Ham resmî ZIP arşivlenemedi.")

    rows = _canonical_rows(result.veriler, islem_tarihi)
    if not rows:
        raise RuntimeError(
            f"{islem_tarihi.isoformat()} için canonical OHLCV kaydı oluşmadı."
        )

    canonical_text = _canonical_csv_text(rows)
    canonical_bytes = canonical_text.encode("utf-8")
    sha256 = hashlib.sha256(canonical_bytes).hexdigest()

    canonical_path = (
        root
        / "canonical"
        / f"{islem_tarihi:%Y}"
        / f"{islem_tarihi:%m}"
        / f"{islem_tarihi.isoformat()}.csv"
    )
    manifest_path = (
        root
        / "manifest"
        / f"{islem_tarihi:%Y}"
        / f"{islem_tarihi:%m}"
        / f"{islem_tarihi.isoformat()}.json"
    )

    if canonical_path.exists():
        existing = canonical_path.read_bytes()
        existing_hash = hashlib.sha256(existing).hexdigest()
        if existing_hash != sha256:
            raise RuntimeError(
                "Daha önce doğrulanmış canonical günlük veri ile "
                "yeni resmî veri farklı. Otomatik üzerine yazma engellendi."
            )
    else:
        _atomic_write_text(canonical_path, canonical_text)

    manifest = {
        "schema_version": 1,
        "source": "Borsa Istanbul Official Daily Bulletin",
        "trade_date": islem_tarihi.isoformat(),
        "source_url": result.kaynak_url,
        "symbol_count": len(rows),
        "missing_requested_symbols": list(result.bulunamayan_semboller),
        "canonical_sha256": sha256,
        "raw_zip": str(result.arsiv_dosyasi),
        "canonical_csv": str(canonical_path),
        "archived_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    # Manifest zaman alanı nedeniyle her çalışmada değişebilir; canonical veri
    # değişmedikçe güvenlidir. Manifest atomik olarak yenilenebilir.
    _atomic_write_text(
        manifest_path,
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    )

    return OfficialArchiveSnapshot(
        islem_tarihi=islem_tarihi,
        sembol_sayisi=len(rows),
        kaynak_url=result.kaynak_url,
        raw_zip=result.arsiv_dosyasi,
        canonical_csv=canonical_path,
        manifest_json=manifest_path,
        sha256=sha256,
    )


def load_canonical_daily_snapshot(
    islem_tarihi: date,
    *,
    archive_root: Path | str,
) -> dict[str, pd.DataFrame]:
    path = (
        Path(archive_root)
        / "canonical"
        / f"{islem_tarihi:%Y}"
        / f"{islem_tarihi:%m}"
        / f"{islem_tarihi.isoformat()}.csv"
    )

    if not path.exists():
        raise FileNotFoundError(path)

    frame = pd.read_csv(path)
    required = {"Date", "Symbol", "Open", "High", "Low", "Close", "Volume"}
    missing = required - set(frame.columns)
    if missing:
        raise RuntimeError(
            "Canonical günlük veri zorunlu kolonları eksik: "
            + ", ".join(sorted(missing))
        )

    result: dict[str, pd.DataFrame] = {}
    for row in frame.to_dict(orient="records"):
        symbol = str(row["Symbol"])
        timestamp = pd.Timestamp(str(row["Date"]))
        result[symbol] = pd.DataFrame(
            [[
                float(row["Open"]),
                float(row["High"]),
                float(row["Low"]),
                float(row["Close"]),
                float(row["Volume"]),
            ]],
            columns=["Open", "High", "Low", "Close", "Volume"],
            index=pd.DatetimeIndex([timestamp], name="Date"),
        )

    return result


__all__ = [
    "OfficialArchiveSnapshot",
    "archive_official_daily_snapshot",
    "load_canonical_daily_snapshot",
]
