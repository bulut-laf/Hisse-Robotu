from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .daily_buy_decision_threshold_recommendation import ThresholdRecommendation

PENDING = "BEKLİYOR"
APPROVED = "ONAYLANDI"
REJECTED = "REDDEDİLDİ"
VALID_STATUSES = (PENDING, APPROVED, REJECTED)

DEFAULT_GOVERNANCE_PATH = Path("data/daily_buy_decision_recommendation_governance.json")


@dataclass(frozen=True)
class RecommendationGovernanceRecord:
    recommendation_id: str
    dimension: str
    horizon: str
    recommendation: str
    preferred_segment: str | None
    review_segment: str | None
    evidence: str
    sample_size: int
    status: str = PENDING
    created_at: str = ""
    reviewed_at: str | None = None


def recommendation_id(item: ThresholdRecommendation) -> str:
    raw = "|".join(
        (
            item.dimension,
            item.horizon,
            item.recommendation,
            item.preferred_segment or "",
            item.review_segment or "",
            item.evidence,
            str(item.sample_size),
        )
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def sync_governance_records(
    records: Iterable[RecommendationGovernanceRecord],
    recommendations: Iterable[ThresholdRecommendation],
    *,
    now: datetime | None = None,
) -> tuple[RecommendationGovernanceRecord, ...]:
    """Register unseen recommendations without changing any decision threshold."""

    timestamp = (now or datetime.now(timezone.utc)).isoformat()
    existing = {item.recommendation_id: item for item in records}

    for recommendation in recommendations:
        rec_id = recommendation_id(recommendation)
        if rec_id in existing:
            continue
        existing[rec_id] = RecommendationGovernanceRecord(
            recommendation_id=rec_id,
            dimension=recommendation.dimension,
            horizon=recommendation.horizon,
            recommendation=recommendation.recommendation,
            preferred_segment=recommendation.preferred_segment,
            review_segment=recommendation.review_segment,
            evidence=recommendation.evidence,
            sample_size=recommendation.sample_size,
            status=PENDING,
            created_at=timestamp,
        )

    return tuple(sorted(existing.values(), key=lambda item: (item.created_at, item.recommendation_id)))


def review_governance_record(
    records: Iterable[RecommendationGovernanceRecord],
    recommendation_id_value: str,
    status: str,
    *,
    now: datetime | None = None,
) -> tuple[RecommendationGovernanceRecord, ...]:
    if status not in (APPROVED, REJECTED):
        raise ValueError("Governance review status ONAYLANDI veya REDDEDİLDİ olmalıdır.")

    timestamp = (now or datetime.now(timezone.utc)).isoformat()
    found = False
    updated: list[RecommendationGovernanceRecord] = []
    for item in records:
        if item.recommendation_id == recommendation_id_value:
            found = True
            updated.append(replace(item, status=status, reviewed_at=timestamp))
        else:
            updated.append(item)

    if not found:
        raise ValueError("Governance recommendation id bulunamadı.")
    return tuple(updated)


class RecommendationGovernanceJsonStore:
    def __init__(self, path: Path | str = DEFAULT_GOVERNANCE_PATH) -> None:
        self.path = Path(path)

    def load(self) -> tuple[RecommendationGovernanceRecord, ...]:
        if not self.path.exists():
            return ()
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("Governance store list biçiminde olmalıdır.")
        records: list[RecommendationGovernanceRecord] = []
        for item in payload:
            if not isinstance(item, dict):
                raise ValueError("Governance store kaydı object biçiminde olmalıdır.")
            record = RecommendationGovernanceRecord(**item)
            if record.status not in VALID_STATUSES:
                raise ValueError("Governance store geçersiz durum içeriyor.")
            records.append(record)
        return tuple(records)

    def save(self, records: Iterable[RecommendationGovernanceRecord]) -> None:
        values = tuple(records)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps([asdict(item) for item in values], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def governance_rows(
    records: Iterable[RecommendationGovernanceRecord],
) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "ID": item.recommendation_id,
            "Boyut": item.dimension,
            "Ufuk": item.horizon,
            "Öneri": item.recommendation,
            "Durum": item.status,
            "Desteklenen segment": item.preferred_segment or "-",
            "İncelenecek segment": item.review_segment or "-",
            "Örnek": item.sample_size,
            "Kanıt": item.evidence,
            "Oluşturma": item.created_at,
            "İnceleme": item.reviewed_at or "-",
        }
        for item in records
    )
