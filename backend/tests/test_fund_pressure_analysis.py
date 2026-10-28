import pytest
from backend.app.funds.fund_pressure_analysis import calculate_liquidation_stress_metrics

def test_calculate_liquidation_stress_metrics_normal_case():
    result = calculate_liquidation_stress_metrics(holding_weight=5.0, fdo_ratio=0.30, daily_volume=1000000)
    assert result["normal"] > 0
    assert result["stress"] > result["normal"]
    assert result["aggressive"] < result["normal"]

def test_calculate_liquidation_stress_metrics_zero_volume():
    result = calculate_liquidation_stress_metrics(holding_weight=2.0, fdo_ratio=0.50, daily_volume=0)
    assert result["normal"] == 0.0
    assert result["stress"] == 0.0