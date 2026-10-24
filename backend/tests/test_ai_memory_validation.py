from backend.app.market_context.ai_memory_validation import (
    validate_ai_memory_chain,
)


def test_ai_memory_chain_validation():
    result = validate_ai_memory_chain(
        {
            "summary": "Temkinli pozitif",
        },
        {
            "risk_changes": {},
            "positive_changes": {},
        },
        {
            "count": 3,
        },
        [
            {
                "summary": "Temkinli pozitif",
            }
        ],
    )

    assert result is True


def test_ai_memory_validation_has_no_trade_logic():
    result = validate_ai_memory_chain(
        {"summary": "Test"},
        {"risk_changes": {}, "positive_changes": {}},
        {"count": 0},
        [],
    )

    assert result is True
