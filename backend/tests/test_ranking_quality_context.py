from backend.app.analysis.ranking_quality_context import (
    QualityEvidence,
    build_quality_context,
    deduplicate_canonical_evidence,
    evidence_from_mapping,
    next_review_module,
)


def ev(family, state, source):
    return QualityEvidence(
        family=family,
        state=state,
        source_module=source,
    )


def test_duplicate_canonical_family_is_not_counted_twice():
    evidence = (
        ev("momentum", "positive", "Momentum Keşif"),
        ev("momentum", "positive", "Ön Yükseliş Hazırlık"),
        ev("trend", "positive", "Ana Research"),
    )
    unique = deduplicate_canonical_evidence(evidence)
    assert [item.family for item in unique] == ["momentum", "trend"]


def test_quality_context_is_explanatory_not_score():
    context = build_quality_context(
        symbol="AAA",
        evidence=(
            ev("trend", "positive", "Research"),
            ev("momentum", "positive", "Momentum"),
            ev("setup", "positive", "Ön Yükseliş"),
        ),
    )
    assert context.status == "DESTEKLENIYOR"
    assert context.unique_family_count == 3
    assert not hasattr(context, "score")
    assert not hasattr(context, "decision")


def test_data_block_is_hard_context_state():
    context = build_quality_context(
        symbol="AAA",
        evidence=(ev("momentum", "positive", "Momentum"),),
        data_blocked=True,
    )
    assert context.status == "VERI_BLOKLU"
    assert context.next_review_module == "Gecikmeli Veri Pilotu"


def test_setup_handoff_prefers_prebreakout_existing_module():
    target = next_review_module(
        (ev("setup", "strengthening", "Ön Yükseliş"),),
    )
    assert target == "Ön Yükseliş Hazırlık"


def test_momentum_handoff_uses_existing_module():
    target = next_review_module(
        (ev("momentum", "positive", "Momentum Keşif"),),
    )
    assert target == "Momentum Keşif"


def test_mapping_adapter_accepts_only_canonical_families():
    evidence = evidence_from_mapping(
        source_module="Existing Module",
        values={
            "momentum": "positive",
            "trend": "positive",
            "made_up_vote": "positive",
        },
    )
    assert [item.family for item in evidence] == ["momentum", "trend"]
