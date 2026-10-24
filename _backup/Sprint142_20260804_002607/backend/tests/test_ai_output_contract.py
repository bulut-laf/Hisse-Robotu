from backend.app.market_context.ai_output_contract import (
    AIEvaluationReport,
)


def test_ai_output_contract_structure():
    data = AIEvaluationReport(
        summary="Piyasa temkinli pozitif",
        positive_factors=["Global görünüm olumlu"],
        risk_factors=["Faiz belirsizliği"],
        aligned_points=["Kurumlar uyumlu"],
        conflicting_points=["Riskler mevcut"],
        watch_items=["Fed açıklamaları"],
    ).to_dict()

    assert data["summary"] == "Piyasa temkinli pozitif"
    assert "Fed açıklamaları" in data["watch_items"]


def test_ai_output_has_no_trade_decision():
    data = AIEvaluationReport().to_dict()

    assert "signal" not in data
    assert "buy" not in data
    assert "sell" not in data
    assert "technical_score" not in data
