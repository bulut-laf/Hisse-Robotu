from __future__ import annotations

import pytest

from app.analysis.next_day_selection import (
    ExtensionState,
    NextDayCandidateEvidence,
    NextDayRole,
    ReboundState,
    STRATEGY_FROZEN,
    STRATEGY_ID,
    select_next_day_candidates,
)


def c(
    symbol: str,
    families: tuple[str, ...],
    *,
    rank: int = 20,
    **kwargs,
) -> NextDayCandidateEvidence:
    return NextDayCandidateEvidence(
        canonical_date="2026-08-28",
        symbol=symbol,
        research_rank=rank,
        evidence_families=families,
        **kwargs,
    )


def test_strategy_is_frozen_v1():
    assert STRATEGY_ID == "NEXT_DAY_SELECTION_STRATEGY_V1"
    assert STRATEGY_FROZEN is True


def test_primary_requires_three_families_structural_and_timing():
    result = select_next_day_candidates(
        (
            c("AAA", ("F1", "F3", "F4")),
            c("BBB", ("F3", "F4", "F5")),
            c("CCC", ("F1", "F2")),
        )
    )
    assert [x.symbol for x in result.primary] == ["AAA"]
    assert {x.symbol for x in result.reserve} == {"BBB", "CCC"}


def test_duplicate_family_ids_do_not_increase_breadth():
    result = select_next_day_candidates(
        (c("AAA", ("F3", "F3", "F3")),)
    )
    assert result.primary == ()
    assert result.reserve == ()
    assert result.excluded[0].exclusion_reason == "INSUFFICIENT_EVIDENCE_BREADTH"


def test_hard_contradiction_excludes_primary_and_reserve():
    result = select_next_day_candidates(
        (
            c(
                "AAA",
                ("F1", "F3", "F4", "F5"),
                hard_contradictions=("DATA_ARTIFACT",),
            ),
        )
    )
    assert result.primary == ()
    assert result.reserve == ()
    assert result.excluded[0].exclusion_reason == "HARD_CONTRADICTION"


def test_rebound_trap_excludes():
    result = select_next_day_candidates(
        (
            c(
                "AAA",
                ("F3", "F5"),
                rebound=ReboundState.TRAP,
            ),
        )
    )
    assert result.excluded[0].exclusion_reason == "REBOUND_TRAP"


def test_severe_extension_cannot_be_primary_but_may_be_reserve():
    result = select_next_day_candidates(
        (
            c(
                "AAA",
                ("F1", "F3", "F4"),
                extension=ExtensionState.SEVERE,
            ),
        )
    )
    assert result.primary == ()
    assert [x.symbol for x in result.reserve] == ["AAA"]


def test_single_factor_domination_cannot_be_primary():
    result = select_next_day_candidates(
        (
            c(
                "AAA",
                ("F1", "F3", "F4"),
                single_factor_domination=True,
            ),
        )
    )
    assert result.primary == ()
    assert [x.symbol for x in result.reserve] == ["AAA"]


def test_no_forced_fill():
    result = select_next_day_candidates(
        (
            c("AAA", ("F1", "F3", "F4")),
            c("BBB", ("F2", "F4")),
        )
    )
    assert len(result.primary) == 1
    assert len(result.reserve) == 1


def test_primary_lexicographic_order_is_deterministic():
    result = select_next_day_candidates(
        (
            c(
                "ZZZ",
                ("F1", "F3", "F4"),
                rank=5,
                readiness_rank=1,
                migration_rank=1,
                relative_strength_rank=1,
            ),
            c(
                "BBB",
                ("F1", "F2", "F3", "F4"),
                rank=30,
                readiness_rank=1,
                migration_rank=1,
                relative_strength_rank=1,
            ),
            c(
                "AAA",
                ("F1", "F2", "F3", "F4", "F5"),
                rank=1,
                soft_contradictions=("MILD",),
                readiness_rank=1,
                migration_rank=1,
                relative_strength_rank=1,
            ),
            c(
                "CCC",
                ("F1", "F2", "F3", "F4"),
                rank=10,
                readiness_rank=2,
                migration_rank=1,
                relative_strength_rank=1,
            ),
        )
    )
    assert [x.symbol for x in result.primary] == ["BBB", "CCC", "ZZZ", "AAA"]


