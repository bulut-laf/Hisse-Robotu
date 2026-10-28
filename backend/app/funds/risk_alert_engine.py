from __future__ import annotations

def check_portfolio_alerts(max_drawdown_pct: float, max_liquidation_days: float, dd_threshold: float = -15.0, liq_threshold: float = 5.0) -> list[dict]:
    """
    Portföy metriklerini belirlenen eşiklerle karşılaştırıp alarm (uyarı) listesi döndürür.
    """
    alerts = []
    
    # Drawdown Kontrolü
    if max_drawdown_pct < dd_threshold:
        alerts.append({
            "level": "CRITICAL",
            "title": "Yüksek Maksimum Düşüş (Drawdown) Riski",
            "message": f"Portföyün maksimum düşüş oranı ({max_drawdown_pct}%) belirlenen {dd_threshold}% sınırını aştı. Sermaye koruması risk altında."
        })
        
    # Likidasyon (Stres) Kontrolü
    if max_liquidation_days > liq_threshold:
        alerts.append({
            "level": "WARNING",
            "title": "Likidite / Satış Baskısı Riski",
            "message": f"Stres durumunda portföyün nakde dönme süresi ({max_liquidation_days} gün) belirlenen {liq_threshold} günlük güvenli limiti aşıyor. Hızlı çıkış zor olabilir."
        })
        
    return alerts