from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from backend.app.funds.analysis_engine import FundAnalysisResult, analyze_funds
from backend.app.funds.evidence_mapper import FundEvidenceInput, map_fund_evidence
from backend.app.funds.normalization import normalize_fund_code, normalize_text, parse_decimal_tr
from backend.app.funds.tefas_adapter import canonical_tefas_fund_id, fetch_tefas_universe_rows


def _pick(row: Mapping[str, Any], *names: str) -> Any:
    values = {str(key).casefold(): value for key, value in row.items()}

    for name in names:
        value = values.get(name.casefold())
        if value not in (None, ""):
            return value

    return None


def _canonical_id(row: Mapping[str, Any]) -> str:
    raw_code = _pick(
        row,
        "fonkod",
        "fonkodu",
        "fund_code",
        "provider_fund_id",
        "code",
    )

    code = normalize_fund_code(raw_code)

    if not code:
        raise ValueError("TEFAS_FUND_CODE_MISSING")

    return canonical_tefas_fund_id(code)


_LAST_LIVE_FUND_METADATA: dict[str, dict[str, str]] = {}


def _capture_live_fund_metadata(rows: Iterable[Mapping[str, Any]]) -> None:
    captured: dict[str, dict[str, str]] = {}
    for row in rows:
        fund_id = _canonical_id(row)
        code = fund_id.rsplit(":", 1)[-1]
        name = normalize_text(_pick(row, "fonUnvan", "fund_name", "name"))
        category = normalize_text(
            _pick(row, "fonTurAciklama", "category_name", "category_id")
        )
        captured[fund_id] = {
            "fund_code": code,
            "fund_name": name,
            "category_name": category,
        }
    _LAST_LIVE_FUND_METADATA.clear()
    _LAST_LIVE_FUND_METADATA.update(captured)


def get_last_live_fund_metadata() -> dict[str, dict[str, str]]:
    return {key: dict(value) for key, value in _LAST_LIVE_FUND_METADATA.items()}



def evidence_from_tefas_rows(
    rows: Iterable[Mapping[str, Any]],
) -> tuple:
    mapped = []

    for row in rows:
        mapped.append(
            map_fund_evidence(
                FundEvidenceInput(
                    canonical_fund_id=_canonical_id(row),
                    category_id=(
                        normalize_text(
                            _pick(row, "fonTurAciklama", "category_name", "category_id")
                        )
                        or None
                    ),
                    # F1 = UNAVAILABLE
                    category_rank_percentile=None,
                    category_rank_change=None,

                    # F2 = VERIFIED TEFAS LIVE
                    return_1m=parse_decimal_tr(
                        _pick(row, "getiri1a"),
                        percent=True,
                    ),
                    return_3m=parse_decimal_tr(
                        _pick(row, "getiri3a"),
                        percent=True,
                    ),
                    return_6m=parse_decimal_tr(
                        _pick(row, "getiri6a"),
                        percent=True,
                    ),

                    # F3 = UNAVAILABLE
                    volatility_percentile=None,
                    max_drawdown=None,

                    # F4 = UNAVAILABLE
                    fund_size_change=None,
                    investor_change=None,
                    net_flow_ratio=None,

                    # F5 = UNAVAILABLE
                    total_expense_ratio=None,
                    regime_fit=None,
                    allocation_known=False,
                )
            )
        )

    return tuple(mapped)


def analyze_tefas_rows(
    rows: Iterable[Mapping[str, Any]],
) -> tuple[FundAnalysisResult, ...]:
    return analyze_funds(
        evidence_from_tefas_rows(rows)
    )


def run_live_fund_analysis() -> tuple[FundAnalysisResult, ...]:
    """
    F2 = live TEFAS universe.
    F3/F4 = persisted observation store.

    No history/detail network call during UI rendering.
    """
    rows = fetch_tefas_universe_rows()
    _capture_live_fund_metadata(rows)
    from backend.app.funds.fund_store_read_model import (
        analyze_tefas_rows_with_store_evidence,
    )
    from backend.app.funds.store import (
        fund_observation_store,
    )

    return analyze_tefas_rows_with_store_evidence(
        rows,
        store=fund_observation_store(),
    )
