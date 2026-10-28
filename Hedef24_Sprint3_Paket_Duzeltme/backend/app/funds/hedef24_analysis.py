from __future__ import annotations

from math import isfinite
from typing import Any, Iterable


def technical_signal(nav_values: Iterable[Any]) -> dict[str, Any]:
    """Deterministic signal from dated NAV values in chronological order.

    Uses only supplied NAVs; no current data is fetched. Requires 21 observations.
    """
    values = []
    for item in nav_values:
        try:
            value = float(item)
        except (TypeError, ValueError):
            continue
        if isfinite(value) and value > 0:
            values.append(value)
    if len(values) < 21:
        return {
            "signal": "VERİ YETERSİZ", "reason": "Teknik sinyal için en az 21 geçerli NAV gözlemi gerekli.",
            "observations": len(values), "latest_nav": values[-1] if values else None,
            "momentum_20_pct": None, "sma_20": None, "rsi_14": None,
        }

    latest = values[-1]
    sma20 = sum(values[-20:]) / 20
    momentum = (latest / values[-21] - 1) * 100
    deltas = [values[i] - values[i-1] for i in range(len(values)-14, len(values))]
    gains = sum(max(x, 0.0) for x in deltas) / 14
    losses = sum(max(-x, 0.0) for x in deltas) / 14
    if losses == 0:
        rsi = 100.0 if gains > 0 else 50.0
    else:
        rsi = 100 - (100 / (1 + gains / losses))

    if latest < sma20 and momentum < 0:
        signal, reason = "SAT İNCELEMESİ", "NAV 20 gözlem ortalamasının altında ve 20 gözlem momentumu negatif."
    elif latest > sma20 and momentum > 0 and rsi < 70:
        signal, reason = "AL İNCELEMESİ", "NAV ortalamanın üzerinde ve momentum pozitif; risk/portföy uygunluğu ayrıca değerlendirilmeli."
    else:
        signal, reason = "TUT / İZLE", "Trend ve momentum koşulları birlikte net bir yön göstermiyor."
    if rsi >= 70 and signal == "AL İNCELEMESİ":
        signal, reason = "TUT / İZLE", "RSI yüksek; yeni alım sinyali teyit edilmedi."
    return {
        "signal": signal, "reason": reason, "observations": len(values),
        "latest_nav": latest, "momentum_20_pct": round(momentum, 2),
        "sma_20": round(sma20, 6), "rsi_14": round(rsi, 2),
    }
