from backend.app.market_context.ai_prompt_contract import AIPromptContract


def test_ai_prompt_contract_structure():
    data = AIPromptContract().to_dict()

    assert data["role"] == "Piyasa analisti destek asistanı"
    assert data["scope"] == "Market context analysis only"
    assert data["language"] == "Türkçe"


def test_ai_prompt_contract_declares_complete_output_shape():
    data = AIPromptContract().to_dict()

    assert data["output_fields"] == [
        "summary",
        "positive_factors",
        "risk_factors",
        "stock_specific_risks",
        "aligned_points",
        "conflicting_points",
        "watch_items",
    ]


def test_ai_prompt_contract_requires_safety_and_evidence_rules():
    data = AIPromptContract().to_dict()

    assert "uydurma" in data["evidence_policy"]
    assert "conflicting_points" in data["conflict_policy"]
    assert "teknik skor" in data["safety_policy"]


def test_ai_prompt_contract_separates_market_and_stock_risks():
    data = AIPromptContract().to_dict()
    assert "risk_factors" in data["risk_classification_policy"]
    assert "stock_specific_risks" in data["risk_classification_policy"]
