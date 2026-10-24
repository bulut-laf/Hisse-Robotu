from datetime import date
import json

from backend.app.funds.international.erste_hungary_rank_history import (
    seed_rank_history,
    two_date_fund_count,
)


def _seed_row(isin: str, position: int = 1):
    return {
        "isin": isin,
        "category_normalized": "EQUITY",
        "rank_position": position,
        "category_size": 10,
        "rank_percentile": "0.90",
        "rank_score": "0.20",
    }


def test_seed_history_is_idempotent_for_same_natural_date(tmp_path):
    path = tmp_path / "history.json"
    rank_date = date(2026, 9, 24)

    first = seed_rank_history(
        [_seed_row("HU0000000001")],
        rank_date=rank_date,
        history_path=path,
    )
    second = seed_rank_history(
        [_seed_row("HU0000000001")],
        rank_date=rank_date,
        history_path=path,
    )

    assert first["inserted_count"] == 1
    assert second["inserted_count"] == 0
    assert second["skipped_existing_count"] == 1


def test_second_date_creates_two_date_history(tmp_path):
    path = tmp_path / "history.json"

    seed_rank_history(
        [_seed_row("HU0000000001")],
        rank_date=date(2026, 9, 24),
        history_path=path,
    )
    seed_rank_history(
        [_seed_row("HU0000000001", position=2)],
        rank_date=date(2026, 9, 25),
        history_path=path,
    )

    history = json.loads(path.read_text(encoding="utf-8"))
    assert len(history) == 2
    assert two_date_fund_count(history) == 1


def test_unranked_rows_are_not_forced_into_history(tmp_path):
    path = tmp_path / "history.json"

    row = {
        "isin": "HU0000000001",
        "category_normalized": "EQUITY",
        "rank_position": None,
        "category_size": 10,
        "rank_percentile": None,
        "rank_score": None,
    }

    result = seed_rank_history(
        [row],
        rank_date=date(2026, 9, 24),
        history_path=path,
    )

    assert result["inserted_count"] == 0
    assert result["history_row_count"] == 0