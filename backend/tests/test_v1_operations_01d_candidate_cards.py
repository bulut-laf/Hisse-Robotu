from pathlib import Path


def _decision_card_block() -> str:
    dashboard = Path("backend/dashboard.py").read_text(encoding="utf-8")
    start = dashboard.index("V1_OPERATIONS_01D_DECISION_CARDS")
    end = dashboard.index(
        'st.caption(\n                "Aday sırası mevcut BIST Toplu Tarama',
        start,
    )
    return dashboard[start:end]


def test_v1_operations_01d_dashboard_has_candidate_decision_cards():
    block = _decision_card_block()

    assert 'st.markdown("##### Aday karar kartları")' in block
    assert "for _candidate_card in _morning_snapshot.candidates" in block
    assert "with st.expander(_candidate_title" in block
    assert '"Teknik skor"' in block
    assert '"Araştırma önceliği"' in block
    assert '"Hacim oranı"' in block
    assert '"Risk/Getiri"' in block
    assert '**Neden burada?**' in block
    assert '**Riskler**' in block


def test_v1_operations_01d_uses_existing_candidate_card_fields_only():
    block = _decision_card_block()

    expected_fields = (
        "rank",
        "symbol",
        "operational_status",
        "technical_score",
        "research_priority",
        "volume_ratio",
        "risk_reward",
        "technical_view",
        "visibility_state",
        "rank_change",
        "positive_reasons",
        "risks",
        "data_blocked",
    )

    for field in expected_fields:
        assert f"_candidate_card.{field}" in block

    assert "new_score" not in block
    assert "buy_signal" not in block
