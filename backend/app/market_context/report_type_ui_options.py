from __future__ import annotations

REPORT_TYPE_LABELS = {
    "market_commentary": "Piyasa Bülteni",
    "kap_news": "KAP / Haber",
    "daily_recommendation": "Günlük AL-SAT Önerisi",
    "weekly_recommendation": "Haftalık AL-SAT Önerisi",
    "model_portfolio": "Model Portföy",
    "target_price_report": "Hedef Fiyat Raporu",
    "sector_view": "Sektör Görüşü",
}


def get_report_type_options() -> list[str]:
    return list(REPORT_TYPE_LABELS.keys())
