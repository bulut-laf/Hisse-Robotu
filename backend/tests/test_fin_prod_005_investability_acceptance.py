from app.analysis.financial_intelligence_investability_acceptance import run_investability_acceptance

class R:
    locked=True
    score=None
    label="LOCKED"
    strengths=()
    risks=()
    confidence="LOW"

def test_read_only_and_missing_context(monkeypatch):
    seen={}
    def s(*a,**k):
        seen["m"]=k["market"]; return R()
    monkeypatch.setattr("app.analysis.financial_intelligence_investability_acceptance.calculate_short_term_investability",s)
    monkeypatch.setattr("app.analysis.financial_intelligence_investability_acceptance.calculate_long_term_investability",lambda *a,**k:R())
    monkeypatch.setattr("app.analysis.financial_intelligence_investability_acceptance.build_financial_intelligence_panel",lambda **k:{"read_only":True})
    r=run_investability_acceptance({"symbol":"TUPRS","as_of_date":"2026-08-04","short_term":{"market":{}},"long_term":{}})
    assert r["status"]=="PASS"
    assert seen["m"].technical_trend is None
    assert r["panel"]["read_only"] is True
