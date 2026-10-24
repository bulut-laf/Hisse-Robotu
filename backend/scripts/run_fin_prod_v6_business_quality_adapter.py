
from __future__ import annotations

import argparse
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
import json
import sys

def d(v):
    if v is None:
        return None
    return Decimal(str(v))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--kap-xls", required=True)
    args=ap.parse_args()

    root=Path(args.project_root)
    backend=root/"backend"
    sys.path.insert(0,str(backend))

    from app.data.kap_financial_xls import import_kap_financial_xls_bytes
    from app.data.historical_financial_series import build_historical_financial_series
    from app.models.fundamental_models import FinancialPeriod
    from app.analysis.fundamental_analysis import build_fundamental_snapshot
    from app.analysis.fundamental_quality import calculate_fundamental_quality
    from app.data.fundamental_data import evaluate_fundamental_freshness

    xls=Path(args.kap_xls)
    outdir=backend/"data"/"financial_intelligence"
    outdir.mkdir(parents=True, exist_ok=True)
    out=outdir/"TUPRS_business_quality_canonical_adapter.json"

    if not xls.exists():
        raise SystemExit(f"KAP_XLS_MISSING:{xls}")

    report=import_kap_financial_xls_bytes(xls.read_bytes(), source_name=xls.name)
    series=build_historical_financial_series((report,))
    as_of=datetime(2026,8,4,23,59,59)
    pit=series.available_as_of(as_of)

    if report.identity.symbol != "TUPRS":
        raise SystemExit("SYMBOL_MISMATCH")

    # Exact canonical code inventory from FIN-001/002.
    code_inventory=sorted({p.metric_code for p in pit.points})
    print("CANONICAL_CODES="+json.dumps(code_inventory,ensure_ascii=False))

    def latest(code):
        p=pit.latest_value(code, as_of=as_of)
        return p

    # Conservative exact-code candidates only. We do not convert ratios/proxies
    # into raw statement values and we do not synthesize missing fields.
    candidates = {
        "revenue": ("REVENUE",),
        "gross_profit": ("GROSS_PROFIT",),
        "operating_profit": ("OPERATING_PROFIT",),
        "ebitda": ("EBITDA",),
        "net_income": ("NET_INCOME",),
        "total_assets": ("TOTAL_ASSETS",),
        "total_equity": ("TOTAL_EQUITY","PARENT_EQUITY"),
        "total_debt": ("FINANCIAL_DEBT","TOTAL_DEBT"),
        "cash_and_equivalents": ("CASH_AND_CASH_EQUIVALENTS","CASH_EQUIVALENTS"),
        "current_assets": ("CURRENT_ASSETS",),
        "current_liabilities": ("CURRENT_LIABILITIES",),
        "operating_cash_flow": ("OPERATING_CASH_FLOW","CASH_FROM_OPERATIONS"),
        "capital_expenditure": ("CAPEX","CAPITAL_EXPENDITURE"),
    }

    resolved={}
    evidence={}
    for field,codes in candidates.items():
        hit=None
        for code in codes:
            p=latest(code)
            if p is not None:
                hit=p
                break
        if hit is not None:
            resolved[field]=hit.value
            evidence[field]={
                "metric_code":hit.metric_code,
                "value":str(hit.value),
                "period_start":None if hit.period_start is None else hit.period_start.isoformat(),
                "period_end":hit.period_end.isoformat(),
                "period_kind":hit.period_kind,
                "published_at":None if hit.published_at is None else hit.published_at.isoformat(),
                "source_sha256":hit.source_sha256,
            }

    # Shares are not fabricated. Reuse canonical ownership acceptance only if present.
    ownership_path=outdir/"TUPRS_market_ownership_acceptance.json"
    shares=None
    shares_evidence=None
    if ownership_path.exists():
        oj=json.loads(ownership_path.read_text(encoding="utf-8-sig"))
        paths=[
            ("ownership","total_shares"),
            ("snapshot","total_shares"),
            ("total_shares",),
        ]
        for path in paths:
            cur=oj
            ok=True
            for key in path:
                if not isinstance(cur,dict) or key not in cur:
                    ok=False; break
                cur=cur[key]
            if ok and cur is not None:
                shares=d(cur)
                shares_evidence={"source":str(ownership_path),"field":".".join(path),"value":str(cur)}
                break

    required_fields = [
        "revenue","gross_profit","operating_profit","ebitda","net_income",
        "total_assets","total_equity","total_debt","cash_and_equivalents",
        "current_assets","current_liabilities","operating_cash_flow","capital_expenditure"
    ]
    missing=[k for k in required_fields if k not in resolved]
    if shares is None:
        missing.append("shares_outstanding")

    # All raw values must refer to the current disclosed period; mixed-period
    # reconstruction is forbidden.
    current_ends={e["period_end"] for e in evidence.values()}
    mixed_period = len(current_ends) != 1
    if mixed_period:
        missing.append("MIXED_PERIOD_RAW_FIELDS")

    payload={
        "status":"BLOCKED",
        "mode":"READ_ONLY_CANONICAL_BUSINESS_QUALITY_ADAPTER_V6",
        "symbol":"TUPRS",
        "as_of_date":"2026-08-04",
        "kap_xls":str(xls),
        "canonical_code_inventory":code_inventory,
        "resolved_raw_fields":evidence,
        "shares_evidence":shares_evidence,
        "missing_requirements":missing,
        "business_quality":None,
        "blockers":[],
        "rules":[
            "No ratio/proxy is converted back into a raw financial-statement value.",
            "No missing field is converted to zero.",
            "Only FIN-001/FIN-002 canonical points available as of 2026-08-04 are used.",
            "Existing calculate_fundamental_quality is the only scoring engine."
        ],
    }

    if missing:
        payload["blockers"]=["BUSINESS_QUALITY_RAW_CANONICAL_INPUTS_INCOMPLETE"]
        out.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
        print("STATUS=BLOCKED")
        print("MISSING="+json.dumps(missing,ensure_ascii=False))
        print("RESULT="+str(out))
        print("FIN_PROD_V6_BUSINESS_QUALITY_ADAPTER=PASS_FAIL_CLOSED")
        return

    period_end=date.fromisoformat(next(iter(current_ends)))
    published=report.identity.published_at.date() if report.identity.published_at else None

    period=FinancialPeriod(
        symbol="TUPRS",
        period_end=period_end,
        fiscal_year=period_end.year,
        fiscal_quarter=2 if period_end.month==6 else (1 if period_end.month==3 else (3 if period_end.month==9 else 4)),
        currency=pit.currency,
        revenue=resolved["revenue"],
        gross_profit=resolved["gross_profit"],
        operating_profit=resolved["operating_profit"],
        ebitda=resolved["ebitda"],
        net_income=resolved["net_income"],
        total_assets=resolved["total_assets"],
        total_equity=resolved["total_equity"],
        total_debt=resolved["total_debt"],
        cash_and_equivalents=resolved["cash_and_equivalents"],
        current_assets=resolved["current_assets"],
        current_liabilities=resolved["current_liabilities"],
        operating_cash_flow=resolved["operating_cash_flow"],
        capital_expenditure=resolved["capital_expenditure"],
        shares_outstanding=shares,
        source="FIN001_FIN002_CANONICAL_ADAPTER",
        published_at=published,
    )

    freshness=evaluate_fundamental_freshness([period], today=date(2026,8,4))
    snapshot=build_fundamental_snapshot([period], source_metadata={
        "adapter":"FIN-PROD-V6",
        "kap_source_sha256":report.source_sha256,
        "as_of":"2026-08-04",
    })
    quality=calculate_fundamental_quality(snapshot,freshness)

    qscore=getattr(quality,"total_score",None)
    locked=getattr(quality,"locked",True)

    payload["fundamental_quality"]={
        "total_score":qscore,
        "locked":locked,
        "grade":getattr(quality,"grade",None),
        "period_key":getattr(quality,"period_key",None),
        "explanation":getattr(quality,"explanation",None),
    }

    if locked or qscore is None:
        payload["blockers"]=["EXISTING_FUNDAMENTAL_QUALITY_ENGINE_LOCKED"]
        out.write_text(json.dumps(payload,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
        print("STATUS=BLOCKED")
        print("FUNDAMENTAL_QUALITY_LOCKED=True")
        print("RESULT="+str(out))
        print("FIN_PROD_V6_BUSINESS_QUALITY_ADAPTER=PASS_FAIL_CLOSED")
        return

    payload["status"]="PASS"
    payload["business_quality"]=str(qscore)
    payload["blockers"]=[]
    out.write_text(json.dumps(payload,ensure_ascii=False,indent=2,default=str),encoding="utf-8")

    print("STATUS=PASS")
    print("BUSINESS_QUALITY="+str(qscore))
    print("FUNDAMENTAL_QUALITY_LOCKED=False")
    print("RESULT="+str(out))
    print("FIN_PROD_V6_BUSINESS_QUALITY_ADAPTER=PASS")

if __name__=="__main__":
    main()
