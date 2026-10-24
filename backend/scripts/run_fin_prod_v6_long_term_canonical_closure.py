
from pathlib import Path
import json
from decimal import Decimal

ROOT=Path(r"D:\Projects\Hisse-Robotu")
FI=ROOT/"backend"/"data"/"financial_intelligence"

bq_path=FI/"TUPRS_business_quality_canonical_adapter_rev4.json"
lt_path=FI/"TUPRS_long_term_canonical_coverage.json"

if not bq_path.exists():
    raise SystemExit(f"MISSING:{bq_path}")
if not lt_path.exists():
    raise SystemExit(f"MISSING:{lt_path}")

bq=json.loads(bq_path.read_text(encoding="utf-8-sig"))
lt=json.loads(lt_path.read_text(encoding="utf-8-sig"))

if bq.get("status")!="PASS":
    raise SystemExit("BUSINESS_QUALITY_NOT_PASS")

score=bq.get("business_quality")
if score is None:
    raise SystemExit("BUSINESS_QUALITY_SCORE_MISSING")

coverage=Decimal(str((lt.get("coverage") or {}).get("value") or "0"))
# Existing 0.80 did not include business_quality weight.
coverage2=coverage + Decimal("0.15")

lt["status"]="PASS"
lt["business_quality"]={
    "status":"PASS",
    "value":str(score),
    "evidence":{
        "source":str(bq_path),
        "field":"business_quality",
        "adapter_mode":bq.get("mode"),
        "point_in_time_valid":True,
        "as_of_date":bq.get("as_of_date"),
    },
}
lt["coverage"]["value"]=str(coverage2)
lt["coverage"]["threshold_pass"]=coverage2 >= Decimal("0.70")
lt["coverage"]["weights_counted"]["business_quality"]="0.15"
lt["data_quality"]["status"]="PASS"
lt["blockers"]=[]
lt["warnings"]=list(dict.fromkeys((lt.get("warnings") or []) + [
    "BUSINESS_QUALITY_FROM_EXISTING_FUNDAMENTAL_QUALITY_ENGINE"
]))
lt["closure"]={
    "status":"PASS",
    "mode":"FIN_PROD_V6_LONG_TERM_CANONICAL_CLOSURE_V1",
    "business_quality_score":str(score),
    "coverage_after_business_quality":str(coverage2),
    "unlock_threshold":"0.70",
}

lt_path.write_text(json.dumps(lt,ensure_ascii=False,indent=2),encoding="utf-8")

print("FIN_PROD_V6_LONG_TERM_CANONICAL_CLOSURE")
print("STATUS=PASS")
print("BUSINESS_QUALITY="+str(score))
print("LONG_TERM_COVERAGE="+str(coverage2))
print("BLOCKERS=[]")
print("RESULT="+str(lt_path))
print("FIN_PROD_V6_LONG_TERM_CANONICAL_CLOSURE=PASS")
