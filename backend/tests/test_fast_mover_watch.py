from __future__ import annotations

import inspect

import pytest

from app.analysis import fast_mover_watch as fm
from app.analysis.fast_mover_watch import (
    FastMoverObservation,
    FastMoverState,
    FastMoverVisibilityPolicy,
    FastMoverWarning,
    evaluate_fast_mover,
    order_fast_movers,
)


@pytest.fixture()
def policy() -> FastMoverVisibilityPolicy:
    # Test-only calibration. Production thresholds are not defined here.
    return FastMoverVisibilityPolicy(
        min_rank_gain=20,
        min_percentile_gain=0.03,
        min_support_families=2,
        max_contradiction_families_for_main=0,
    )


def obs(symbol: str = "TEST", **changes) -> FastMoverObservation:
    values = dict(
        symbol=symbol,
        current_rank=20,
        previous_canonical_rank=60,
        current_universe_size=548,
        previous_universe_size=548,
        data_usable=True,
        baseline_comparable=True,
        support_families=("momentum", "volume"),
    )
    values.update(changes)
    return FastMoverObservation(**values)


def test_policy_requires_explicit_calibration():
    with pytest.raises(TypeError):
        FastMoverVisibilityPolicy()


def test_sudden_mover_can_be_visible_without_persistent_migration(policy):
    row = evaluate_fast_mover(obs("BAHKM_CASE"), policy)

    assert row.visible is True
    assert row.main_list_eligible is True
    assert row.state is FastMoverState.ANI_GUCLENME
    assert row.rank_gain == 40


def test_technical_strength_is_context_not_score(policy):
    row = evaluate_fast_mover(
        obs(
            "TGSAS_CASE",
            support_families=("technical_strength", "volume"),
        ),
        policy,
    )

    assert row.state is FastMoverState.TEKNIK_GUC_DESTEKLI
    assert not hasattr(row, "fast_mover_score")


def test_persistent_overlap_is_context_only(policy):
    row = evaluate_fast_mover(
        obs("MRGYO_CASE", early_visibility_overlap=True),
        policy,
    )

    assert row.main_list_eligible is True
    assert row.state is FastMoverState.PERSISTENT_OVERLAP
    assert "EARLY_VISIBILITY_OVERLAP" in row.reasons


def test_negative_control_is_not_main_list_eligible(policy):
    row = evaluate_fast_mover(
        obs(
            "BRKVY",
            previous_canonical_rank=90,
            support_families=("volume",),
            contradiction_families=("trend",),
        ),
        policy,
    )

    assert row.visible is True
    assert row.main_list_eligible is False
    assert row.state is FastMoverState.DIKKAT_DAR_TEYIT


def test_symbol_name_is_not_business_logic(policy):
    a = evaluate_fast_mover(obs("BRKVY"), policy)
    b = evaluate_fast_mover(obs("OTHER_SYMBOL"), policy)

    assert a.visible == b.visible
    assert a.main_list_eligible == b.main_list_eligible
    assert a.state == b.state


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"data_usable": False}, "DATA_NOT_USABLE"),
        ({"baseline_comparable": False}, "BASELINE_NOT_COMPARABLE"),
        ({"security_or_data_lock": True}, "SECURITY_OR_DATA_LOCK"),
        ({"proven_data_artifact": True}, "PROVEN_DATA_ARTIFACT"),
        ({"previous_canonical_rank": None}, "BASELINE_MISSING"),
    ],
)
def test_hard_blocks_fail_closed(policy, changes, reason):
    row = evaluate_fast_mover(obs(**changes), policy)

    assert row.visible is False
    assert row.main_list_eligible is False
    assert row.state is FastMoverState.BLOCKED
    assert reason in row.reasons


def test_non_material_movement_is_not_promoted(policy):
    row = evaluate_fast_mover(
        obs(current_rank=50, previous_canonical_rank=55),
        policy,
    )

    assert row.visible is False
    assert row.main_list_eligible is False
    assert row.state is None


def test_existing_positive_state_transition_can_establish_materiality(policy):
    row = evaluate_fast_mover(
        obs(
            current_rank=50,
            previous_canonical_rank=55,
            positive_state_transition=True,
        ),
        policy,
    )

    assert row.visible is True
    assert row.main_list_eligible is True


def test_warning_is_not_automatic_hard_block(policy):
    row = evaluate_fast_mover(
        obs(warnings=(FastMoverWarning.OVEREXTENDED,)),
        policy,
    )

    assert row.visible is True
    assert row.main_list_eligible is True
    assert row.warnings == (FastMoverWarning.OVEREXTENDED,)


def test_normalized_position_supports_different_universe_sizes(policy):
    row = evaluate_fast_mover(
        obs(
            current_rank=25,
            previous_canonical_rank=70,
            current_universe_size=500,
            previous_universe_size=600,
        ),
        policy,
    )

    assert row.current_percentile_position is not None
    assert row.previous_percentile_position is not None
    assert row.percentile_gain is not None


def test_presentation_order_does_not_mutate_main_rank(policy):
    stronger = evaluate_fast_mover(
        obs("STRONGER", previous_canonical_rank=120),
        policy,
    )
    weaker = evaluate_fast_mover(
        obs("WEAKER", previous_canonical_rank=50),
        policy,
    )

    ordered = order_fast_movers((weaker, stronger), by="rank_gain")

    assert [row.symbol for row in ordered] == ["STRONGER", "WEAKER"]
    assert stronger.current_rank == 20
    assert weaker.current_rank == 20


def test_module_has_no_io_or_persistence_authority():
    source = inspect.getsource(fm).lower()

    forbidden = (
        "requests.",
        "httpx.",
        "subprocess.",
        "sqlite3",
        "pathlib",
        "open(",
        ".write_text(",
        ".write_bytes(",
        "save_snapshot(",
        "rank_observations.jsonl",
    )

    for token in forbidden:
        assert token not in source