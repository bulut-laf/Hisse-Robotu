import pytest
import pandas as pd
from backend.app.funds.backtest_simulator import calculate_max_drawdown, simulate_portfolio

def test_calculate_max_drawdown():
    # Zirveden dibe %50 düşüş senaryosu (100 -> 50)
    equity = pd.Series([100.0, 120.0, 60.0, 80.0])
    dd = calculate_max_drawdown(equity)
    assert dd == -0.50

def test_simulate_portfolio():
    # 2 fon, 3 günlük basit getiri verisi (örnek)
    data = {
        "MAC": [0.01, -0.02, 0.05],
        "IIH": [0.03, -0.01, 0.02]
    }
    df = pd.DataFrame(data, index=["2026-10-26", "2026-10-27", "2026-10-28"])
    
    result = simulate_portfolio(df, initial_capital=100000.0)
    
    assert "final_capital" in result
    assert result["total_return_pct"] > 0
    assert result["max_drawdown_pct"] < 0