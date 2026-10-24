
from datetime import date

from backend.app.analysis.ranking_memory import (
    RankObservation,
    RankObservationJsonlStore,
    ResearchProfileObservation,
)
from backend.app.analysis.research_profile_memory import (
    build_profile_lifecycle,
    persist_research_profile_bundle,
)
from backend.app.analysis.research_profiles import FundamentalSnapshot
from backend.app.analysis.research_profiles_daily import (
    build_daily_research_profiles_from_snapshots,
)

AS_OF = date(2026, 8, 26)


def obs(day, state, recorded="2026-08-26T10:00:00+00:00", reasons=()):
    return ResearchProfileObservation(
        as_of=day,
        symbol="AAA",
        research_profile="EARNINGS_INFLECTION",
        state=state,
        direction="POSITIVE",
        reasons=tuple(reasons),
        warnings=(),
        universe_name="BIST Tüm",
        successful_universe_size=548,
        recorded_at=recorded,
    )


def bundle(day):
    snap = FundamentalSnapshot(
        symbol="AAA.IS",
        latest_ebitda=100,
        latest_operating_profit=80,
        revenue_yoy_pct=20,
        gross_margin_delta_pp=3,
        ebitda_margin_delta_pp=4,
        operating_profit_yoy_pct=40,
        ttm_cfo=10,
        net_cash=20,
        cfo_direction="improving",
        leverage_direction="stable",
    )
    return build_daily_research_profiles_from_snapshots({"AAA.IS": snap}, as_of=day)


def test_mixed_memory_file_preserves_rank_reader(tmp_path):
    store = RankObservationJsonlStore(tmp_path / "rank_observations.jsonl")
    rank = RankObservation("2026-08-25", "AAA", 10, 97, "XUTUM", "Dengeli")
    assert store.append_snapshot((rank,)) == 1
    assert store.append_profile_snapshot((obs("2026-08-26", "MATCH"),), activation_date=AS_OF) == 1
    assert store.list() == (rank,)
    assert len(store.list_profile_observations()) == 1


def test_same_physical_file_no_sibling_store(tmp_path):
    store = RankObservationJsonlStore(tmp_path / "rank_observations.jsonl")
    store.append_profile_snapshot((obs("2026-08-26", "MATCH"),), activation_date=AS_OF)
    assert store.path.exists()
    assert not (tmp_path / "profile_observations.jsonl").exists()


def test_pre_activation_profile_write_is_blocked(tmp_path):
    store = RankObservationJsonlStore(tmp_path / "rank_observations.jsonl")
    try:
        store.append_profile_snapshot((obs("2026-08-25", "MATCH"),), activation_date=AS_OF)
    except ValueError as exc:
        assert "PROFILE_MEMORY_BACKFILL_BLOCKED" in str(exc)
    else:
        raise AssertionError("backfill must be blocked")


def test_identical_same_day_revision_is_idempotent(tmp_path):
    store = RankObservationJsonlStore(tmp_path / "rank_observations.jsonl")
    item = obs("2026-08-26", "MATCH")
    assert store.append_profile_snapshot((item,), activation_date=AS_OF) == 1
    assert store.append_profile_snapshot((item,), activation_date=AS_OF) == 0


def test_changed_same_day_state_is_append_only_revision(tmp_path):
    store = RankObservationJsonlStore(tmp_path / "rank_observations.jsonl")
    first = obs("2026-08-26", "INSUFFICIENT", "2026-08-26T09:00:00+00:00")
    second = obs("2026-08-26", "MATCH", "2026-08-26T12:00:00+00:00")
    assert store.append_profile_snapshot((first,), activation_date=AS_OF) == 1
    assert store.append_profile_snapshot((second,), activation_date=AS_OF) == 1
    assert [x.state for x in store.list_profile_observations()] == ["INSUFFICIENT", "MATCH"]


def test_lifecycle_entry_streak_and_exit():
    history = (
        obs("2026-08-26", "MATCH", "2026-08-26T12:00:00+00:00"),
        obs("2026-08-27", "MATCH", "2026-08-27T12:00:00+00:00"),
    )
    ctx = build_profile_lifecycle(history, symbol="AAA", research_profile="EARNINGS_INFLECTION")
    assert ctx.first_match == "2026-08-26"
    assert ctx.last_match == "2026-08-27"
    assert ctx.consecutive_match_sessions == 2
    assert ctx.profile_age_sessions == 2
    assert ctx.event is None

    history += (
        obs(
            "2026-08-28",
            "BLOCKED",
            "2026-08-28T12:00:00+00:00",
            reasons=("BLOCK_DIRECTION_NEGATIVE",),
        ),
    )
    ctx = build_profile_lifecycle(history, symbol="AAA", research_profile="EARNINGS_INFLECTION")
    assert ctx.event == "EXIT"
    assert ctx.consecutive_match_sessions == 0
    assert ctx.block_reason == "BLOCK_DIRECTION_NEGATIVE"


def test_non_bist_tum_is_never_persisted(tmp_path):
    store = RankObservationJsonlStore(tmp_path / "rank_observations.jsonl")
    result = persist_research_profile_bundle(
        bundle(AS_OF), universe_name="BIST 100", store=store
    )
    assert result.status == "SKIPPED_NON_CANONICAL_UNIVERSE"
    assert not store.path.exists()


def test_pre_activation_bundle_is_warming_up(tmp_path):
    store = RankObservationJsonlStore(tmp_path / "rank_observations.jsonl")
    result = persist_research_profile_bundle(
        bundle(date(2026, 8, 25)), universe_name="BIST Tüm", store=store
    )
    assert result.status == "WARMING_UP"
    assert not store.path.exists()


def test_canonical_bundle_persists_three_profile_states(tmp_path):
    store = RankObservationJsonlStore(tmp_path / "rank_observations.jsonl")
    result = persist_research_profile_bundle(
        bundle(AS_OF), universe_name="BIST Tüm", store=store
    )
    assert result.status == "WRITTEN"
    assert result.appended == 3
    assert len(store.list_profile_observations()) == 3
