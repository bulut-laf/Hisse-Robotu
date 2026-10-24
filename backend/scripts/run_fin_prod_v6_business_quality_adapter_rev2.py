
from __future__ import annotations
import argparse, json, sys, inspect
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal

def D(v):
    return None if v is None else Decimal(str(v))

def loadj(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))

def metric_value(obj, code):
    for section in ("financial_health","earnings_cash_quality","financial_risk"):
        s=obj.get(section) or {}
        for m in s.get("metrics") or []:
            if str(m.get("code") or "").upper()==code.upper() and m.get("value") is not None:
                return Decimal(str(m["value"])), {
                    "source_section": section,
                    "metric_code": code,
                    "value": str(m["value"]),
                    "source_period_end": m.get("source_period_end") or m.get("current_period_end"),
                }
    return None, None

def deep_find_total_shares(obj):
    candidates=[]
    def walk(o,path="$"):
        if isinstance(o,dict):
            for k,v in o.items():
                p=f"{path}.{k}"
                if str(k).lower() in {"total_shares","shares_outstanding","issued_shares"} and v is not None:
                    try:
                        candidates.append((p,Decimal(str(v))))
                    except Exception:
                        pass
                walk(v,p)
        elif isinstance(o,list):
            for i,v in enumerate(o):
                walk(v,f"{path}[{i}]")
    walk(obj)
    return candidates

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",required=True)
    ap.add_argument("--kap-xls",required=True)
    a=ap.parse_args()

    root=Path(a.project_root)
    backend=root/"backend"
    sys.path.insert(0,str(backend))

    from app.data.kap_financial_xls import import_kap_financial_xls_bytes
    from app.data.historical_financial_series import build_historical_financial_series
    from app.models.fundamental_models import FinancialPeriod
    from app.analysis.fundamental_analysis import build_fundamental_snapshot
    from app.analysis.fundamental_quality import calculate_fundamental_quality
    from app.data.fundamental_data import evaluate_fundamental_freshness

    xls=Path(a.kap_xls)
    fi=backend/"data"/"financial_intelligence"
    acceptance=backend/"data"/"financial_intelligence_acceptance_TUPRS_2026_2.json"
    ownership=fi/"TUPRS_market_ownership_acceptance.json"
    out=fi/"TUPRS_business_quality_canonical_adapter_rev2.json"

    report=import_kap_financial_xls_bytes(xls.read_bytes(),source_name=xls.name)
    series=build_historical_financial_series((report,))
    as_of=datetime(2026,8,4,23,59,59)
    pit=series.available_as_of(as_of)

    def latest(code):
        return pit.latest_value(code,as_of=as_of)

    mapcodes={
        "revenue":["REVENUE"],
        "gross_profit":["GROSS_PROFIT"],
        "operating_profit":["OPERATING_PROFIT"],
        "net_income":["NET_INCOME"],
        "total_assets":["TOTAL_ASSETS"],
        "total_equity":["TOTAL_EQUITY","PARENT_EQUITY"],
        "cash_and_equivalents":["CASH_EQUIVALENTS"],
        "current_assets":["CURRENT_ASSETS"],
        "current_liabilities":["CURRENT_LIABILITIES"],
        "operating_cash_flow":["OPERATING_CASH_FLOW","CASH_FROM_OPERATIONS"],
        "capital_expenditure":["CAPEX","CAPITAL_EXPENDITURE"],
    }

    vals={}
    ev={}
    for field,codes in mapcodes.items():
        for c in codes:
            p=latest(c)
            if p is not None:
                vals[field]=p.value
                ev[field]={"metric_code":c,"value":str(p.value),"period_end":p.period_end.isoformat(),
                           "published_at":None if p.published_at is None else p.published_at.isoformat()}
                break

    # Existing accepted Financial Health derivation: do not recompute here.
    acc=loadj(acceptance)
    total_debt, debt_ev = metric_value(acc,"FINANCIAL_DEBT")
    if total_debt is not None:
        vals["total_debt"]=total_debt
        ev["total_debt"]={
            **debt_ev,
            "source":str(acceptance),
            "semantic_guard":"existing FINANCIAL_DEBT output reused; no new debt formula",
        }

    # EBITDA: accept only an exact canonical EBITDA point OR an already-existing EBITDA metric.
    p=latest("EBITDA")
    if p is not None:
        vals["ebitda"]=p.value
        ev["ebitda"]={"metric_code":"EBITDA","value":str(p.value),"period_end":p.period_end.isoformat(),
                      "source":"FIN002_CANONICAL_POINT"}
    else:
        ebitda_val, ebitda_ev = metric_value(acc,"EBITDA")
        if ebitda_val is not None:
            vals["ebitda"]=ebitda_val
            ev["ebitda"]={**ebitda_ev,"source":str(acceptance),"semantic_guard":"existing EBITDA metric only"}

    # Shares: exact ownership acceptance only.
    shares=None
    shares_ev=None
    if ownership.exists():
        oj=loadj(ownership)
        cands=deep_find_total_shares(oj)
        if cands:
            path,val=cands[0]
            shares=val
            shares_ev={"source":str(ownership),"field":path,"value":str(val)}
            vals["shares_outstanding"]=val
            ev["shares_outstanding"]=shares_ev

    required=[
        "revenue","gross_profit","operating_profit","ebitda","net_income",
        "total_assets","total_equity","total_debt","cash_and_equivalents",
        "current_assets","current_liabilities","operating_cash_flow",
        "capital_expenditure","shares_outstanding"
    ]
    missing=[k for k in required if k not in vals]

    payload={
        "status":"BLOCKED",
        "mode":"READ_ONLY_CANONICAL_BUSINESS_QUALITY_ADAPTER_V6_REV2",
        "symbol":"TUPRS","as_of_date":"2026-08-04",
        "resolved_inputs":ev,
        "missing_requirements":missing,
        "business_quality":None,
        "blockers":[],
        "rules":[
            "No missing value is converted to zero.",
            "No EBITDA formula is introduced.",
            "Debt reuses existing accepted FINANCIAL_DEBT output only.",
            "Shares reuse existing ownership acceptance only.",
            "Existing calculate_fundamental_quality remains the only quality scoring engine."
        ]
    }

    if missing:
        payload["blockers"]=["BUSINESS_QUALITY_CANONICAL_INPUTS_INCOMPLETE"]
        out.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
        print("STATUS=BLOCKED")
        print("MISSING="+json.dumps(missing,ensure_ascii=False))
        print("RESULT="+str(out))
        print("FIN_PROD_V6_BUSINESS_QUALITY_ADAPTER_REV2=PASS_FAIL_CLOSED")
        return

    ends={x.get("period_end") for k,x in ev.items() if x.get("period_end")}
    # Derived debt/shares can be as-of evidence without period_end; raw statement fields must align.
    raw_ends={ev[k]["period_end"] for k in mapcodes if k in ev and ev[k].get("period_end")}
    if len(raw_ends)!=1:
        payload["blockers"]=["MIXED_PERIOD_RAW_CANONICAL_INPUTS"]
        out.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
        print("STATUS=BLOCKED")
        print("MISSING=[\"MIXED_PERIOD_RAW_CANONICAL_INPUTS\"]")
        print("RESULT="+str(out))
        print("FIN_PROD_V6_BUSINESS_QUALITY_ADAPTER_REV2=PASS_FAIL_CLOSED")
        return

    period_end=date.fromisoformat(next(iter(raw_ends)))
    q={3:1,6:2,9:3,12:4}[period_end.month]
    pub=report.identity.published_at.date() if report.identity.published_at else None

    period=FinancialPeriod(
        symbol="TUPRS", period_end=period_end, fiscal_year=period_end.year, fiscal_quarter=q,
        currency=pit.currency,
        revenue=vals["revenue"], gross_profit=vals["gross_profit"],
        operating_profit=vals["operating_profit"], ebitda=vals["ebitda"],
        net_income=vals["net_income"], total_assets=vals["total_assets"],
        total_equity=vals["total_equity"], total_debt=vals["total_debt"],
        cash_and_equivalents=vals["cash_and_equivalents"],
        current_assets=vals["current_assets"], current_liabilities=vals["current_liabilities"],
        operating_cash_flow=vals["operating_cash_flow"], capital_expenditure=vals["capital_expenditure"],
        shares_outstanding=vals["shares_outstanding"],
        source="FIN001_FIN002_PLUS_EXISTING_ACCEPTED_DERIVATIONS",
        published_at=pub
    )

    freshness=evaluate_fundamental_freshness([period],today=date(2026,8,4))
    snapshot=build_fundamental_snapshot([period],source_metadata={
        "adapter":"FIN-PROD-V6-REV2","as_of":"2026-08-04","kap_source_sha256":report.source_sha256
    })
    quality=calculate_fundamental_quality(snapshot,freshness)

    score=getattr(quality,"total_score",None)
    locked=getattr(quality,"locked",True)
    payload["fundamental_quality"]={
        "total_score":score,"locked":locked,
        "grade":getattr(quality,"grade",None),
        "period_key":getattr(quality,"period_key",None),
        "explanation":getattr(quality,"explanation",None),
    }

    if locked or score is None:
        payload["blockers"]=["EXISTING_FUNDAMENTAL_QUALITY_ENGINE_LOCKED"]
        out.write_text(json.dumps(payload,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
        print("STATUS=BLOCKED")
        print("FUNDAMENTAL_QUALITY_LOCKED=True")
        print("RESULT="+str(out))
        print("FIN_PROD_V6_BUSINESS_QUALITY_ADAPTER_REV2=PASS_FAIL_CLOSED")
        return

    payload["status"]="PASS"
    payload["business_quality"]=str(score)
    payload["blockers"]=[]
    out.write_text(json.dumps(payload,ensure_ascii=False,indent=2,default=str),encoding="utf-8")

    print("STATUS=PASS")
    print("BUSINESS_QUALITY="+str(score))
    print("FUNDAMENTAL_QUALITY_LOCKED=False")
    print("RESULT="+str(out))
    print("FIN_PROD_V6_BUSINESS_QUALITY_ADAPTER_REV2=PASS")

if __name__=="__main__":
    main()
