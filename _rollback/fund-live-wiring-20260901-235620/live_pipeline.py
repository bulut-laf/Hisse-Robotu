from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from backend.app.funds.analysis_engine import FundAnalysisResult, analyze_funds
from backend.app.funds.evidence_mapper import FundEvidenceInput, map_fund_evidence
from backend.app.funds.normalization import normalize_fund_code, parse_decimal_tr
from backend.app.funds.tefas_adapter import fetch_tefas_universe_rows


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

    return f"TEFAS:{code}"


def evidence_from_tefas_rows(
    rows: Iterable[Mapping[str, Any]],
) -> tuple:
    mapped = []

    for row in rows:
        mapped.append(
            map_fund_evidence(
                FundEvidenceInput(
                    canonical_fund_id=_canonical_id(row),
                    category_id=None,

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
    return analyze_tefas_rows(
        fetch_tefas_universe_rows()
    )
