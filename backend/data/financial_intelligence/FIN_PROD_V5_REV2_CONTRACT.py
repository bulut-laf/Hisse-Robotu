from pathlib import Path
import ast

ROOT = Path("D:/Projects/Hisse-Robotu")

targets = [
    (
        ROOT / "backend/app/analysis/short_term_investability.py",
        ["calculate_short_term_investability"]
    ),
    (
        ROOT / "backend/app/analysis/technical_confirmation.py",
        [
            "TimeframeConfirmationResult",
            "MultiTimeframeTechnicalConfirmation"
        ]
    ),
    (
        ROOT / "backend/app/data/bist_official_daily.py",
        ["yahoo_style_symbol"]
    ),
]

for path, wanted in targets:
    print("=" * 80)
    print("FILE=" + str(path.relative_to(ROOT)))

    text = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(text)
    lines = text.splitlines()

    for node in tree.body:
        if getattr(node, "name", None) not in wanted:
            continue

        print("-" * 80)
        print("NAME=" + node.name)

        start = node.lineno
        end = getattr(node, "end_lineno", start)

        for i in range(start, end + 1):
            print(f"{i:05d}: {lines[i-1]}")

print("=" * 80)
print("FIN_PROD_V5_REV2_CONTRACT=PASS")
