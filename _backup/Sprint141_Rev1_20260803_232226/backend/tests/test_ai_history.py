from backend.app.market_context.ai_history import (
    AIEvaluationHistory,
    load_ai_evaluation_history,
)


def test_ai_history_stores_multiple_days():
    history = AIEvaluationHistory()

    history.add(
        {
            "date": "2026-08-03",
            "summary": "Temkinli pozitif",
        }
    )

    history.add(
        {
            "date": "2026-08-04",
            "summary": "Pozitif",
        }
    )

    data = history.to_dict()

    assert data["evaluation_count"] == 2
    assert data["evaluations"][1]["summary"] == "Pozitif"


def test_ai_history_has_no_trade_logic():
    data = AIEvaluationHistory().to_dict()

    assert "signal" not in data
    assert "technical_score" not in data


def test_load_ai_history_keeps_latest_record_per_day(tmp_path):
    root = tmp_path / "market_context_ai_evaluations" / "2026-08-03"
    root.mkdir(parents=True)

    old = {
        "date": "2026-08-03",
        "created_at": "2026-08-03T10:00:00Z",
        "output": {"summary": "Eski"},
    }
    new = {
        "date": "2026-08-03",
        "created_at": "2026-08-03T20:00:00Z",
        "output": {"summary": "Yeni"},
    }

    import json

    (root / "old.json").write_text(json.dumps(old), encoding="utf-8")
    (root / "new.json").write_text(json.dumps(new), encoding="utf-8")

    data = load_ai_evaluation_history(tmp_path)

    assert len(data) == 1
    assert data[0]["output"]["summary"] == "Yeni"
