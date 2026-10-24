from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from backend.app.data.bist_official_archive import (
    archive_official_daily_snapshot,
    load_canonical_daily_snapshot,
)


DEFAULT_ARCHIVE = Path("data") / "bist_official_daily"
CHECK_SYMBOLS = (
    "THYAO.IS",
    "ASELS.IS",
    "TUPRS.IS",
    "SAHOL.IS",
    "KCHOL.IS",
    "AKBNK.IS",
    "GARAN.IS",
    "BIMAS.IS",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="2026-08-03")
    parser.add_argument("--archive-root", default=str(DEFAULT_ARCHIVE))
    args = parser.parse_args()

    trade_date = date.fromisoformat(args.date)
    archive_root = Path(args.archive_root)

    print("BIST OFFICIAL LIVE ARCHIVE VALIDATION")
    print("=" * 72)
    print("Tarih       :", trade_date.isoformat())
    print("Arşiv kökü :", archive_root)
    print()

    result = archive_official_daily_snapshot(
        trade_date,
        archive_root=archive_root,
        symbols=None,
    )

    data = load_canonical_daily_snapshot(
        trade_date,
        archive_root=archive_root,
    )

    print("Kaynak URL      :", result.kaynak_url)
    print("Arşiv sembol    :", result.sembol_sayisi)
    print("Raw ZIP         :", result.raw_zip)
    print("Canonical CSV   :", result.canonical_csv)
    print("Manifest        :", result.manifest_json)
    print("Canonical SHA256:", result.sha256)
    print()

    print("KONTROL SEMBOLLERI")
    print("-" * 72)
    missing = []

    for symbol in CHECK_SYMBOLS:
        frame = data.get(symbol)
        if frame is None or frame.empty:
            print(f"{symbol:10s} YOK")
            missing.append(symbol)
            continue

        row = frame.iloc[-1]
        print(
            f"{symbol:10s} "
            f"O={row['Open']:>8.2f} "
            f"H={row['High']:>8.2f} "
            f"L={row['Low']:>8.2f} "
            f"C={row['Close']:>8.2f} "
            f"V={row['Volume']:>14.0f}"
        )

    print()
    thyao = data.get("THYAO.IS")
    thyao_ok = False
    if thyao is not None and not thyao.empty:
        row = thyao.iloc[-1]
        thyao_ok = (
            float(row["Open"]) == 320.5
            and float(row["High"]) == 322.25
            and float(row["Low"]) == 316.5
            and float(row["Close"]) == 317.0
            and float(row["Volume"]) == 46594813.0
        )

    if missing:
        print("SONUC: BASARISIZ — kontrol sembollerinde eksik var:", ", ".join(missing))
        return 10

    if trade_date == date(2026, 8, 3) and not thyao_ok:
        print("SONUC: BASARISIZ — THYAO 03.08 referans OHLCV uyuşmuyor.")
        return 11

    print("SONUC: BASARILI — resmî günlük veri canlı alındı, doğrulandı ve yerel arşive yazıldı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
