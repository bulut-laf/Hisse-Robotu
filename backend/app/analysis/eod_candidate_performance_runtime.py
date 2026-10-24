from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable, Mapping

import pandas as pd

from backend.app.analysis.eod_candidate_output_archive import EodCandidateOutputJsonStore
from backend.app.analysis.eod_candidate_performance import (
    EodCandidatePerformanceJsonStore,
    calculate_eod_candidate_performance,
)
from backend.app.data.batch_market_data import toplu_fiyat_verisi_getir


def _clean_symbol(value: object) -> str:
    return str(value or "").strip().upper().removesuffix(".IS")


def _frame_rows(frame: object) -> dict[date, dict[str, float]]:
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return {}
    normalized = frame.copy()
    if isinstance(normalized.columns, pd.MultiIndex):
        normalized.columns = normalized.columns.get_level_values(0)
    columns = {str(col).casefold(): col for col in normalized.columns}
    if not all(name in columns for name in ("high", "low", "close")):
        return {}
    rows: dict[date, dict[str, float]] = {}
    for index, row in normalized.iterrows():
        try:
            day = pd.Timestamp(index).date()
            values = {
                name: float(row[columns[name]])
                for name in ("high", "low", "close")
            }
        except (TypeError, ValueError, KeyError):
            continue
        if all(value > 0 for value in values.values()):
            rows[day] = values
    return rows


def _source_symbols(source: Mapping[str, Any]) -> tuple[str, ...] | None:
    symbols_raw = source.get("buy_candidate_symbols", [])
    if not isinstance(symbols_raw, list):
        return None
    return tuple(dict.fromkeys(
        _clean_symbol(symbol) for symbol in symbols_raw if _clean_symbol(symbol)
    ))


def _settle_source_record(
    *,
    source: dict[str, Any],
    today: date,
    target_store: EodCandidatePerformanceJsonStore,
    market_data_fetcher: Callable[..., Any],
) -> dict[str, Any]:
    run_date = str(source.get("run_date", ""))[:10]
    try:
        base_date = date.fromisoformat(run_date)
    except ValueError:
        return {"status": "SOURCE_RUN_DATE_INVALID", "run_date": run_date}

    symbols = _source_symbols(source)
    if symbols is None:
        return {"status": "SOURCE_CANDIDATES_INVALID", "run_date": run_date}

    if today <= base_date:
        return {
            "status": "WAITING_FOR_FUTURE_SESSIONS",
            "run_date": run_date,
            "candidate_count": len(symbols),
        }

    if not symbols:
        record = calculate_eod_candidate_performance(
            run_date=run_date,
            candidate_symbols=(),
            reference_prices={},
            price_history={},
        )
        record["source_created_at"] = source.get("created_at")
        record["evaluated_as_of"] = today.isoformat()
        target_store.save_record(record, recorded_at=datetime.now().astimezone())
        return {
            "status": record["status"],
            "run_date": run_date,
            "candidate_count": 0,
            "complete_count": 0,
            "archive_path": str(target_store.path),
        }

    try:
        market = market_data_fetcher(
            symbols,
            islem_gunu=40,
            indirme_donemi="3mo",
            bugun=today,
        )
    except Exception as exc:
        return {
            "status": "DATA_UNAVAILABLE",
            "run_date": run_date,
            "candidate_count": len(symbols),
            "detail": f"{type(exc).__name__}: {exc}",
        }

    raw_frames = dict(getattr(market, "veriler", {}) or {})
    frames = {
        _clean_symbol(symbol): _frame_rows(frame)
        for symbol, frame in raw_frames.items()
    }
    reference_prices: dict[str, float] = {}
    future_history: dict[str, dict[str, dict[str, float]]] = {}

    for symbol in symbols:
        rows = frames.get(symbol, {})
        base_row = rows.get(base_date)
        if base_row is not None:
            reference_prices[symbol] = base_row["close"]
        future_history[symbol] = {
            day.isoformat(): row
            for day, row in rows.items()
            if base_date < day <= today
        }

    record = calculate_eod_candidate_performance(
        run_date=run_date,
        candidate_symbols=symbols,
        reference_prices=reference_prices,
        price_history=future_history,
    )
    record["source_created_at"] = source.get("created_at")
    record["evaluated_as_of"] = today.isoformat()
    target_store.save_record(record, recorded_at=datetime.now().astimezone())
    return {
        "status": record["status"],
        "run_date": run_date,
        "candidate_count": len(symbols),
        "complete_count": sum(
            1 for item in record["candidates"]
            if item.get("status") == "COMPLETE"
        ),
        "archive_path": str(target_store.path),
    }


