
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal

AS_OF = datetime(2026,8,4,23,59,59)
TARGET_END = date(2026,6,30)
TARGET_START = date(2026,1,1)

def loadj(p: Path):
    return json.loads(p.read_text(encoding="utf-8-sig"))

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
    out=fi/"TUPRS_business_quality_canonical_adapter_rev4.json"

    report=import_kap_financial_xls_bytes(xls.read_bytes(),source_name=xls.name)
    series=build_historical_financial_series((report,))
    pit=series.available_as_of(AS_OF)

    if report.identity.symbol!="TUPRS":
        raise SystemExit("SYMBOL_MISMATCH")

    def points(code):
        return [p for p in pit.points if p.metric_code==code and p.period_end==TARGET_END]

    def ytd(code):
        c=[p for p in points(code)
           if p.period_kind=="DURATION"
           and p.period_start==TARGET_START
           and p.comparison_role=="CURRENT_YTD"]
        return c[-1] if c else None

    def instant(code):
        c=[p for p in points(code)
           if p.period_kind!="DURATION" or p.period_start is None]
        if not c:
            c=points(code)
        # Prefer current-role point if roles exist.
        cur=[p for p in c if p.comparison_role in ("CURRENT","CURRENT_PERIOD","CURRENT_YTD","CURRENT_QUARTER")]
        return (cur or c)[-1] if (cur or c) else None

    ev={}
    vals={}

    def put(field,p):
        if p is None: return
        vals[field]=p.value
        ev[field]={
            "metric_code":p.metric_code,
            "value":str(p.value),
            "period_kind":p.period_kind,
            "period_start":None if p.period_start is None else p.period_start.isoformat(),
            "period_end":p.period_end.isoformat(),
            "comparison_role":p.comparison_role,
            "published_at":None if p.published_at is None else p.published_at.isoformat(),
            "source_sha256":p.source_sha256,
        }

    # Duration statement fields must use the same CURRENT_YTD leg.
    for field, codes in {
        "revenue":["REVENUE"],
        "gross_profit":["GROSS_PROFIT"],
        "operating_profit":["OPERATING_PROFIT"],
        "net_income":["NET_INCOME"],
        "operating_cash_flow":["OPERATING_CASH_FLOW","CASH_FROM_OPERATIONS"],
        "capital_expenditure":["CAPEX"],
    }.items():
        for code in codes:
            p=ytd(code)
            if p is not None:
                put(field,p); break

    # Balance sheet fields are period-end snapshots.
    for field,codes in {
        "total_assets":["TOTAL_ASSETS"],
        "total_equity":["TOTAL_EQUITY","PARENT_EQUITY"],
        "cash_and_equivalents":["CASH_EQUIVALENTS"],
        "current_assets":["CURRENT_ASSETS"],
        "current_liabilities":["CURRENT_LIABILITIES"],
    }.items():
        for code in codes:
            p=instant(code)
            if p is not None:
                put(field,p); break

    # Reuse accepted total financial debt.
    acc=loadj(acceptance)
    for m in (acc.get("financial_health") or {}).get("metrics") or []:
        if str(m.get("code") or "").upper()=="FINANCIAL_DEBT" and m.get("value") is not None:
            vals["total_debt"]=Decimal(str(m["value"]))
            ev["total_debt"]={
                "source":str(acceptance),
                "metric_code":"FINANCIAL_DEBT",
                "value":str(vals["total_debt"]),
                "source_period_end":m.get("source_period_end"),
                "semantic_guard":"existing accepted FINANCIAL_DEBT reused"
            }
            break

    # Exact same-leg single-period EBITDA.
    op=ytd("OPERATING_PROFIT")
    da=ytd("DEPRECIATION_AMORTIZATION")
    if op is not None and da is not None:
        vals["ebitda"]=op.value + abs(da.value)
        ev["ebitda"]={
            "value":str(vals["ebitda"]),
            "derivation":"OPERATING_PROFIT + abs(DEPRECIATION_AMORTIZATION)",
            "period_start":TARGET_START.isoformat(),
            "period_end":TARGET_END.isoformat(),
            "comparison_role":"CURRENT_YTD",
            "components":{
                "OPERATING_PROFIT":str(op.value),
                "DEPRECIATION_AMORTIZATION":str(da.value),
            },
            "same_period_verified":True,
            "point_in_time_verified":True,
            "ttm_synthesis":False,
        }

    # Exact FIN-006 legal share piece count.
    if ownership.exists():
        oj=loadj(ownership)
        inp=oj.get("input_convention") or {}
        legal=inp.get("legal_share_piece_count")
        if legal is not None and Decimal(str(legal))>0:
            vals["shares_outstanding"]=Decimal(str(legal))
            ev["shares_outstanding"]={
                "source":str(ownership),
                "field":"input_convention.legal_share_piece_count",
                "value":str(vals["shares_outstanding"]),
                "issued_capital_try":inp.get("issued_capital_try"),
                "legal_share_nominal_try":inp.get("legal_share_nominal_try"),
            }

    req=[
        "revenue","gross_profit","operating_profit","ebitda","net_income",
        "total_assets","total_equity","total_debt","cash_and_equivalents",
        "current_assets","current_liabilities","operating_cash_flow",
        "capital_expenditure","shares_outstanding"
    ]
    missing=[x for x in req if x not in vals]

    payload={
        "status":"BLOCKED",
        "mode":"READ_ONLY_CANONICAL_BUSINESS_QUALITY_ADAPTER_V6_REV4",
        "symbol":"TUPRS","as_of_date":"2026-08-04",
        "period_selection":{
            "duration_leg":"CURRENT_YTD",
            "duration_start":"2026-01-01",
            "period_end":"2026-06-30",
            "balance_sheet":"PERIOD_END_SNAPSHOT",
        },
        "resolved_inputs":ev,
        "missing_requirements":missing,
        "business_quality":None,
        "blockers":[],
    }

    if missing:
        payload["blockers"]=["BUSINESS_QUALITY_CANONICAL_INPUTS_INCOMPLETE"]
        out.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
        print("STATUS=BLOCKED")
        print("MISSING="+json.dumps(missing,ensure_ascii=False))
        print("RESULT="+str(out))
        print("FIN_PROD_V6_BUSINESS_QUALITY_ADAPTER_REV4=PASS_FAIL_CLOSED")
        return

    pub=report.identity.published_at.date() if report.identity.published_at else None
    period=FinancialPeriod(
        symbol="TUPRS",period_end=TARGET_END,fiscal_year=2026,fiscal_quarter=2,
        currency=pit.currency,
        revenue=vals["revenue"],gross_profit=vals["gross_profit"],
        operating_profit=vals["operating_profit"],ebitda=vals["ebitda"],
        net_income=vals["net_income"],total_assets=vals["total_assets"],
        total_equity=vals["total_equity"],total_debt=vals["total_debt"],
        cash_and_equivalents=vals["cash_and_equivalents"],
        current_assets=vals["current_assets"],current_liabilities=vals["current_liabilities"],
        operating_cash_flow=vals["operating_cash_flow"],
        capital_expenditure=vals["capital_expenditure"],
        shares_outstanding=vals["shares_outstanding"],
        source="FIN001_FIN002_CURRENT_YTD_PLUS_FIN006",
        published_at=pub,
    )

    freshness=evaluate_fundamental_freshness([period],today=date(2026,8,4))
    snapshot=build_fundamental_snapshot([period],source_metadata={
        "adapter":"FIN-PROD-V6-REV4","as_of":"2026-08-04",
        "period_selection":"CURRENT_YTD_2026H1",
        "kap_source_sha256":report.source_sha256,
    })
    quality=calculate_fundamental_quality(snapshot,freshness)

    score=getattr(quality,"total_score",None)
    locked=getattr(quality,"locked",True)
    payload["fundamental_quality"]={
        "total_score":score,
        "locked":locked,
        "grade":getattr(quality,"grade",None),
        "period_key":getattr(quality,"period_key",None),
        "explanation":getattr(quality,"explanation",None),
    }

    if locked or score is None:
        payload["blockers"]=["EXISTING_FUNDAMENTAL_QUALITY_ENGINE_LOCKED"]
        out.write_text(json.dumps(payload,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
        print("STATUS=BLOCKED")
        print("EBITDA="+str(vals["ebitda"]))
        print("FUNDAMENTAL_QUALITY_LOCKED=True")
        print("RESULT="+str(out))
        print("FIN_PROD_V6_BUSINESS_QUALITY_ADAPTER_REV4=PASS_FAIL_CLOSED")
        return

    payload["status"]="PASS"
    payload["business_quality"]=str(score)
    payload["blockers"]=[]
    out.write_text(json.dumps(payload,ensure_ascii=False,indent=2,default=str),encoding="utf-8")

    print("STATUS=PASS")
    print("REVENUE_YTD="+str(vals["revenue"]))
    print("OPERATING_PROFIT_YTD="+str(vals["operating_profit"]))
    print("EBITDA="+str(vals["ebitda"]))
    print("SHARES_OUTSTANDING="+str(vals["shares_outstanding"]))
    print("BUSINESS_QUALITY="+str(score))
    print("FUNDAMENTAL_QUALITY_LOCKED=False")
    print("RESULT="+str(out))
    print("FIN_PROD_V6_BUSINESS_QUALITY_ADAPTER_REV4=PASS")

if __name__=="__main__":
    main()
