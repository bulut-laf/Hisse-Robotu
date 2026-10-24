from backend.app.system.performance_validation import (
    validate_performance_metrics,
)


def test_performance_validation():
    result = validate_performance_metrics(
        {
            "analysis_time": 1.2,
            "report_time": 0.8,
            "data_processing": True,
        }
    )

    assert result["ready"] is True


def test_performance_validation_missing():
    result = validate_performance_metrics({})

    assert result["ready"] is False
