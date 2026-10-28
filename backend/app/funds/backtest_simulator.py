from __future__ import annotations
import pandas as pd
import numpy as np

def calculate_max_drawdown(equity_curve: pd.Series) -> float:
    if equity_curve.empty:
        return 0.0
    rolling_max = equity_curve.cummax()
    drawdown = (equity_curve - rolling_max) / rolling_max
    return float(drawdown.min())

def simulate_portfolio(fund_returns: pd.DataFrame, initial_capital: float = 100000.0) -> dict:
    if fund_returns.empty:
        return {}

    num_funds = len(fund_returns.columns)
    weights = np.array([1.0 / num_funds] * num_funds)
    
    portfolio_daily_return = fund_returns.dot(weights)
    cumulative_returns = (1 + portfolio_daily_return).cumprod()
    equity_curve = initial_capital * cumulative_returns
    
    total_return_pct = (cumulative_returns.iloc[-1] - 1.0) * 100
    max_dd_pct = calculate_max_drawdown(equity_curve) * 100
    
    return {
        "initial_capital": initial_capital,
        "final_capital": round(float(equity_curve.iloc[-1]), 2),
        "total_return_pct": round(float(total_return_pct), 2),
        "max_drawdown_pct": round(float(max_dd_pct), 2),
        "equity_curve": equity_curve.to_dict()
    }