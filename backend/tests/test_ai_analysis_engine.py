from backend.app.market_context.ai_analysis_engine import (
    prepare_ai_analysis_request,
)


def test_ai_analysis_request_preparation():
    data = prepare_ai_analysis_request(
        {
            "market_context": ["BIST pozitif"],
            "risks": ["Fed"],
        }
    )

    assert data["ready"] is True
    assert "market_context" in data["context"]


def test_ai_engine_has_no_trade_logic():
    data = prepare_ai_analysis_request({})

    assert "signal" not in data
    assert "buy" not in data
    assert "technical_score" not in data
