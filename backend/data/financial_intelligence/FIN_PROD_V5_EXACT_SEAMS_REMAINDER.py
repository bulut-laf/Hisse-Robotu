import ast
from pathlib import Path

ROOT = Path("D:/Projects/Hisse-Robotu")

targets = {
    "backend/app/analysis/market_regime.py": [
        "piyasa_rejimini_analiz_et",
        "piyasa_rejimi_karsilastirmasi",
    ],
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
}

def returns(node):
    result = []
    for n in ast.walk(node):
        if isinstance(n, ast.Return):
            if n.value is None:
                result.append("None")
            else:
                try:
                    result.append(ast.unparse(n.value))
                except Exception:
                    result.append(type(n.value).__name__)
    return result[:12]

for rel, names in targets.items():
    path = ROOT / rel
    print("=" * 80)
    print("FILE=" + rel)
    print("EXISTS=" + str(path.exists()))

    if not path.exists():
        continue

    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    found = set()

    for node in tree.body:
        name = getattr(node, "name", None)
        if name not in names:
            continue

        found.add(name)
        print("-" * 80)
        print("NAME=" + name)
        print("TYPE=" + type(node).__name__)
        print(f"LINES={node.lineno}-{getattr(node,'end_lineno',node.lineno)}")

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            print("SIGNATURE=" + ast.unparse(node.args))
            print("RETURN_ANNOTATION=" + (ast.unparse(node.returns) if node.returns else "NONE"))
            for r in returns(node):
                print("RETURN_EXPR=" + r)

        elif isinstance(node, ast.ClassDef):
            print("BASES=" + ",".join(ast.unparse(x) for x in node.bases))
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    value = item.target.id + ":" + ast.unparse(item.annotation)
                    if item.value is not None:
                        value += "=" + ast.unparse(item.value)
                    print("FIELD=" + value)

    for missing in sorted(set(names) - found):
        print("MISSING=" + missing)

print("=" * 80)
print("FIN_PROD_V5_EXACT_SEAMS_REMAINDER=PASS")
