from __future__ import annotations

from datetime import date, datetime, timezone
from statistics import median
from typing import Mapping

import pandas as pd

from backend.app.analysis.ranking_memory import RankObservationJsonlStore
from backend.app.analysis.weekly_opportunity_memory import (
    OUTCOME_RECORD_TYPE,
    list_weekly_outcome_records,
    list_weekly_snapshot_records,
    load_weekly_snapshot,
    persist_weekly_outcome_record,
    snapshot_digest,
)
from backend.app.data.batch_market_data import BatchMarketDataResult, toplu_fiyat_verisi_getir


def _clean(value: object) -> str:
    return str(value or "").upper().strip().removesuffix(".IS")


def _day(value: object) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _col(frame: pd.DataFrame, name: str):
    for col in frame.columns:
        if str(col).casefold() == name.casefold():
            return col
    return None


def _rows(frame: object) -> dict[date, dict[str, float]]:
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return {}
    cols = {n: _col(frame, n) for n in ("Open", "High", "Low", "Close")}
    if any(v is None for v in cols.values()):
        return {}
    result = {}
    for idx, row in frame.iterrows():
        try:
            d = pd.Timestamp(idx).date()
            values = {k.lower(): float(row[v]) for k, v in cols.items()}
        except (TypeError, ValueError, KeyError):
            continue
        if all(x > 0 for x in values.values()):
            result[d] = values
    return result


def _universe(
    canonical_date: str,
    candidate_symbols: set[str],
    store: RankObservationJsonlStore,
) -> tuple[str, ...]:
    obs = tuple(x for x in store.list() if str(x.as_of)[:10] == canonical_date)
    groups: dict[tuple[str, str, int], list[object]] = {}
    for x in obs:
        key = (str(x.universe_source), str(x.profile_name), int(x.ranked_universe_size))
        groups.setdefault(key, []).append(x)
    valid = []
    for key, items in groups.items():
        expected = key[2]
        ordered = tuple(sorted(items, key=lambda x: (int(x.rank), str(x.symbol))))
        symbols = tuple(_clean(x.symbol) for x in ordered)
        if (
            expected > 0
            and len(ordered) == expected
            and tuple(int(x.rank) for x in ordered) == tuple(range(1, expected + 1))
            and len(set(symbols)) == expected
            and candidate_symbols.issubset(set(symbols))
        ):
            valid.append(symbols)
    if len(valid) != 1:
        raise RuntimeError(f"WEEKLY_CANONICAL_UNIVERSE_AMBIGUOUS_OR_INVALID:{len(valid)}")
    return valid[0]


def _horizon_metrics(
    *,
    symbol: str,
    base_date: date,
    session_dates: tuple[date, ...],
    data: Mapping[str, Mapping[date, Mapping[str, float]]],
    horizon: int,
    benchmark_returns: list[float],
) -> dict[str, object] | None:
    rows = data.get(symbol)
    if not rows or base_date not in rows or len(session_dates) < horizon:
        return None
    target = session_dates[horizon - 1]
    target_row = rows.get(target)
    if target_row is None:
        return None
    base = float(rows[base_date]["close"])
    close = float(target_row["close"])
    window = [rows.get(d) for d in session_dates[:horizon]]
    if any(x is None for x in window):
        return None
    ret = close / base - 1.0
    mfe = max(float(x["high"]) for x in window if x is not None) / base - 1.0
    mae = min(float(x["low"]) for x in window if x is not None) / base - 1.0
    bench = median(benchmark_returns) if benchmark_returns else None
    return {
        "horizon": horizon,
        "target_date": target.isoformat(),
        "return": ret,
        "benchmark_return": bench,
        "relative_return": (ret - bench) if bench is not None else None,
        "mfe": mfe,
        "mae": mae,
        "outperformed": (ret > bench) if bench is not None else None,
    }


def settle_weekly_outcomes(
    *,
    current_date: str,
    market_data_fetcher=toplu_fiyat_verisi_getir,
    store: RankObservationJsonlStore | None = None,
) -> tuple[dict[str, object], ...]:
    memory = store or RankObservationJsonlStore()
    today = _day(current_date)
    if today is None:
        raise ValueError("CURRENT_DATE_INVALID")

    finalized = {
        str(x.get("canonical_date", ""))
        for x in list_weekly_outcome_records(memory)
    }
    results = []

    for raw in list_weekly_snapshot_records(memory):
        canonical_date = str(raw.get("canonical_date", ""))
        if canonical_date in finalized:
            continue
        base = _day(canonical_date)
        if base is None or base >= today:
            continue
        snapshot = load_weekly_snapshot(canonical_date, store=memory)
        if snapshot is None or not snapshot.candidates:
            continue
        candidates = {_clean(x.symbol) for x in snapshot.candidates}
        try:
            universe = _universe(canonical_date, candidates, memory)
            market: BatchMarketDataResult = market_data_fetcher(
                universe, islem_gunu=40, indirme_donemi="3mo", bugun=today
            )
        except Exception as exc:
            results.append({"canonical_date": canonical_date, "status": "DATA_UNAVAILABLE", "detail": str(exc)})
            continue

        data = {_clean(s): _rows(f) for s, f in dict(market.veriler or {}).items()}
        all_dates = sorted(
            {
                d for rows in data.values() for d in rows
                if base < d <= today
            }
        )
        if len(all_dates) < 5:
            results.append({"canonical_date": canonical_date, "status": "WAITING_FOR_T5"})
            continue
        sessions = tuple(all_dates[:5])

        benchmark: dict[int, list[float]] = {1: [], 3: [], 5: []}
        for symbol in universe:
            rows = data.get(_clean(symbol), {})
            if base not in rows:
                continue
            base_close = float(rows[base]["close"])
            for h in (1, 3, 5):
                target = sessions[h - 1]
                if target in rows:
                    benchmark[h].append(float(rows[target]["close"]) / base_close - 1.0)

        candidate_rows = []
        complete = True
        for candidate in snapshot.candidates:
            horizons = []
            for h in (1, 3, 5):
                metric = _horizon_metrics(
                    symbol=_clean(candidate.symbol),
                    base_date=base,
                    session_dates=sessions,
                    data=data,
                    horizon=h,
                    benchmark_returns=benchmark[h],
                )
                if metric is None:
                    complete = False
                    break
                horizons.append(metric)
            if not complete:
                break
            candidate_rows.append({
                "symbol": candidate.symbol,
                "stage": candidate.stage.value,
                "next_day_status": candidate.next_day_status,
                "horizons": horizons,
            })

        if not complete:
            results.append({"canonical_date": canonical_date, "status": "PENDING_DATA"})
            continue

        payload = {
            "record_type": OUTCOME_RECORD_TYPE,
            "as_of": canonical_date,
            "contract_id": "WEEKLY_OPPORTUNITY_OUTCOME_V1",
            "canonical_date": canonical_date,
            "snapshot_digest": snapshot_digest(snapshot),
            "t1_date": sessions[0].isoformat(),
            "t3_date": sessions[2].isoformat(),
            "t5_date": sessions[4].isoformat(),
            "candidates": candidate_rows,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        status = persist_weekly_outcome_record(payload, store=memory)
        results.append({"canonical_date": canonical_date, "status": status})
    return tuple(results)
