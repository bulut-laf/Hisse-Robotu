import pandas as pd
from backend.app.funds.fund_pressure_analysis import calculate_liquidation_stress_metrics

def build_pressure_dataframe(portfolio_holdings: list[dict]) -> pd.DataFrame:
    "`"`"
    KAP'tan çekilen hisse verilerini alır, FDO/Baskı Riski metriklerini hesaplar 
    ve Streamlit arayüzü için hazır bir Pandas DataFrame'e dönüştürür.
    "`"`"
    table_rows = []
    
    for holding in portfolio_holdings:
        # Arka plan motorumuzu çağırıyoruz
        metrics = calculate_liquidation_stress_metrics(
            holding_weight=holding.get("weight", 0.0),
            fdo_ratio=holding.get("fdo_ratio", 0.0),
            daily_volume=holding.get("daily_volume", 0.0)
        )
        
        # Arayüzdeki kolon formatıyla eşleştiriyoruz
        table_rows.append({
            "Hisse": holding.get("ticker", "BLNMYOR"),
            "Fon/FDO %": round(holding.get("weight", 0.0), 4),
            "Likidasyon Normal (gün)": metrics["normal"],
            "Likidasyon Agresif (gün)": metrics["aggressive"],
            "Likidasyon Stres (gün)": metrics["stress"]
        })
        
    df = pd.DataFrame(table_rows)
    return df