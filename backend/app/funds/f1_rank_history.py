from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
from typing import Iterable

DEFAULT_F1_RANK_HISTORY_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "funds"
    / "f1_rank_history.json"
)

@dataclass(frozen=True, slots=True)
class FundCategoryRankObservation:
    canonical_fund_id: str
    observation_date: date
    category_rank: int
    category_fund_count: int
    provider: str = "TEFAS"

class FundCategoryRankHistoryJsonStore:
    def __init__(self, path: str | Path = DEFAULT_F1_RANK_HISTORY_PATH) -> None:
        self.path = Path(path)

    def list_records(self) -> tuple[FundCategoryRankObservation, ...]:
        if not self.path.exists():
            return ()
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        out = []
        for row in raw:
            out.append(FundCategoryRankObservation(
                canonical_fund_id=str(row["canonical_fund_id"]),
                observation_date=date.fromisoformat(str(row["observation_date"])),
                category_rank=int(row["category_rank"]),
                category_fund_count=int(row["category_fund_count"]),
                provider=str(row.get("provider") or "TEFAS"),
            ))
        return tuple(out)

    def upsert(self, records: Iterable[FundCategoryRankObservation]) -> None:
        current = {
            (r.canonical_fund_id, r.observation_date): r
            for r in self.list_records()
        }
        for r in records:
            if r.category_rank <= 0 or r.category_fund_count <= 0:
                raise ValueError("F1_RANK_VALUES_MUST_BE_POSITIVE")
            if r.category_rank > r.category_fund_count:
                raise ValueError("F1_CATEGORY_RANK_EXCEEDS_FUND_COUNT")
            current[(r.canonical_fund_id, r.observation_date)] = r

        serial = [{
            "canonical_fund_id": r.canonical_fund_id,
            "observation_date": r.observation_date.isoformat(),
            "category_rank": r.category_rank,
            "category_fund_count": r.category_fund_count,
            "provider": r.provider,
        } for r in sorted(
            current.values(),
            key=lambda x: (x.canonical_fund_id, x.observation_date),
        )]

        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(serial, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

def fund_category_rank_history_store(
    path: str | Path | None = None,
) -> FundCategoryRankHistoryJsonStore:
    return FundCategoryRankHistoryJsonStore(path or DEFAULT_F1_RANK_HISTORY_PATH)
