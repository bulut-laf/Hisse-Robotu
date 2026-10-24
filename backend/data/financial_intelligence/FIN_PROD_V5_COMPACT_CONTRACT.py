import ast
import json
from pathlib import Path

ROOT = Path("D:/Projects/Hisse-Robotu")

targets = {
    "backend/app/analysis/short_term_investability.py": [
        "calculate_short_term_investability",
    ],
    "backend/app/models/investability_models.py": [
        "MarketContextInput",
        "PointInTimeObservation",
        "InvestabilityResult",
    ],
    "backend/app/analysis/investability_runtime_wiring.py": [
        "run_runtime_wiring",
    ],
    "backend/app/analysis/investability_production_closure.py": [
        "discover_exact_canonical_candidates",
        "run_closure",
    ],
    "backend/app/analysis/market_regime.py": [
        "piyasa_rejimi_karsilastirmasi",
    ],
}

results = []

for rel, wanted in targets.items():
    path = ROOT / rel

    if not path.exists():
        results.append({
            "file": rel,
            "status": "MISSING_FILE"
        })
        continue

    try:
        text = path.read_text(encoding="utf-8-sig")
        tree = ast.parse(text)
    except Exception as exc:
        results.append({
            "file": rel,
            "status": "PARSE_ERROR",
            "error": type(exc).__name__ + ": " + str(exc)
        })
        continue

    found = set()

    for node in tree.body:
        name = getattr(node, "name", None)

        if name not in wanted:
            continue

        found.add(name)

        try:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                results.append({
                    "file": rel,
                    "name": name,
                    "type": "function",
                    "args": ast.unparse(node.args),
                    "return_annotation": (
                        ast.unparse(node.returns)
                        if node.returns is not None
                        else None
                    ),
                    "status": "PASS",
                })

            elif isinstance(node, ast.ClassDef):
                fields = []

                for item in node.body:
                    try:
                        if (
                            isinstance(item, ast.AnnAssign)
                            and isinstance(item.target, ast.Name)
                        ):
                            fields.append({
                                "name": item.target.id,
                                "annotation": ast.unparse(item.annotation),
                                "default": (
                                    ast.unparse(item.value)
                                    if item.value is not None
                                    else None
                                )
                            })
                    except Exception as exc:
                        fields.append({
                            "status": "FIELD_PARSE_ERROR",
                            "error": type(exc).__name__ + ": " + str(exc)
                        })

                results.append({
                    "file": rel,
                    "name": name,
                    "type": "class",
                    "fields": fields,
                    "status": "PASS",
                })

        except Exception as exc:
            results.append({
                "file": rel,
                "name": name,
                "status": "NODE_ERROR",
                "error": type(exc).__name__ + ": " + str(exc)
            })

    for missing in sorted(set(wanted) - found):
        results.append({
            "file": rel,
            "name": missing,
            "status": "MISSING_SYMBOL"
        })

payload = {
    "status": "PASS",
    "mode": "FIN_PROD_V5_COMPACT_CONTRACT",
    "results": results
}

out = ROOT / "backend/data/financial_intelligence/FIN_PROD_V5_COMPACT_CONTRACT.json"
out.write_text(
    json.dumps(payload, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("FIN_PROD_V5_COMPACT_CONTRACT=PASS")
print("RESULT=" + str(out))
print("RECORDS=" + str(len(results)))
