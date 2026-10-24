from __future__ import annotations

from pathlib import Path
import pickle


SNAPSHOT_PATH = Path("backend/cache/bist_daily_market_last_snapshot.pkl")


def save_market_snapshot(result: object) -> None:
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SNAPSHOT_PATH.open("wb") as handle:
        pickle.dump(result, handle)


def load_market_snapshot() -> object | None:
    if not SNAPSHOT_PATH.exists():
        return None

    with SNAPSHOT_PATH.open("rb") as handle:
        return pickle.load(handle)
