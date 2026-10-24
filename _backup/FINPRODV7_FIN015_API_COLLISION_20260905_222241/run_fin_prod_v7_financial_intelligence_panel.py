
from pathlib import Path
import argparse, json, sys

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default=r"D:\Projects\Hisse-Robotu")
    ap.add_argument("--symbol", default="TUPRS")
    ap.add_argument("--period-key", default="2026_2")
    a = ap.parse_args()

    root = Path(a.project_root)
    sys.path.insert(0, str(root / "backend"))

    from app.analysis.financial_intelligence_panel import save_financial_intelligence_panel

    out = save_financial_intelligence_panel(root, a.symbol, period_key=a.period_key)
    j = json.loads(out.read_text(encoding="utf-8-sig"))

    print("FIN_PROD_V7_FINANCIAL_INTELLIGENCE_PANEL")
    print("STATUS=" + str(j.get("status")))
    print("SYMBOL=" + str(j.get("symbol")))
    print("HEALTH_SCORE=" + str(j["sections"]["financial_health"]["score"]))
    print("BUSINESS_QUALITY=" + str(j["sections"]["long_term_context"]["business_quality"]))
    print("SHORT_TERM_STATUS=" + str(j["sections"]["short_term_context"]["status"]))
    print("LONG_TERM_STATUS=" + str(j["sections"]["long_term_context"]["status"]))
    print("COVERAGE_STATUS=" + str(j["sections"]["coverage_readiness"]["coverage_status"]))
    print("DECISION_SUPPORT_STATUS=" + str(j["sections"]["coverage_readiness"]["decision_support_status"]))
    print("MISSING_SOURCES=" + json.dumps(j["source_health"]["missing_sources"], ensure_ascii=False))
    print("RESULT=" + str(out))
    print("FIN_PROD_V7_FINANCIAL_INTELLIGENCE_PANEL=PASS")

if __name__ == "__main__":
    main()
