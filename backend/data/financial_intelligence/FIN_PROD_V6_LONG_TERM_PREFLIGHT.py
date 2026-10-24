from pathlib import Path
import ast
import json

ROOT = Path(r"D:\Projects\Hisse-Robotu")
BACKEND = ROOT / "backend"
DATA = BACKEND / "data"

SEARCH_TERMS = (
    "business_quality",
    "governance",
    "growth_context",
    "quality_score",
    "governance_score",
    "growth_score",
    "long_term",
    "long_term_investability",
)

print("FIN_PROD_V6_LONG_TERM_PREFLIGHT")
print()

print("===== EXISTING_LONG_TERM_ARTIFACTS =====")
artifact_hits = 0

for path in sorted(DATA.rglob("*.json")):
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        continue

    text = json.dumps(obj, ensure_ascii=False).lower()

    if "tuprs" not in text and "tuprs" not in path.name.lower():
        continue

    matched = [term for term in SEARCH_TERMS if term.lower() in text]
    if not matched:
        continue

    artifact_hits += 1
    print("ARTIFACT=" + str(path))
    print("MATCHED=" + ",".join(matched))

    if isinstance(obj, dict):
        for key in (
            "status",
            "mode",
            "symbol",
            "as_of_date",
            "schema_version",
            "business_quality",
            "governance",
            "growth_context",
            "long_term",
            "long_term_coverage",
            "coverage",
        ):
            if key in obj:
                print(key + "=" + repr(obj.get(key)))

    print("---")

print("ARTIFACT_HITS=" + str(artifact_hits))
print()

print("===== EXACT_CODE_REFERENCES =====")
code_hits = 0

for path in sorted((BACKEND / "app").rglob("*.py")):
    try:
        text = path.read_text(encoding="utf-8-sig")
        tree = ast.parse(text)
    except Exception:
        continue

    lines = text.splitlines()

    for node in ast.walk(tree):
        hit = set()

        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value.lower()
            for term in SEARCH_TERMS:
                if term.lower() in value:
                    hit.add(term)

        if isinstance(node, ast.Name):
            low = node.id.lower()
            for term in SEARCH_TERMS:
                if term.lower() == low:
                    hit.add(term)

        if isinstance(node, ast.Attribute):
            low = node.attr.lower()
            for term in SEARCH_TERMS:
                if term.lower() == low:
                    hit.add(term)

        if not hit:
            continue

        code_hits += 1

        parent_func = None
        for candidate in ast.walk(tree):
            if isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end = getattr(candidate, "end_lineno", candidate.lineno)
                if candidate.lineno <= node.lineno <= end:
                    if parent_func is None or candidate.lineno >= parent_func.lineno:
                        parent_func = candidate

        print("FILE=" + str(path.relative_to(ROOT)))
        print("TERMS=" + ",".join(sorted(hit)))
        print("LINE=" + str(node.lineno))

        if parent_func is not None:
            print("FUNCTION=" + parent_func.name)
            try:
                print("ARGS=" + ast.unparse(parent_func.args))
            except Exception:
                pass
        else:
            print("FUNCTION=<module/class-body>")

        start = max(1, node.lineno - 4)
        end = min(len(lines), getattr(node, "end_lineno", node.lineno) + 6)

        for i in range(start, end + 1):
            print(f"{i:05d}: {lines[i-1]}")

        print("---")

print("CODE_HITS=" + str(code_hits))
print()

print("===== LONG_TERM_MODULE_ENTRYPOINTS =====")

for path in sorted((BACKEND / "app").rglob("*.py")):
    name = path.name.lower()
    if "long_term" not in name and "investability" not in name and "quality" not in name:
        continue

    try:
        text = path.read_text(encoding="utf-8-sig")
        tree = ast.parse(text)
    except Exception:
        continue

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            low = node.name.lower()
            if any(token in low for token in (
                "build","calculate","run","create","analy",
                "coverage","quality","governance","growth","long_term",
            )):
                try:
                    args = ast.unparse(node.args)
                except Exception:
                    args = "?"
                print("FUNC=" + str(path.relative_to(ROOT)) + "::" + node.name + "|ARGS=" + args)

        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                low = item.name.lower()
                if any(token in low for token in (
                    "build","calculate","run","create","analy",
                    "coverage","quality","governance","growth","long_term",
                )):
                    try:
                        args = ast.unparse(item.args)
                    except Exception:
                        args = "?"
                    print("METHOD=" + str(path.relative_to(ROOT)) + "::" + node.name + "." + item.name + "|ARGS=" + args)

print()
print("===== V4_EXPECTED_CONTRACT =====")
print("FILE=TUPRS_long_term_canonical_coverage.json")
print("REQUIRED=canonical")
print("REQUIRED=as_of_date")
print("REQUIRED=business_quality.status")
print("REQUIRED=governance.status")
print("REQUIRED=growth_context.status")
print("REQUIRED=data_quality.status")
print()
print("FIN_PROD_V6_LONG_TERM_PREFLIGHT=PASS")