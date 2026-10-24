from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class RankObservation:
    as_of: str
    symbol: str
    rank: int
    ranked_universe_size: int
    universe_source: str
    profile_name: str


def _clean_symbol(value: object) -> str:
    return str(value or "").removesuffix(".IS").upper().strip()


def _coerce_rank(value: object) -> int | None:
    try:
        rank = int(value)
    except (TypeError, ValueError):
        return None
    return rank if rank > 0 else None


def observations_from_research_rows(*, rows, as_of, universe_source, profile_name):
    materialized = tuple(rows)
    ranked_universe_size = len(materialized)

    if ranked_universe_size == 0:
        return ()

    observations = []

    for row in materialized:
        symbol = _clean_symbol(
            row.get("Hisse")
            or row.get("hisse")
            or row.get("symbol")
            or row.get("Symbol")
        )

        rank = _coerce_rank(
            row.get("Sıra")
            or row.get("Sira")
            or row.get("rank")
            or row.get("Rank")
        )

        if not symbol or rank is None:
            continue

        observations.append(
            RankObservation(
                as_of=str(as_of),
                symbol=symbol,
                rank=rank,
                ranked_universe_size=ranked_universe_size,
                universe_source=str(universe_source or ""),
                profile_name=str(profile_name or ""),
            )
        )

    return tuple(observations)


# RPV1_SPRINT03_PROFILE_RECORD_FAMILY
PROFILE_RECORD_TYPE = "research_profile"

@dataclass(frozen=True)
class ResearchProfileObservation:
    as_of: str
    symbol: str
    research_profile: str
    state: str
    direction: str
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    universe_name: str
    successful_universe_size: int
    recorded_at: str
    record_type: str = PROFILE_RECORD_TYPE

class RankObservationJsonlStore:
    """Append-only history of existing Research ranks.

    No scoring, ranking, signal, or trading authority.
    """

    def __init__(self, path=None):
        if path is None:
            project_root = Path(__file__).resolve().parents[3]
            path = project_root / "data" / "ranking_memory" / "rank_observations.jsonl"
        self.path = Path(path)

    @staticmethod
    def _key(item):
        return (
            item.as_of,
            item.symbol,
            item.universe_source,
            item.profile_name,
        )


    def list(self):
        # Rank reader stays backward compatible; profile records are ignored here.
        if not self.path.exists():
            return ()
        items = []
        for raw in self.path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            payload = json.loads(raw)
            if payload.get("record_type", "rank") != "rank":
                continue
            items.append(
                RankObservation(
                    as_of=payload["as_of"],
                    symbol=payload["symbol"],
                    rank=payload["rank"],
                    ranked_universe_size=payload["ranked_universe_size"],
                    universe_source=payload["universe_source"],
                    profile_name=payload["profile_name"],
                )
            )
        return tuple(items)

    def append_snapshot(self, observations):
        incoming = tuple(observations)
        if not incoming:
            return 0

        existing_keys = {self._key(item) for item in self.list()}
        new_items = [item for item in incoming if self._key(item) not in existing_keys]
        if not new_items:
            return 0

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            for item in new_items:
                handle.write(
                    json.dumps(asdict(item), ensure_ascii=False, sort_keys=True) + "\n"
                )
        return len(new_items)



    def list_profile_observations(self):
        if not self.path.exists():
            return ()
        items = []
        for raw in self.path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            payload = json.loads(raw)
            if payload.get("record_type") != PROFILE_RECORD_TYPE:
                continue
            items.append(
                ResearchProfileObservation(
                    as_of=str(payload["as_of"]),
                    symbol=_clean_symbol(payload["symbol"]),
                    research_profile=str(payload["research_profile"]),
                    state=str(payload["state"]),
                    direction=str(payload["direction"]),
                    reasons=tuple(payload.get("reasons", ())),
                    warnings=tuple(payload.get("warnings", ())),
                    universe_name=str(payload.get("universe_name", "")),
                    successful_universe_size=int(
                        payload.get("successful_universe_size", 0)
                    ),
                    recorded_at=str(payload.get("recorded_at", "")),
                )
            )
        return tuple(
            sorted(
                items,
                key=lambda item: (
                    item.as_of,
                    item.symbol,
                    item.research_profile,
                    item.recorded_at,
                ),
            )
        )

    @staticmethod
    def _profile_revision_key(item):
        return (
            item.as_of,
            item.symbol,
            item.research_profile,
            item.state,
            item.direction,
            tuple(item.reasons),
            tuple(item.warnings),
            item.universe_name,
            item.successful_universe_size,
        )

    def append_profile_snapshot(self, observations, *, activation_date):
        incoming = tuple(observations)
        if not incoming:
            return 0

        activation_iso = activation_date.isoformat()
        for item in incoming:
            if str(item.as_of)[:10] < activation_iso:
                raise ValueError(
                    "PROFILE_MEMORY_BACKFILL_BLOCKED: "
                    f"{item.as_of} < {activation_iso}"
                )

        existing_keys = {
            self._profile_revision_key(item)
            for item in self.list_profile_observations()
        }
        new_items = [
            item
            for item in incoming
            if self._profile_revision_key(item) not in existing_keys
        ]
        if not new_items:
            return 0

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            for item in new_items:
                handle.write(
                    json.dumps(
                        asdict(item),
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    + "\n"
                )
        return len(new_items)

def rank_history_for_symbol(observations, symbol):
    target = _clean_symbol(symbol)
    return tuple(
        sorted(
            (item for item in observations if item.symbol == target),
            key=lambda item: item.as_of,
        )
    )







