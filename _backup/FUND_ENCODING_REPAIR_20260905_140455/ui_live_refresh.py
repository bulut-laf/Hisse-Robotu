from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from .analysis_engine import FundAnalysisResult


FundAnalysisLoader = Callable[[], Iterable[FundAnalysisResult]]


@dataclass(frozen=True, slots=True)
class FundLiveRefreshOutcome:
    results: tuple[FundAnalysisResult, ...]
    refreshed: bool
    error_message: str | None = None


def refresh_fund_analysis_if_requested(
    *,
    requested: bool,
    current_results: Iterable[FundAnalysisResult] = (),
    loader: FundAnalysisLoader | None = None,
) -> FundLiveRefreshOutcome:
    """Run TEFAS live analysis only after an explicit UI action."""
    current = tuple(current_results)
    if not requested:
        return FundLiveRefreshOutcome(results=current, refreshed=False)

    if loader is None:
        from .live_pipeline import run_live_fund_analysis

        loader = run_live_fund_analysis

    try:
        refreshed = tuple(loader())
        if not refreshed:
            return FundLiveRefreshOutcome(
                results=current,
                refreshed=False,
                error_message="TEFAS_EMPTY_RESULT",
            )
    except Exception as exc:  # UI boundary: preserve last good state on refresh failure.
        return FundLiveRefreshOutcome(
            results=current,
            refreshed=False,
            error_message=str(exc) or exc.__class__.__name__,
        )

    return FundLiveRefreshOutcome(results=refreshed, refreshed=True)

