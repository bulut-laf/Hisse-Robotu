
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.analysis.momentum_discovery import MomentumDiscoveryEngine
from backend.app.data.market_data import guvenli_fiyat_verisi_getir


SCHEMA_VERSION = "fin-prod-v5-exact-momentum-producer-v1"
MODE = "EXACT_EXISTING_MOMENTUM_PRODUCER_POINT_IN_TIME"


def _market_symbol(symbol: str) -> str:
    clean = symbol.strip().upper()
    return clean if "." in clean else f"{clean}.IS"


def _idx_date(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return pd.Timestamp(value).date()
    except Exception:
        return None


def _jsonable(value):
    if is_dataclass(value):
        return {k: _jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (date, datetime, pd.Timestamp)):
        return value.isoformat()
    return value


def _historical_frame(symbol: str, as_of_date: date) -> tuple[pd.DataFrame, dict]:
    market_symbol = _market_symbol(symbol)
    recovered = guvenli_fiyat_verisi_getir(
        market_symbol,
        islem_gunu=320,
        indirme_donemi="2y",
    )
    frame = getattr(recovered, "veri", recovered)

    if frame is None or frame.empty:
        raise RuntimeError("REV6_MARKET_DATA_EMPTY")

    keep = []
    future_rows = 0
    for i, idx in enumerate(frame.index):
        d = _idx_date(idx)
        if d is None:
            continue
        if d <= as_of_date:
            keep.append(i)
        else:
            future_rows += 1

    if not keep:
        raise RuntimeError("REV6_POINT_IN_TIME_NO_ELIGIBLE_ROWS")

    sliced = frame.iloc[keep].copy()

    last_date = _idx_date(sliced.index[-1])
    if last_date is None or last_date > as_of_date:
        raise RuntimeError("REV6_POINT_IN_TIME_VIOLATION")

    return sliced, {
        "market_symbol": market_symbol,
        "rows": int(len(sliced)),
        "last_date": last_date.isoformat(),
        "future_rows_excluded": int(future_rows),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="TUPRS")
    p.add_argument("--as-of-date", required=True)
    p.add_argument("--output")
    args = p.parse_args()

    symbol = args.symbol.strip().upper().replace(".IS", "")
    as_of = date.fromisoformat(args.as_of_date)

    frame, pit = _historical_frame(symbol, as_of)

    engine = MomentumDiscoveryEngine()

    candidates, failures = engine.analiz_et(
        {symbol: frame},
    )

    matching = [c for c in candidates if str(c.sembol).upper().replace(".IS", "") == symbol]

    payload = {
        "status": "PASS" if matching else "BLOCKED",
        "mode": MODE,
        "symbol": symbol,
        "as_of_date": as_of.isoformat(),
        "point_in_time": pit,
        "candidate": _jsonable(matching[0]) if matching else None,
        "failures": _jsonable(failures),
        "blockers": [] if matching else ["MOMENTUM_CANDIDATE_NOT_PRODUCED"],
        "schema_version": SCHEMA_VERSION,
    }

    output = Path(args.output) if args.output else (
        PROJECT_ROOT
        / "backend"
        / "data"
        / "financial_intelligence"
        / f"{symbol}_momentum_candidate_{as_of.isoformat()}.json"
    )
    if not output.is_absolute():
        output = PROJECT_ROOT / output

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = {
        "status": payload["status"],
        "symbol": symbol,
        "as_of_date": as_of.isoformat(),
        "candidate_found": bool(matching),
        "failure_count": len(failures),
        "last_market_date": pit["last_date"],
        "future_rows_excluded": pit["future_rows_excluded"],
        "result": str(output),
        "schema_version": SCHEMA_VERSION,
    }
    print(json.dumps(summary, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
