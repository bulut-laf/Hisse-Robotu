from __future__ import annotations

from datetime import date, datetime
import json
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from backend.app.analysis.eod_candidate_output_archive import EodCandidateOutputJsonStore
from backend.app.data.batch_market_data import toplu_fiyat_verisi_getir

CONTRACT_ID = "SCAN_TOP10_NEXT_SESSION_V1"
DEFAULT_ARCHIVE_PATH = Path("backend/data/scan_top10_next_session_performance.json")


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
    result: dict[date, dict[str, float]] = {}
    for index, row in normalized.iterrows():
        try:
            day = pd.Timestamp(index).date()
            high, low, close = (float(row[columns[name]]) for name in ("high", "low", "close"))
        except (TypeError, ValueError, KeyError):
            continue
        if high > 0 and low > 0 and close > 0 and high >= low and low <= close <= high:
            result[day] = {"high": high, "low": low, "close": close}
    return result


class ScanTop10NextSessionJsonStore:
    def __init__(self, path: Path | str = DEFAULT_ARCHIVE_PATH) -> None:
        self.path = Path(path)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"records": []}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return {"records": []}
        if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
            return {"records": []}
        return payload

    def save_record(self, record: dict[str, Any]) -> dict[str, Any]:
        if record.get("contract_id") != CONTRACT_ID:
            raise ValueError("CONTRACT_ID_INVALID")
        run_date = str(record.get("run_date", ""))[:10]
        date.fromisoformat(run_date)
        payload = self.load()
        records = [
            item for item in payload["records"]
            if not (isinstance(item, dict) and item.get("contract_id") == CONTRACT_ID
                    and str(item.get("run_date", ""))[:10] == run_date)
        ]
        saved = dict(record)
        saved["recorded_at"] = datetime.now().astimezone().isoformat()
        records.append(saved)
        payload["records"] = records
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)
        return saved



def record_scan_top10_snapshot(
    *, run_date: str, candidates: Any, outcome_store: ScanTop10NextSessionJsonStore | None = None,
) -> dict[str, Any]:
    """Freeze the first ten real MomentumDiscovery candidates at scan time."""
    try:
        day = date.fromisoformat(str(run_date)[:10])
    except (TypeError, ValueError):
        return {"status": "RUN_DATE_INVALID", "candidate_count": 0}
    store = outcome_store or ScanTop10NextSessionJsonStore()
    frozen: list[dict[str, Any]] = []
    for candidate in (candidates or ()):
        symbol = _clean_symbol(getattr(candidate, "sembol", None) or (candidate.get("sembol") if isinstance(candidate, dict) else None) or (candidate.get("symbol") if isinstance(candidate, dict) else None))
        if not symbol or any(item["symbol"] == symbol for item in frozen):
            continue
        raw_price = getattr(candidate, "kapanis", None)
        if raw_price is None and isinstance(candidate, dict):
            raw_price = candidate.get("kapanis", candidate.get("close"))
        raw_date = getattr(candidate, "analiz_tarihi", None)
        if raw_date is None and isinstance(candidate, dict):
            raw_date = candidate.get("analiz_tarihi", candidate.get("analysis_date"))
        try:
            price = float(raw_price) if raw_price is not None else None
            price_date = str(raw_date)[:10] if raw_date is not None else day.isoformat()
            date.fromisoformat(price_date)
            if price is not None and price <= 0:
                price = None
        except (TypeError, ValueError):
            price, price_date = None, day.isoformat()
        frozen.append({"symbol": symbol, "reference_price": price, "reference_date": price_date,
                       "status": "PENDING_DATA", "reason": "AWAITING_NEXT_SESSION_CLOSE",
                       "next_session_date": None, "next_session_close": None, "return_pct": None})
        if len(frozen) == 10:
            break
    record = {"contract_id": CONTRACT_ID, "run_date": day.isoformat(), "phase": "CANONICAL_CLOSE",
              "status": "SNAPSHOT_FROZEN" if frozen else "NO_CANDIDATES",
              "candidate_symbols": [item["symbol"] for item in frozen], "candidate_count": len(frozen),
              "candidates": frozen, "evaluated_as_of": day.isoformat(),
              "summary": {"evaluated_count": 0, "pending_count": len(frozen),
                          "rising_count": 0, "falling_count": 0, "unchanged_count": 0,
                          "hit_rate_pct": None, "average_return_pct": None}}
    store.save_record(record)
    return {"status": record["status"], "candidate_count": len(frozen), "run_date": day.isoformat()}