def settle_latest_eod_candidate_performance(
    *,
    current_date: str,
    eod_store: EodCandidateOutputJsonStore | None = None,
    outcome_store: EodCandidatePerformanceJsonStore | None = None,
    market_data_fetcher: Callable[..., Any] = toplu_fiyat_verisi_getir,
) -> dict[str, Any]:
    """Backward-compatible latest-record measurement helper."""
    today = date.fromisoformat(str(current_date)[:10])
    source_store = eod_store or EodCandidateOutputJsonStore()
    target_store = outcome_store or EodCandidatePerformanceJsonStore()
    source_payload = source_store.load()
    source_records = source_payload.get("records", [])
    source = source_records[-1] if source_records else None
    if not isinstance(source, dict):
        return {"status": "NO_EOD_ARCHIVE"}
    return _settle_source_record(
        source=source,
        today=today,
        target_store=target_store,
        market_data_fetcher=market_data_fetcher,
    )


def settle_eod_candidate_performance_history(
    *,
    current_date: str,
    eod_store: EodCandidateOutputJsonStore | None = None,
    outcome_store: EodCandidatePerformanceJsonStore | None = None,
    market_data_fetcher: Callable[..., Any] = toplu_fiyat_verisi_getir,
) -> dict[str, Any]:
    """Settle historical EOD records independently; measurement-only and best-effort."""
    try:
        today = date.fromisoformat(str(current_date)[:10])
    except (TypeError, ValueError):
        return {"status": "CURRENT_DATE_INVALID", "processed_count": 0}

    source_store = eod_store or EodCandidateOutputJsonStore()
    target_store = outcome_store or EodCandidatePerformanceJsonStore()

    try:
        source_payload = source_store.load()
        source_records = source_payload.get("records", [])
    except Exception as exc:
        return {
            "status": "SOURCE_ARCHIVE_UNAVAILABLE",
            "processed_count": 0,
            "detail": f"{type(exc).__name__}: {exc}",
        }

    if not isinstance(source_records, list) or not source_records:
        return {"status": "NO_EOD_ARCHIVE", "processed_count": 0}

    try:
        existing_records = target_store.load().get("records", [])
    except Exception:
        existing_records = []
    settled_by_date: dict[str, dict[str, Any]] = {}
    if isinstance(existing_records, list):
        for item in existing_records:
            if isinstance(item, dict) and item.get("contract_id") == "EOD_CANDIDATE_PERFORMANCE_V1":
                key = str(item.get("run_date", ""))[:10]
                if key:
                    settled_by_date[key] = item

    outcomes: list[dict[str, Any]] = []
    for source in source_records:
        if not isinstance(source, dict):
            continue
        run_date = str(source.get("run_date", ""))[:10]
        prior = settled_by_date.get(run_date)
        if prior and prior.get("status") == "SUCCESS":
            candidates = prior.get("candidates", [])
            if isinstance(candidates, list) and all(
                isinstance(item, dict) and item.get("status") == "COMPLETE"
                for item in candidates
            ):
                outcomes.append({
                    "status": "ALREADY_COMPLETE",
                    "run_date": run_date,
                    "candidate_count": int(prior.get("candidate_count", len(candidates)) or 0),
                })
                continue

        try:
            result = _settle_source_record(
                source=source,
                today=today,
                target_store=target_store,
                market_data_fetcher=market_data_fetcher,
            )
        except Exception as exc:
            result = {
                "status": "RECORD_FAILED",
                "run_date": run_date,
                "detail": f"{type(exc).__name__}: {exc}",
            }
        outcomes.append(result)

    processed = sum(
        1 for item in outcomes
        if item.get("status") not in {
            "WAITING_FOR_FUTURE_SESSIONS", "ALREADY_COMPLETE",
            "SOURCE_RUN_DATE_INVALID", "SOURCE_CANDIDATES_INVALID",
        }
    )
    failures = sum(
        1 for item in outcomes
        if item.get("status") in {"DATA_UNAVAILABLE", "RECORD_FAILED"}
    )
    waiting = sum(1 for item in outcomes if item.get("status") == "WAITING_FOR_FUTURE_SESSIONS")
    return {
        "status": "PARTIAL_FAILURE" if failures else ("WAITING" if waiting and processed == 0 else "SUCCESS"),
        "processed_count": processed,
        "failure_count": failures,
        "waiting_count": waiting,
        "record_count": len(outcomes),
        "results": outcomes,
        "archive_path": str(target_store.path),
    }
