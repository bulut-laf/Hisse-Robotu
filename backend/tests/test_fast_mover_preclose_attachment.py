from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from backend.app.analysis.fast_mover_preclose_attachment import (
    build_preclose_fast_mover_observations,
)
from backend.app.analysis.ranking_memory import RankObservation


ISTANBUL = ZoneInfo("Europe/Istanbul")


def _candidate(
    symbol: str,
    *,
    score: float = 75.0,
    analysis_date: str = "2026-08-28T17:20:00+03:00",
):
    return SimpleNamespace(
        sembol=symbol,
        sinyal=SimpleNamespace(skor=score),
        analiz_tarihi=analysis_date,
    )


def _rank(
    *,
    as_of: str,
    symbol: str,
    rank: int,
    size: int = 548,
    profile: str = "dengeli",
    source: str = "BIST Tüm",
):
    return RankObservation(
        as_of=as_of,
        symbol=symbol,
        rank=rank,
        ranked_universe_size=size,
        universe_source=source,
        profile_name=profile,
    )


def test_current_result_order_becomes_current_partial_rank():
    now = datetime(2026, 8, 28, 17, 20, tzinfo=ISTANBUL)

    rows = build_preclose_fast_mover_observations(
        current_results=(
            _candidate("AAA.IS", score=81),
            _candidate("BBB.IS", score=79),
        ),
        observed_at=now,
        profile_name="dengeli",
        rank_observations=(
            _rank(as_of="2026-08-27", symbol="AAA", rank=44),
            _rank(as_of="2026-08-27", symbol="BBB", rank=10),
        ),
    )

    assert [row.symbol for row in rows] == ["AAA", "BBB"]
    assert [row.current_rank for row in rows] == [1, 2]
    assert [row.previous_canonical_rank for row in rows] == [44, 10]
    assert [row.current_universe_size for row in rows] == [2, 2]
    assert rows[0].research_score_current == 81.0


def test_latest_prior_canonical_snapshot_is_used():
    now = datetime(2026, 8, 28, 17, 20, tzinfo=ISTANBUL)

    rows = build_preclose_fast_mover_observations(
        current_results=(_candidate("AAA"),),
        observed_at=now,
        profile_name="dengeli",
        rank_observations=(
            _rank(as_of="2026-08-25", symbol="AAA", rank=80),
            _rank(as_of="2026-08-27", symbol="AAA", rank=25),
        ),
    )

    assert rows[0].previous_canonical_rank == 25


def test_same_day_rank_memory_is_never_used_as_1720_baseline():
    now = datetime(2026, 8, 28, 17, 20, tzinfo=ISTANBUL)

    rows = build_preclose_fast_mover_observations(
        current_results=(_candidate("AAA"),),
        observed_at=now,
        profile_name="dengeli",
        rank_observations=(
            _rank(
                as_of="2026-08-28T09:00:00+03:00",
                symbol="AAA",
                rank=2,
            ),
            _rank(as_of="2026-08-27", symbol="AAA", rank=40),
        ),
    )

    assert rows[0].previous_canonical_rank == 40


def test_profile_mismatch_does_not_create_comparable_baseline():
    now = datetime(2026, 8, 28, 17, 20, tzinfo=ISTANBUL)

    rows = build_preclose_fast_mover_observations(
        current_results=(_candidate("AAA"),),
        observed_at=now,
        profile_name="dengeli",
        rank_observations=(
            _rank(
                as_of="2026-08-27",
                symbol="AAA",
                rank=20,
                profile="agresif",
            ),
        ),
    )

    assert rows[0].previous_canonical_rank is None
    assert rows[0].baseline_comparable is False


def test_missing_baseline_fails_closed_without_dropping_current_row():
    now = datetime(2026, 8, 28, 17, 20, tzinfo=ISTANBUL)

    rows = build_preclose_fast_mover_observations(
        current_results=(_candidate("AAA"),),
        observed_at=now,
        profile_name="dengeli",
        rank_observations=(),
    )

    assert len(rows) == 1
    assert rows[0].previous_canonical_rank is None
    assert rows[0].previous_universe_size is None
    assert rows[0].baseline_comparable is False


def test_stale_current_analysis_is_marked_not_usable():
    now = datetime(2026, 8, 28, 17, 20, tzinfo=ISTANBUL)

    rows = build_preclose_fast_mover_observations(
        current_results=(
            _candidate(
                "AAA",
                analysis_date="2026-08-27T18:10:00+03:00",
            ),
        ),
        observed_at=now,
        profile_name="dengeli",
        rank_observations=(
            _rank(as_of="2026-08-27", symbol="AAA", rank=40),
        ),
    )

    assert rows[0].data_usable is False


def test_adapter_has_no_threshold_or_write_authority():
    source = Path(
        "backend/app/analysis/fast_mover_preclose_attachment.py"
    ).read_text(encoding="utf-8").lower()

    forbidden = (
        "append_snapshot(",
        "write_text(",
        "write_bytes(",
        "save_snapshot(",
        "fast_mover_score",
        "min_rank_gain=",
        "min_percentile_gain=",
    )

    for token in forbidden:
        assert token not in source


def test_preclose_result_contract_carries_raw_attachment_only():
    source = Path(
        "backend/app/operations/preclose_partial_daily_preview.py"
    ).read_text(encoding="utf-8")

    assert (
        "fast_mover_observations: tuple[FastMoverObservation, ...] = ()"
        in source
    )
    assert "build_preclose_fast_mover_observations(" in source
    assert "fast_mover_observations=fast_mover_observations" in source
    assert '"Durum": "PREVIEW · NOT CANONICAL · PARTIAL SESSION"' in source