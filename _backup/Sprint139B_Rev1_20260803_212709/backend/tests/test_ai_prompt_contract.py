from backend.app.market_context.ai_prompt_contract import (
    AIPromptContract,
)


def test_ai_prompt_contract_structure():
    data = AIPromptContract().to_dict()

    assert data["role"] == "Piyasa analisti destek asistanı"
    assert data["scope"] == "Market context analysis only"


def test_ai_prompt_contract_has_no_trade_instruction():
    data = AIPromptContract().to_dict()

    assert "buy" not in data
    assert "sell" not in data
    assert "technical_score" not in data
