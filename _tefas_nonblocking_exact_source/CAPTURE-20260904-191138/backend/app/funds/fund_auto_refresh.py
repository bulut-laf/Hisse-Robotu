from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .f4_snapshot import fetch_tefas_detail_observation
from .kap_free_float_auto_population import (
    MAX_FDO_SYMBOLS_PER_REFRESH,
    populate_kap_free_float_for_symbols,
)
from .kap_portfolio_auto_ingestion import auto_ingest_kap_portfolio_reports
from .portfolio_tracking import (
    FundPortfolioSnapshotJsonStore,
    fund_portfolio_snapshot_store,
)
from .pressure_read_model import build_fund_pressure_read_model
from .store import FundObservationJsonStore, fund_observation_store
from .tefas_history_population import populate_tefas_history_batch
from .free_float_store import default_free_float_store


DEFAULT_AUTO_REFRESH_STATE = (
    Path(__file__).resolve().parents[2] / "data" / "funds" / "auto_refresh_state.json"
)


@dataclass(frozen=True, slots=True)
class FundAutoRefreshOutcome:
    fund_code: str
    attempted: bool
    refreshed: bool
    detail_written: bool
    history_written: bool
    portfolio_checked: bool
    fdo_checked: bool
    warnings: tuple[str, ...]


def _read_state(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_state(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temp.replace(path)


def _due(
    state: dict[str, object],
    fund_code: str,
    now: datetime,
    *,
    success_interval: timedelta,
    failure_interval: timedelta,
) -> bool:
    item = state.get(fund_code)
    if not isinstance(item, dict):
        return True
    raw = item.get("last_success_utc") or item.get("last_attempt_utc")
    if not raw:
        return True
    try:
        last = datetime.fromisoformat(str(raw))
    except Exception:
        return True
    if last.tzinfo is None:
        return True
    interval = success_interval if item.get("last_success_utc") else failure_interval
    return now - last >= interval


def _held_symbols(
    store: FundPortfolioSnapshotJsonStore,
    canonical_fund_id: str,
) -> tuple[str, ...]:
    candidates = [
        item for item in store.list_snapshots()
        if item.canonical_fund_id == canonical_fund_id
    ]
    if not candidates:
        return ()
    latest = max(
        candidates,
        key=lambda item: (
            item.portfolio_date,
            item.publication_date,
            item.ingested_at,
        ),
    )
    return tuple(sorted({
        position.symbol
        for position in latest.positions
        if position.asset_type == "EQUITY"
    }))


def auto_refresh_selected_fund_if_due(
    fund_code: str,
    *,
    observation_store: FundObservationJsonStore | None = None,
    portfolio_store: FundPortfolioSnapshotJsonStore | None = None,
    state_path: str | Path | None = None,
    network_enabled: bool = True,
    now: datetime | None = None,
) -> FundAutoRefreshOutcome:
    code = str(fund_code or "").strip().upper()
    if not code:
        raise ValueError("FUND_AUTO_REFRESH_CODE_EMPTY")

    observations = observation_store or fund_observation_store()
    portfolios = portfolio_store or fund_portfolio_snapshot_store()
    state_file = Path(state_path) if state_path is not None else DEFAULT_AUTO_REFRESH_STATE
    stamp = now or datetime.now(timezone.utc)
    if stamp.tzinfo is None:
        raise ValueError("FUND_AUTO_REFRESH_NOW_TZ_REQUIRED")

    state = _read_state(state_file)
    if not _due(
        state,
        code,
        stamp,
        success_interval=timedelta(hours=6),
        failure_interval=timedelta(hours=1),
    ):
        return FundAutoRefreshOutcome(
            fund_code=code,
            attempted=False,
            refreshed=False,
            detail_written=False,
            history_written=False,
            portfolio_checked=False,
            fdo_checked=False,
            warnings=(),
        )

    warnings: list[str] = []
    detail_written = history_written = portfolio_checked = fdo_checked = False

    if not network_enabled:
        return FundAutoRefreshOutcome(
            fund_code=code,
            attempted=False,
            refreshed=False,
            detail_written=False,
            history_written=False,
            portfolio_checked=False,
            fdo_checked=False,
            warnings=("NETWORK_DISABLED",),
        )

    try:
        detail = fetch_tefas_detail_observation(code, fetched_at=stamp)
        observations.upsert((detail,))
        detail_written = True
    except Exception as exc:
        warnings.append(f"TEFAS_DETAIL:{exc}")

    try:
        populate_tefas_history_batch(
            (code,),
            store=observations,
            maximum_funds=1,
            fetched_at=stamp,
            source_as_of=stamp,
        )
        history_written = True
    except Exception as exc:
        warnings.append(f"TEFAS_HISTORY:{exc}")

    try:
        auto_ingest_kap_portfolio_reports(
            store=portfolios,
            fund_codes=(code,),
            network_enabled=True,
        )
        portfolio_checked = True
    except Exception as exc:
        warnings.append(f"KAP_PORTFOLIO:{exc}")

    canonical_id = f"fund:tefas:{code}"
    symbols = _held_symbols(portfolios, canonical_id)[:MAX_FDO_SYMBOLS_PER_REFRESH]
    if symbols:
        try:
            populate_kap_free_float_for_symbols(
                store=default_free_float_store(),
                symbols=symbols,
                network_enabled=True,
            )
            fdo_checked = True
        except Exception as exc:
            warnings.append(f"KAP_FDO:{exc}")

        try:
            build_fund_pressure_read_model(portfolios)
        except Exception as exc:
            warnings.append(f"PRESSURE:{exc}")

    success = detail_written or history_written or portfolio_checked or fdo_checked
    state[code] = {
        "last_attempt_utc": stamp.isoformat(),
        "last_success_utc": stamp.isoformat() if success else None,
        "warnings": warnings[-10:],
    }
    _write_state(state_file, state)

    return FundAutoRefreshOutcome(
        fund_code=code,
        attempted=True,
        refreshed=success,
        detail_written=detail_written,
        history_written=history_written,
        portfolio_checked=portfolio_checked,
        fdo_checked=fdo_checked,
        warnings=tuple(warnings),
    )
