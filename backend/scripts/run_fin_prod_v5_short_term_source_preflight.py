
from __future__ import annotations
import ast, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
OUT = BACKEND / "data" / "financial_intelligence" / "FIN_PROD_V5_SHORT_TERM_SOURCE_PREFLIGHT.json"

KEYWORDS = (
    "canonical_close","ohlcv","market","technical","price","volume","trend",
    "momentum","atr","rsi","macd","regime","liquidity","volatility",
    "relative_strength","support","resistance","scheduled_session","delayed_data",
)

def inspect_py(path: Path):
    try:
        text = path.read_text(encoding="utf-8-sig")
    except Exception:
        return None
    low = text.lower()
    kws = sorted({k for k in KEYWORDS if k in low})
    if not kws:
        return None
    try:
        tree = ast.parse(text)
        parse = "PASS"
        funcs = sorted({n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))})[:80]
        classes = sorted({n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)})[:40]
    except SyntaxError:
        parse, funcs, classes = "FAIL", [], []
    score_map = {"canonical_close":8,"ohlcv":7,"market":6,"technical":6,"price":5,"volume":5,
                 "trend":4,"momentum":4,"atr":3,"regime":3,"liquidity":3,"volatility":3}
    return {
        "path": str(path.relative_to(ROOT)),
        "parse_status": parse,
        "matched_keywords": kws,
        "evidence_score": sum(score_map.get(k,1) for k in kws),
        "functions": funcs,
        "classes": classes,
    }

def main():
    rows = []
    app = BACKEND / "app"
    if app.exists():
        for path in app.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            item = inspect_py(path)
            if item:
                rows.append(item)

    rows.sort(key=lambda x: (-x["evidence_score"], x["path"]))

    payload = {
        "status": "PASS",
        "mode": "READ_ONLY_SHORT_TERM_SOURCE_PREFLIGHT_V5",
        "candidate_count": len(rows),
        "likely_sources": rows[:120],
        "required_context_fields": [
            "symbol","as_of_date","price_reference","trend_context","momentum_context",
            "volume_liquidity_context","volatility_context","market_regime_context",
            "data_quality","source_refs"
        ],
        "strict_rules": [
            "No AL/SAT authority.",
            "No scanner/ranking/watchlist mutation.",
            "No portfolio mutation.",
            "No missing metric becomes zero.",
            "No current/live value may be backfilled into a historical as_of_date.",
            "Only existing canonical or production data sources may be wired.",
            "Adapter creation is blocked until exact source seams are identified."
        ],
        "schema_version": "fin-prod-v5-short-term-source-preflight-v1",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Console-safe summary only. Full UTF-8 payload remains in OUT.
    print(json.dumps({
        "status": payload["status"],
        "mode": payload["mode"],
        "candidate_count": payload["candidate_count"],
        "schema_version": payload["schema_version"],
    }, ensure_ascii=True))
    print("FIN-PROD-V5 PREFLIGHT PASS")
    print(f"RESULT={OUT}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
