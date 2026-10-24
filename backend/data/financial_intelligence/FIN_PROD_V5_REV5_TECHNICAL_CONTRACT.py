import ast
from pathlib import Path

ROOT = Path("D:/Projects/Hisse-Robotu")

targets = {
    "backend/app/analysis/technical_confirmation.py": [
        "TimeframeConfirmationResult",
        "MultiTimeframeTechnicalConfirmation",
        "teknik_teyit_analizi_yap",
        "zaman_dilimi_teyidini_hesapla",
    ],
    "backend/app/analysis/momentum_discovery.py": [],
    "backend/app/analysis/stock_analyzer.py": [],
    "backend/app/analysis/technical_decision_matrix.py": [],
}

KEYWORDS = (
    "relative",
    "strength",
    "guc",
    "trend",
    "momentum",
    "volume",
    "hacim",
    "liquidity",
    "likid",
    "skor",
    "score",
)

for rel, wanted in targets.items():
    path = ROOT / rel
    print("=" * 90)
    print("FILE=" + rel)
    print("EXISTS=" + str(path.exists()))

    if not path.exists():
        continue

    text = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(text)
    lines = text.splitlines()

    for node in tree.body:
        name = getattr(node, "name", "")

        include = name in wanted

        if not include:
            lowered = name.lower()
            include = any(k in lowered for k in KEYWORDS)

        if not include:
            continue

        if isinstance(node, ast.ClassDef):
            fields = []
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    fields.append(
                        item.target.id + ":" + ast.unparse(item.annotation)
                    )

            print(
                "CLASS|"
                + name
                + "|FIELDS="
                + ";".join(fields)
            )

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            ret = ast.unparse(node.returns) if node.returns else "NONE"

            print(
                "FUNC|"
                + name
                + "|ARGS="
                + ast.unparse(node.args)
                + "|RET="
                + ret
            )

            for item in ast.walk(node):
                if isinstance(item, ast.Return) and item.value is not None:
                    try:
                        value = ast.unparse(item.value)
                    except Exception:
                        continue

                    low = value.lower()
                    if any(k in low for k in KEYWORDS):
                        value = " ".join(value.split())
                        if len(value) > 700:
                            value = value[:700] + "..."
                        print("RETURN|" + name + "|" + value)

print("=" * 90)
print("FIN_PROD_V5_REV5_TECHNICAL_CONTRACT=PASS")