def settle_scan_top10_next_session(
    *,
    current_date: str,
    source_store: EodCandidateOutputJsonStore | None = None,
    outcome_store: ScanTop10NextSessionJsonStore | None = None,
    market_data_fetcher: Callable[..., Any] = toplu_fiyat_verisi_getir,
) -> dict[str, Any]:
    """Freeze up to ten scan candidates and settle their next available market-session close."""
    try:
        today = date.fromisoformat(str(current_date)[:10])
    except (TypeError, ValueError):
        return {"status": "CURRENT_DATE_INVALID", "processed_count": 0}

    source_store = source_store or EodCandidateOutputJsonStore()
    outcome_store = outcome_store or ScanTop10NextSessionJsonStore()
    try:
        source_records = source_store.load().get("records", [])
        saved_records = outcome_store.load().get("records", [])
    except Exception as exc:
        return {"status": "ARCHIVE_UNAVAILABLE", "processed_count": 0,
                "detail": f"{type(exc).__name__}: {exc}"}
    if not isinstance(source_records, list) or not source_records:
        return {"status": "NO_EOD_ARCHIVE", "processed_count": 0}

    prior_by_date = {
        str(item.get("run_date", ""))[:10]: item
        for item in saved_records
        if isinstance(item, dict) and item.get("contract_id") == CONTRACT_ID
    } if isinstance(saved_records, list) else {}
    # Frozen scan-time snapshots take precedence over the legacy EOD candidate archive.
    merged_by_date = {str(item.get("run_date", ""))[:10]: item for item in source_records if isinstance(item, dict)}
    for saved_date, saved in prior_by_date.items():
        if saved.get("status") in {"SNAPSHOT_FROZEN", "PENDING_DATA"} and saved.get("candidate_symbols"):
            merged_by_date[saved_date] = {**merged_by_date.get(saved_date, {}), **saved}
    source_records = list(merged_by_date.values())

    outcomes: list[dict[str, Any]] = []
    for source in source_records:
        if not isinstance(source, dict):
            continue
        run_date = str(source.get("run_date", ""))[:10]
        try:
            base_date = date.fromisoformat(run_date)
        except ValueError:
            continue
        raw_symbols = source.get("candidate_symbols", [])
        if not isinstance(raw_symbols, list):
            continue
        symbols = tuple(dict.fromkeys(_clean_symbol(s) for s in raw_symbols if _clean_symbol(s)))[:10]
        prior = prior_by_date.get(run_date)
        frozen_by_symbol = {item.get("symbol"): item for item in (prior or {}).get("candidates", []) if isinstance(item, dict)}
        # A completed result is immutable/idempotent.
        if prior and prior.get("status") == "COMPLETE":
            outcomes.append({"run_date": run_date, "status": "ALREADY_COMPLETE",
                             "candidate_count": len(prior.get("candidates", []))})
            continue
        if not symbols:
            record = {"contract_id": CONTRACT_ID, "run_date": run_date,
                      "phase": "CANONICAL_CLOSE", "status": "NO_CANDIDATES",
                      "candidate_symbols": [], "candidate_count": 0, "candidates": [],
                      "evaluated_as_of": today.isoformat()}
            outcome_store.save_record(record)
            outcomes.append({"run_date": run_date, "status": record["status"], "candidate_count": 0})
            continue

        try:
            market = market_data_fetcher(
                symbols, islem_gunu=40, indirme_donemi="3mo", bugun=today
            )
        except Exception as exc:
            outcomes.append({"run_date": run_date, "status": "DATA_UNAVAILABLE",
                             "candidate_count": len(symbols), "detail": f"{type(exc).__name__}: {exc}"})
            continue

        raw_frames = dict(getattr(market, "veriler", {}) or {})
        frames = {_clean_symbol(symbol): _frame_rows(frame) for symbol, frame in raw_frames.items()}
        candidates: list[dict[str, Any]] = []
        for symbol in symbols:
            rows = frames.get(symbol, {})
            frozen = frozen_by_symbol.get(symbol, {})
            reference_date = base_date
            try:
                if frozen.get("reference_date"):
                    reference_date = date.fromisoformat(str(frozen["reference_date"])[:10])
            except ValueError:
                reference_date = base_date
            frozen_price = frozen.get("reference_price")
            base = rows.get(reference_date)
            reference_price = float(frozen_price) if frozen_price is not None else (base["close"] if base else None)
            future_dates = sorted(day for day in rows if day > max(base_date, reference_date))
            if reference_price is None:
                candidates.append({"symbol": symbol, "status": "PENDING_DATA",
                                   "reason": "REFERENCE_CLOSE_MISSING", "reference_price": None,
                                   "next_session_date": None, "next_session_close": None,
                                   "return_pct": None})
                continue
            if not future_dates:
                candidates.append({"symbol": symbol, "status": "PENDING_DATA",
                                   "reason": "NEXT_SESSION_CLOSE_NOT_AVAILABLE",
                                   "reference_price": reference_price, "next_session_date": None,
                                   "next_session_close": None, "return_pct": None})
                continue
            target_date = future_dates[0]
            target_close = rows[target_date]["close"]
            candidates.append({"symbol": symbol, "status": "COMPLETE",
                               "reason": None, "reference_price": reference_price,
                               "next_session_date": target_date.isoformat(),
                               "next_session_close": target_close,
                               "return_pct": (target_close / reference_price - 1.0) * 100.0})

        completed = [item for item in candidates if item["status"] == "COMPLETE"]
        returns = [float(item["return_pct"]) for item in completed]
        rising = sum(value > 0 for value in returns)
        falling = sum(value < 0 for value in returns)
        unchanged = sum(value == 0 for value in returns)
        pending = len(candidates) - len(completed)
        record = {
            "contract_id": CONTRACT_ID, "run_date": run_date, "phase": "CANONICAL_CLOSE",
            "status": "COMPLETE" if candidates and pending == 0 else "PENDING_DATA",
            "candidate_symbols": list(symbols), "candidate_count": len(symbols),
            "candidates": candidates, "evaluated_as_of": today.isoformat(),
            "summary": {
                "evaluated_count": len(completed), "pending_count": pending,
                "rising_count": rising, "falling_count": falling, "unchanged_count": unchanged,
                "hit_rate_pct": (rising / len(completed) * 100.0) if completed else None,
                "average_return_pct": (sum(returns) / len(returns)) if returns else None,
            },
        }
        outcome_store.save_record(record)
        outcomes.append({"run_date": run_date, "status": record["status"],
                         "candidate_count": len(symbols), "evaluated_count": len(completed),
                         "pending_count": pending})

    failures = sum(item.get("status") == "DATA_UNAVAILABLE" for item in outcomes)
    pending = sum(item.get("status") == "PENDING_DATA" for item in outcomes)
    return {"status": "PARTIAL_FAILURE" if failures else ("PENDING_DATA" if pending else "SUCCESS"),
            "processed_count": len(outcomes), "failure_count": failures,
            "results": outcomes, "archive_path": str(outcome_store.path)}
