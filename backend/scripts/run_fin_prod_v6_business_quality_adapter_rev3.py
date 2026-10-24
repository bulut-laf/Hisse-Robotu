
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal

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
    out=fi/"TUPRS_business_quality_canonical_adapter_rev3.json"

    report=import_kap_financial_xls_bytes(xls.read_bytes(),source_name=xls.name)
    series=build_historical_financial_series((report,))
    as_of=datetime(2026,8,4,23,59,59)
    pit=series.available_as_of(as_of)

    if report.identity.symbol != "TUPRS":
        raise SystemExit("SYMBOL_MISMATCH")

    def latest(code):
        return pit.latest_value(code,as_of=as_of)

    exact_map={
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
        "capital_expenditure":["CAPEX"],
    }

    vals={}
    ev={}

    for field,codes in exact_map.items():
        for code in codes:
            p=latest(code)
            if p is not None:
                vals[field]=p.value
                ev[field]={
                    "metric_code":code,
                    "value":str(p.value),
                    "period_start":None if p.period_start is None else p.period_start.isoformat(),
                    "period_end":p.period_end.isoformat(),
                    "published_at":None if p.published_at is None else p.published_at.isoformat(),
                    "source_sha256":p.source_sha256,
                }
                break

    # Existing accepted debt output; no new debt formula.
    acc=loadj(acceptance)
    debt=None
    for m in (acc.get("financial_health") or {}).get("metrics") or []:
        if str(m.get("code") or "").upper()=="FINANCIAL_DEBT" and m.get("value") is not None:
            debt=Decimal(str(m["value"]))
            vals["total_debt"]=debt
            ev["total_debt"]={
                "source":str(acceptance),
                "metric_code":"FINANCIAL_DEBT",
                "value":str(debt),
                "source_period_end":m.get("source_period_end"),
                "semantic_guard":"existing accepted FINANCIAL_DEBT reused; no new debt formula",
            }
            break

    # Exact canonical single-period EBITDA derivation:
    # OPERATING_PROFIT and DEPRECIATION_AMORTIZATION must be same period and same PIT source chain.
    op=latest("OPERATING_PROFIT")
    da=latest("DEPRECIATION_AMORTIZATION")
    if op is not None and da is not None:
        same_period=(op.period_start==da.period_start and op.period_end==da.period_end)
        pit_ok=((op.published_at is None or op.published_at<=as_of) and
                (da.published_at is None or da.published_at<=as_of))
        if same_period and pit_ok:
            ebitda=op.value + abs(da.value)
            vals["ebitda"]=ebitda
            ev["ebitda"]={
                "value":str(ebitda),
                "derivation":"OPERATING_PROFIT + abs(DEPRECIATION_AMORTIZATION)",
                "period_start":None if op.period_start is None else op.period_start.isoformat(),
                "period_end":op.period_end.isoformat(),
                "published_at":None if op.published_at is None else op.published_at.isoformat(),
                "components":{
                    "OPERATING_PROFIT":str(op.value),
                    "DEPRECIATION_AMORTIZATION":str(da.value),
                },
                "same_period_verified":True,
                "point_in_time_verified":True,
                "ttm_synthesis":False,
                "semantic_guard":"single-period canonical derivation only; no TTM EBITDA synthesis",
            }

    # Exact legal share piece count from FIN-006 ownership acceptance.
    if ownership.exists():
        oj=loadj(ownership)
        inp=oj.get("input_convention") or {}
        legal_count=inp.get("legal_share_piece_count")
        issued_capital=inp.get("issued_capital_try")
        nominal=inp.get("legal_share_nominal_try")
        if legal_count is not None:
            shares=Decimal(str(legal_count))
            if shares>0:
                vals["shares_outstanding"]=shares
                ev["shares_outstanding"]={
                    "source":str(ownership),
                    "field":"input_convention.legal_share_piece_count",
                    "value":str(shares),
                    "issued_capital_try":issued_capital,
                    "legal_share_nominal_try":nominal,
                    "semantic_guard":"exact legal share piece count from existing FIN-006 acceptance",
                }

    required=[
        "revenue","gross_profit","operating_profit","ebitda","net_income",
        "total_assets","total_equity","total_debt","cash_and_equivalents",
        "current_assets","current_liabilities","operating_cash_flow",
        "capital_expenditure","shares_outstanding"
    ]
    missing=[k for k in required if k not in vals]

    payload={
        "status":"BLOCKED",
        "mode":"READ_ONLY_CANONICAL_BUSINESS_QUALITY_ADAPTER_V6_REV3",
        "symbol":"TUPRS",
        "as_of_date":"2026-08-04",
        "resolved_inputs":ev,
        "missing_requirements":missing,
        "business_quality":None,
        "blockers":[],
        "rules":[
            "No missing value is converted to zero.",
            "No TTM EBITDA is synthesized.",
            "Single-period EBITDA is derived only when OPERATING_PROFIT and DEPRECIATION_AMORTIZATION are exact canonical same-period PIT points.",
            "Shares use existing FIN-006 legal_share_piece_count.",
            "Existing calculate_fundamental_quality remains the only quality scoring engine."
        ]
    }

    if missing:
        payload["blockers"]=["BUSINESS_QUALITY_CANONICAL_INPUTS_INCOMPLETE"]
        out.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
        print("STATUS=BLOCKED")
        print("MISSING="+json.dumps(missing,ensure_ascii=False))
        print("RESULT="+str(out))
        print("FIN_PROD_V6_BUSINESS_QUALITY_ADAPTER_REV3=PASS_FAIL_CLOSED")
        return

    raw_fields=[
        "revenue","gross_profit","operating_profit","net_income","total_assets",
        "total_equity","cash_and_equivalents","current_assets","current_liabilities",
        "operating_cash_flow","capital_expenditure"
    ]
    raw_ends={ev[k]["period_end"] for k in raw_fields if ev[k].get("period_end")}
    if len(raw_ends)!=1 or ev["ebitda"].get("period_end") not in raw_ends:
        payload["blockers"]=["MIXED_PERIOD_RAW_CANONICAL_INPUTS"]
        out.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
        print("STATUS=BLOCKED")
        print("MISSING=[\"MIXED_PERIOD_RAW_CANONICAL_INPUTS\"]")
        print("RESULT="+str(out))
        print("FIN_PROD_V6_BUSINESS_QUALITY_ADAPTER_REV3=PASS_FAIL_CLOSED")
        return

    period_end=date.fromisoformat(next(iter(raw_ends)))
    q={3:1,6:2,9:3,12:4}[period_end.month]
    pub=report.identity.published_at.date() if report.identity.published_at else None

    period=FinancialPeriod(
        symbol="TUPRS",
        period_end=period_end,
        fiscal_year=period_end.year,
        fiscal_quarter=q,
        currency=pit.currency,
        revenue=vals["revenue"],
        gross_profit=vals["gross_profit"],
        operating_profit=vals["operating_profit"],
        ebitda=vals["ebitda"],
        net_income=vals["net_income"],
        total_assets=vals["total_assets"],
        total_equity=vals["total_equity"],
        total_debt=vals["total_debt"],
        cash_and_equivalents=vals["cash_and_equivalents"],
        current_assets=vals["current_assets"],
        current_liabilities=vals["current_liabilities"],
        operating_cash_flow=vals["operating_cash_flow"],
        capital_expenditure=vals["capital_expenditure"],
        shares_outstanding=vals["shares_outstanding"],
        source="FIN001_FIN002_PLUS_EXISTING_FIN006_AND_ACCEPTED_DERIVATIONS",
        published_at=pub,
    )

    freshness=evaluate_fundamental_freshness([period],today=date(2026,8,4))
    snapshot=build_fundamental_snapshot([period],source_metadata={
        "adapter":"FIN-PROD-V6-REV3",
        "as_of":"2026-08-04",
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
        print("FUNDAMENTAL_QUALITY_LOCKED=True")
        print("RESULT="+str(out))
        print("FIN_PROD_V6_BUSINESS_QUALITY_ADAPTER_REV3=PASS_FAIL_CLOSED")
        return

    payload["status"]="PASS"
    payload["business_quality"]=str(score)
    payload["blockers"]=[]
    out.write_text(json.dumps(payload,ensure_ascii=False,indent=2,default=str),encoding="utf-8")

    print("STATUS=PASS")
    print("EBITDA="+str(vals["ebitda"]))
    print("SHARES_OUTSTANDING="+str(vals["shares_outstanding"]))
    print("BUSINESS_QUALITY="+str(score))
    print("FUNDAMENTAL_QUALITY_LOCKED=False")
    print("RESULT="+str(out))
    print("FIN_PROD_V6_BUSINESS_QUALITY_ADAPTER_REV3=PASS")

if __name__=="__main__":
    main()
