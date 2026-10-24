import ast
from pathlib import Path

ROOT = Path("D:/Projects/Hisse-Robotu")

targets = {
    "backend/app/data/market_data.py": [
        "fiyat_verisi_getir",
        "fiyat_verisini_duzelt",
        "guvenli_fiyat_verisi_getir",
    ],
    "backend/app/data/bist_official_daily.py": [
        "official_daily_data_get",
        "normalize_symbol",
    ],
    "backend/app/operations/scheduled_operation_phase_runner.py": [
        "canonical_close",
        "execute_operation_phase",
    ],
    "backend/app/analysis/technical_confirmation.py": [
        "teknik_teyit_analizi_yap",
        "zaman_dilimi_teyidini_hesapla",
    ],
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

for rel, names in targets.items():
    path = ROOT / rel

    print("=" * 80)
    print(f"FILE={rel}")
    print(f"EXISTS={path.exists()}")

    if not path.exists():
        continue

    text = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(text)

    found = set()

    for node in tree.body:
        name = getattr(node, "name", None)

        if name not in names:
            continue

        found.add(name)

        print("-" * 80)
        print(f"NAME={name}")
        print(f"TYPE={type(node).__name__}")
        print(f"LINES={node.lineno}-{getattr(node, 'end_lineno', node.lineno)}")

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            print("SIGNATURE=" + ast.unparse(node.args))
            print(
                "RETURN_ANNOTATION="
                + (ast.unparse(node.returns) if node.returns else "NONE")
            )

            returns = []
            for item in ast.walk(node):
                if isinstance(item, ast.Return):
                    if item.value is None:
                        returns.append("None")
                    else:
                        try:
                            returns.append(ast.unparse(item.value))
                        except Exception:
                            returns.append(type(item.value).__name__)

            for value in returns[:20]:
                print("RETURN_EXPR=" + value)

        elif isinstance(node, ast.ClassDef):
            print("BASES=" + ",".join(ast.unparse(x) for x in node.bases))

            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    field = item.target.id + ":" + ast.unparse(item.annotation)

                    if item.value is not None:
                        field += "=" + ast.unparse(item.value)

                    print("FIELD=" + field)

    for missing in sorted(set(names) - found):
        print("MISSING=" + missing)

print("=" * 80)
print("FIN_PROD_V5_EXACT_SEAMS_V2=PASS")
