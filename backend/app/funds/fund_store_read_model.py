from __future__ import annotations

from collections.abc import Iterable, Mapping

from .analysis_engine import FundAnalysisResult, analyze_funds
from .f3_store_read_model import (
    enrich_evidence_maps_with_f3_store,
)
from .f4_store_read_model import (
    enrich_evidence_maps_with_f4_store,
)
from .live_pipeline import evidence_from_tefas_rows
from .store import FundObservationJsonStore


def analyze_tefas_rows_with_store_evidence(
    rows: Iterable[Mapping[str, object]],
    *,
    store: FundObservationJsonStore,
) -> tuple[FundAnalysisResult, ...]:
    base = evidence_from_tefas_rows(rows)

    with_f3 = enrich_evidence_maps_with_f3_store(
        base,
        store=store,
    )

    with_f4 = enrich_evidence_maps_with_f4_store(
        with_f3,
        store=store,
    )

    return analyze_funds(
        with_f4
    )
