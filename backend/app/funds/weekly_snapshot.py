from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Iterable

from .analysis_engine import FundAnalysisResult


@dataclass(frozen=True, slots=True)
class FundWeeklySnapshot:
    week_ending: date
    observed_at: datetime
    results: tuple[FundAnalysisResult, ...]
    observation_mode: str = "MANUAL_OR_PROVIDER_RUNTIME"
    scheduler_authority: str = "NONE"


def build_weekly_snapshot(week_ending: date, results: Iterable[FundAnalysisResult], *, observed_at: datetime | None = None) -> FundWeeklySnapshot:
    items = tuple(results)
    unique = {item.canonical_fund_id: item for item in items}
    if len(unique) != len(items):
        raise ValueError("DUPLICATE_FUND_WEEKLY_SNAPSHOT")
    return FundWeeklySnapshot(week_ending, observed_at or datetime.now(timezone.utc), tuple(unique[key] for key in sorted(unique)))


class FundWeeklySnapshotStore:
    def __init__(self, path: str | Path) -> None: self.path = Path(path)

    def append(self, snapshot: FundWeeklySnapshot) -> str:
        payload = {
            "week_ending": snapshot.week_ending.isoformat(), "observed_at": snapshot.observed_at.isoformat(),
            "observation_mode": snapshot.observation_mode, "scheduler_authority": snapshot.scheduler_authority,
            "results": [{"canonical_fund_id": x.canonical_fund_id, "category_id": x.category_id,
                         "classification": x.classification.value, "reason": x.eligibility_reason,
                         "engine_version": x.engine_version} for x in snapshot.results],
        }
        digest_source = {**payload, "observed_at": None}
        payload["digest"] = hashlib.sha256(json.dumps(digest_source, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        existing = [] if not self.path.exists() else [json.loads(x) for x in self.path.read_text(encoding="utf-8").splitlines() if x.strip()]
        same_week = [x for x in existing if x.get("week_ending") == payload["week_ending"]]
        if same_week:
            if len(same_week) == 1 and same_week[0].get("digest") == payload["digest"]: return "ALREADY_PRESENT"
            raise ValueError("WEEKLY_SNAPSHOT_CONFLICT")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        return "APPENDED"
