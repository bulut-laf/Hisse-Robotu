from __future__ import annotations
import pandas as pd

def generate_rotation_plan(current_portfolio: dict[str, float], target_funds: list[str], total_capital: float) -> pd.DataFrame:
    plan = []
    
    target_weight = 1.0 / len(target_funds) if target_funds else 0.0
    target_amount_per_fund = total_capital * target_weight

    all_funds = set(current_portfolio.keys()).union(set(target_funds))
    
    for fund in all_funds:
        current_amount = current_portfolio.get(fund, 0.0)
        target_amount = target_amount_per_fund if fund in target_funds else 0.0
        
        diff = target_amount - current_amount
        
        if abs(diff) < 1.0:
            action = "HOLD"
            action_tr = "TUT"
        elif diff > 0:
            action = "BUY"
            action_tr = "AL"
        else:
            action = "SELL"
            action_tr = "SAT"
            
        plan.append({
            "Fon Kodu": fund,
            "Mevcut Bakiye ()": round(current_amount, 2),
            "Hedef Bakiye ()": round(target_amount, 2),
            "Fark ()": round(diff, 2),
            "Aksiyon": action_tr
        })
        
    df = pd.DataFrame(plan)
    if not df.empty:
        df["sort_order"] = df["Aksiyon"].map({"SAT": 1, "AL": 2, "TUT": 3})
        df = df.sort_values("sort_order").drop(columns=["sort_order"]).reset_index(drop=True)
        
    return df