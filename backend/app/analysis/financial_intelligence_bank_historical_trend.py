from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from app.analysis.financial_intelligence_bank_canonical_adapter import (
    adapt_bank_canonical_input,
)
from app.analysis.financial_intelligence_bank_official_bundle_record import (
    build_bank_official_bundle_record,
)
from app.analysis.financial_intelligence_bank_production_source_onboarding import (
    evaluate_bank_production_source,
)
from app.analysis.financial_intelligence_bank_scoring_engine import (
    score_bank_model,
)


@dataclass(frozen=True)
class BankHistoricalSnapshot:
    symbol: str
    period_end: str
    as_of: str
    publication_date: str
    source_uri: str
    total_score: float
    model_version: str
    canonical_facts: Mapping[str, Any]
    component_scores: Mapping[str, float]
    metric_scores: Mapping[str, float]
    read_only: bool = True


@dataclass(frozen=True)
class BankHistoricalTrend:
    symbol: str
    snapshots: tuple[BankHistoricalSnapshot, ...]
    read_only: bool = True


def _snapshot_from_bundle(
    path: Path,
    *,
    expected_symbol: str,
) -> BankHistoricalSnapshot | None:
    record = build_bank_official_bundle_record(path)

    if record is None:
        return None

    symbol = str(
        record.get("symbol", "")
    ).strip().upper()

    if symbol != expected_symbol:
        return None

    onboarding = evaluate_bank_production_source(
        record
    )

    if onboarding.status != "PASS":
        return None

    if onboarding.blocker is not None:
        return None

    if not onboarding.canonical_input_ready:
        return None

    if not onboarding.scoring_ready:
        return None

    if not onboarding.production_evidence:
        return None

    if not onboarding.activation_ready:
        return None

    canonical = adapt_bank_canonical_input(
        record
    )

    if canonical.status != "PASS":
        return None

    if canonical.payload is None:
        return None

    scored = score_bank_model(
        canonical.payload
    )

    if scored.status != "PASS":
        return None

    if scored.blocker is not None:
        return None

    if scored.total_score is None:
        return None

    facts = record.get("canonical_facts")

    if not isinstance(facts, Mapping):
        return None

    return BankHistoricalSnapshot(
        symbol=symbol,
        period_end=str(
            record.get("period_end", "")
        ),
        as_of=str(
            onboarding.as_of or ""
        ),
        publication_date=str(
            onboarding.publication_date or ""
        ),
        source_uri=str(
            onboarding.source_uri or ""
        ),
        total_score=float(
            scored.total_score
        ),
        model_version=str(
            scored.model_version
        ),
        canonical_facts=dict(facts),
        component_scores=dict(
            scored.component_scores
        ),
        metric_scores=dict(
            scored.metric_scores
        ),
        read_only=True,
    )


def build_bank_historical_trend(
    project_root: str | Path,
    symbol: str,
) -> BankHistoricalTrend:
    root = Path(project_root)

    normalized_symbol = str(
        symbol
    ).strip().upper()

    fi_dir = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
    )

    snapshots: list[
        BankHistoricalSnapshot
    ] = []

    for path in sorted(
        fi_dir.glob(
            f"{normalized_symbol}_*_OFFICIAL_EVIDENCE_BUNDLE.json"
        )
    ):
        snapshot = _snapshot_from_bundle(
            path,
            expected_symbol=normalized_symbol,
        )

        if snapshot is not None:
            snapshots.append(snapshot)

    snapshots.sort(
        key=lambda item: (
            item.period_end,
            item.publication_date,
            item.as_of,
            item.source_uri,
        )
    )

    return BankHistoricalTrend(
        symbol=normalized_symbol,
        snapshots=tuple(snapshots),
        read_only=True,
    )


__all__ = [
    "BankHistoricalSnapshot",
    "BankHistoricalTrend",
    "build_bank_historical_trend",
]