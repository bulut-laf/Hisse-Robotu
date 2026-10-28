import pytest
from backend.app.funds.risk_alert_engine import check_portfolio_alerts

def test_check_portfolio_alerts_trigger():
    # Kötü senaryo: -20% drawdown ve 7 günlük tasfiye
    alerts = check_portfolio_alerts(max_drawdown_pct=-20.0, max_liquidation_days=7.0)
    assert len(alerts) == 2
    assert any(a["level"] == "CRITICAL" for a in alerts)
    assert any(a["level"] == "WARNING" for a in alerts)

def test_check_portfolio_alerts_safe():
    # Güvenli senaryo: Sınırların içinde
    alerts = check_portfolio_alerts(max_drawdown_pct=-10.0, max_liquidation_days=2.0)
    assert len(alerts) == 0