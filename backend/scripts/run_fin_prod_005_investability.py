import argparse, json
from pathlib import Path
from app.analysis.financial_intelligence_investability_acceptance import run_investability_acceptance

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--config",required=True)
    ap.add_argument("--out")
    a=ap.parse_args()
    r=run_investability_acceptance(json.loads(Path(a.config).read_text(encoding="utf-8")))
    text=json.dumps(r,ensure_ascii=False,indent=2)
    print(text)
    out=Path(a.out) if a.out else Path("backend/data/financial_intelligence")/f"{r['symbol']}_investability_acceptance.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(text+"\n",encoding="utf-8")
    print()
    print("FIN-PROD-005 ACCEPTANCE PASS")
    print("RESULT="+str(out.resolve()))
    return 0

if __name__=="__main__": raise SystemExit(main())