def test_primary_overflow_becomes_near_primary_reserve():
    candidates = tuple(
        c(
            f"A{i}",
            ("F1", "F3", "F4"),
            rank=i,
            readiness_rank=i,
        )
        for i in range(1, 8)
    )
    result = select_next_day_candidates(candidates)
    assert len(result.primary) == 5
    assert [x.symbol for x in result.reserve] == ["A6", "A7"]


def test_maximum_five_primary_and_five_reserve():
    candidates = (
        tuple(
            c(f"P{i}", ("F1", "F3", "F4"), rank=i)
            for i in range(1, 8)
        )
        + tuple(
            c(f"R{i}", ("F2", "F4"), rank=100 + i)
            for i in range(1, 8)
        )
    )
    result = select_next_day_candidates(candidates)
    assert len(result.primary) == 5
    assert len(result.reserve) == 5


def test_evaluation_identity_is_stable_and_role_independent():
    result = select_next_day_candidates(
        (
            c("AAA.IS", ("F1", "F3", "F4")),
            c("BBB", ("F2", "F4")),
        )
    )
    all_selected = (*result.primary, *result.reserve)
    identities = {x.symbol: x.evaluation_identity for x in all_selected}
    assert identities["AAA"] == "NEXT_DAY_SELECTION_STRATEGY_V1|2026-08-28|AAA"
    assert identities["BBB"] == "NEXT_DAY_SELECTION_STRATEGY_V1|2026-08-28|BBB"


def test_explainability_snapshot_contains_contract_fields():
    result = select_next_day_candidates(
        (
            c(
                "AAA",
                ("F1", "F3", "F4"),
                soft_contradictions=("WEAK_VOLUME",),
                warnings=("CAUTION",),
            ),
        )
    )
    item = result.primary[0]
    assert item.role is NextDayRole.PRIMARY
    assert item.canonical_date == "2026-08-28"
    assert item.evidence_families == ("F1", "F3", "F4")
    assert item.contradiction_state == "SOFT"
    assert item.extension_state is ExtensionState.CLEAN
    assert item.rebound_state is ReboundState.NO
    assert item.exclusion_reason is None
    assert item.explanation
    assert item.next_action


def test_hard_data_gates_exclude():
    cases = (
        c("A1", ("F1", "F3", "F4"), data_ready=False),
        c("A2", ("F1", "F3", "F4"), freshness_valid=False),
        c("A3", ("F1", "F3", "F4"), security_lock=True),
        c("A4", ("F1", "F3", "F4"), universe_comparable=False),
        c("A5", ("F1", "F3", "F4"), research_valid=False),
    )
    result = select_next_day_candidates(cases)
    assert result.primary == ()
    assert result.reserve == ()
    assert {x.exclusion_reason for x in result.excluded} == {
        "DATA_NOT_READY",
        "STALE_DATA",
        "SECURITY_LOCK",
        "UNIVERSE_NOT_COMPARABLE",
        "RESEARCH_INVALID",
    }


def test_unknown_family_fails_closed():
    with pytest.raises(ValueError, match="Unknown evidence family"):
        select_next_day_candidates((c("AAA", ("F1", "F9")),))


def test_mixed_canonical_dates_fail_closed():
    first = c("AAA", ("F1", "F3", "F4"))
    second = NextDayCandidateEvidence(
        canonical_date="2026-08-27",
        symbol="BBB",
        research_rank=2,
        evidence_families=("F1", "F3", "F4"),
    )
    with pytest.raises(ValueError, match="canonical_date"):
        select_next_day_candidates((first, second))
