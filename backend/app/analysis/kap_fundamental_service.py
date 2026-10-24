from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..data.fundamental_data import (
    FundamentalFreshnessResult,
    evaluate_fundamental_freshness,
)
from ..data.fundamental_store import (
    FundamentalJsonStore,
    FundamentalStoreResult,
)
from ..data.kap_fundamental_source import (
    KapFundamentalClient,
    KapFundamentalPackage,
)
from ..models.fundamental_models import FundamentalSnapshot
from .fundamental_analysis import build_fundamental_snapshot


@dataclass(frozen=True)
class KapFundamentalAnalysisResult:
    package: KapFundamentalPackage
    freshness: FundamentalFreshnessResult
    store_result: FundamentalStoreResult | None
    snapshot: FundamentalSnapshot | None
    locked: bool
    explanation: str


class KapFundamentalService:
    """KAP finansal veri alma, doğrulama, saklama ve analiz zinciri."""

    def __init__(
        self,
        *,
        client: KapFundamentalClient,
        store: FundamentalJsonStore | None = None,
    ) -> None:
        self._client = client
        self._store = store

    def analyze(
        self,
        symbol: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        today: date | None = None,
    ) -> KapFundamentalAnalysisResult:
        package = self._client.fetch(
            symbol,
            start_date=start_date,
            end_date=end_date,
        )

        freshness = evaluate_fundamental_freshness(
            package.periods,
            today=today,
        )

        if package.status.locked or freshness.locked:
            return KapFundamentalAnalysisResult(
                package=package,
                freshness=freshness,
                store_result=None,
                snapshot=None,
                locked=True,
                explanation=(
                    package.status.explanation
                    if package.status.locked
                    else freshness.explanation
                ),
            )

        store_result = (
            self._store.upsert(package.periods)
            if self._store is not None
            else None
        )
        snapshot = build_fundamental_snapshot(
            list(package.periods),
            source_metadata={
                "provider": package.status.source,
                "data_identity": package.status.data_identity,
                "fetched_at": package.status.fetched_at.isoformat(),
            },
        )

        return KapFundamentalAnalysisResult(
            package=package,
            freshness=freshness,
            store_result=store_result,
            snapshot=snapshot,
            locked=False,
            explanation=(
                "KAP finansal veri paketi doğrulandı ve temel "
                "analiz özeti üretildi."
            ),
        )
