from pathlib import Path
import ast
import json

ROOT = Path("D:/Projects/Hisse-Robotu")
BACKEND = ROOT / "backend"

FIELDS = (
    "trend_puani",
    "goreceli_guc_puani",
    "likidite_puani",
)

print("FIN_PROD_V5_EXACT_PRODUCER_DISCOVERY")
print()

# ------------------------------------------------------------------
# 1. Existing real artifacts containing the exact fields
# ------------------------------------------------------------------
print("===== EXISTING_ARTIFACTS =====")

artifact_hits = 0

for path in sorted((BACKEND / "data").rglob("*.json")):
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        continue

    stack = [("$", obj)]

    while stack:
        obj_path, node = stack.pop()

        if isinstance(node, dict):
            present = [field for field in FIELDS if field in node]

            if present:
                artifact_hits += 1
                print("ARTIFACT=" + str(path))
                print("OBJECT_PATH=" + obj_path)

                for field in present:
                    print(field + "=" + repr(node.get(field)))

                for date_key in (
                    "analiz_tarihi",
                    "as_of_date",
                    "observation_date",
                    "publication_date",
                    "date",
                ):
                    if date_key in node:
                        print(date_key + "=" + repr(node.get(date_key)))

                for symbol_key in ("symbol", "sembol", "ticker"):
                    if symbol_key in node:
                        print(symbol_key + "=" + repr(node.get(symbol_key)))

                print("---")

            for key, value in node.items():
                if isinstance(value, (dict, list)):
                    stack.append((obj_path + "." + str(key), value))

        elif isinstance(node, list):
            for i, value in enumerate(node):
                if isinstance(value, (dict, list)):
                    stack.append((obj_path + f"[{i}]", value))

print("ARTIFACT_HITS=" + str(artifact_hits))
print()

# ------------------------------------------------------------------
# 2. Exact Python producers / assignments
# ------------------------------------------------------------------
print("===== EXACT_CODE_PRODUCERS =====")

producer_hits = 0

for path in sorted((BACKEND / "app").rglob("*.py")):
    try:
        text = path.read_text(encoding="utf-8-sig")
        tree = ast.parse(text)
    except Exception:
        continue

    lines = text.splitlines()

    for node in ast.walk(tree):
        hit_fields = set()

        # keyword args: MomentumCandidate(trend_puani=...)
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg in FIELDS:
                    hit_fields.add(kw.arg)

        # dict literals: {"trend_puani": ...}
        if isinstance(node, ast.Dict):
            for key in node.keys:
                if isinstance(key, ast.Constant) and key.value in FIELDS:
                    hit_fields.add(str(key.value))

        # assignments: trend_puani = ...
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = []
            if isinstance(node, ast.Assign):
                targets = node.targets
            else:
                targets = [node.target]

            for target in targets:
                if isinstance(target, ast.Name) and target.id in FIELDS:
                    hit_fields.add(target.id)

        if not hit_fields:
            continue

        producer_hits += 1

        parent_func = None
        for candidate in ast.walk(tree):
            if isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if (
                    candidate.lineno <= node.lineno
                    <= getattr(candidate, "end_lineno", candidate.lineno)
                ):
                    if parent_func is None or candidate.lineno >= parent_func.lineno:
                        parent_func = candidate

        print("FILE=" + str(path.relative_to(ROOT)))
        print("FIELDS=" + ",".join(sorted(hit_fields)))

        if parent_func is not None:
            print("FUNCTION=" + parent_func.name)
            print("SIGNATURE=" + ast.unparse(parent_func.args))
        else:
            print("FUNCTION=<module/class-body>")

        start = max(1, node.lineno - 3)
        end = min(
            len(lines),
            getattr(node, "end_lineno", node.lineno) + 3
        )

        print(f"LINES={start}-{end}")

        for i in range(start, end + 1):
            print(f"{i:05d}: {lines[i-1]}")

        print("---")

print("PRODUCER_HITS=" + str(producer_hits))
print()

# ------------------------------------------------------------------
# 3. MomentumDiscovery execution entry points
# ------------------------------------------------------------------
print("===== MOMENTUM_EXECUTION_ENTRYPOINTS =====")

path = BACKEND / "app" / "analysis" / "momentum_discovery.py"

if path.exists():
    text = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(text)

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    low = item.name.lower()

                    if any(
                        token in low
                        for token in (
                            "analiz",
                            "analyze",
                            "discover",
                            "tara",
                            "scan",
                            "run",
                            "execute",
                            "aday",
                        )
                    ):
                        print(
                            f"METHOD={node.name}.{item.name}"
                            f"|ARGS={ast.unparse(item.args)}"
                            f"|RET={ast.unparse(item.returns) if item.returns else 'NONE'}"
                        )

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            low = node.name.lower()

            if any(
                token in low
                for token in (
                    "analiz",
                    "discover",
                    "tara",
                    "scan",
                    "run",
                    "execute",
                    "aday",
                )
            ):
                print(
                    f"FUNC={node.name}"
                    f"|ARGS={ast.unparse(node.args)}"
                    f"|RET={ast.unparse(node.returns) if node.returns else 'NONE'}"
                )

print()
print("FIN_PROD_V5_EXACT_PRODUCER_DISCOVERY=PASS")
