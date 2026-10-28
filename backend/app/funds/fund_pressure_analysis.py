from __future__ import annotations
import math

def calculate_liquidation_stress_metrics(holding_weight: float, fdo_ratio: float, daily_volume: float) -> dict:
    if daily_volume <= 0 or fdo_ratio <= 0:
        return {"normal": 0.0, "aggressive": 0.0, "stress": 0.0}
    
    effective_capacity = daily_volume * fdo_ratio
    
    normal_days = (holding_weight * 100) / max(effective_capacity * 0.1, 0.001)
    aggressive_days = normal_days * 0.5
    stress_days = normal_days * 2.5
    
    return {
        "normal": round(normal_days, 4),
        "aggressive": round(aggressive_days, 4),
        "stress": round(stress_days, 4)
    }