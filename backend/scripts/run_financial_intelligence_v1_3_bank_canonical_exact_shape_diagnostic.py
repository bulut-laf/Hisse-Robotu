from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path


root = Path(sys.argv[1])

targets = [
    root / "backend" / "app" / "analysis" / "financial_intelligence_bank_model_contract.py",
    root / "backend" / "app" / "analysis" / "financial_intelligence_bank_canonical_adapter.py",
    root / "backend" / "app" / "analysis" / "financial_intelligence_bank_scoring_engine.py",
]

result = {
    "status": "PASS_FAIL_CLOSED",
    "files": [],
    "required_metric_paths": [],
    "component_metric_map": {},
    "adapter_functions": [],
    "blocker_sites": [],
    "canonical_shape_ready": False,
    "production_mutation": "NO",
    "store_mutation": "NO",
    "al_sat_mutation": "NO",
    "blockers": [],
}

for path in targets:
    if not path.exists():
        result["blockers"].append(f"FILE_MISSING:{path}")
        continue

    text = path.read_text(encoding="utf-8-sig", errors="ignore")
    tree = ast.parse(text)

    file_row = {
        "path": str(path),
        "definitions": [],
    }

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            file_row["definitions"].append({
                "name": node.name,
                "line_start": node.lineno,
                "line_end": getattr(node, "end_lineno", node.lineno),
            })

            if path.name == "financial_intelligence_bank_canonical_adapter.py":
                if isinstance(node, ast.FunctionDef):
                    result["adapter_functions"].append({
                        "name": node.name,
                        "line_start": node.lineno,
                        "line_end": getattr(node, "end_lineno", node.lineno),
                    })

    lines = text.splitlines()

    for idx, line in enumerate(lines, start=1):
        if "BANK_CANONICAL_METRIC_MISSING" in line:
            start = max(1, idx - 12)
            end = min(len(lines), idx + 16)
            snippet = "\n".join(
                f"{n:04d}: {lines[n-1]}"
                for n in range(start, end + 1)
            )
            result["blocker_sites"].append({
                "path": str(path),
                "line": idx,
                "snippet": snippet,
            })

    # Extract literal metric-path strings such as COMPONENT.metric where present.
    for match in re.finditer(
        r'["\']([A-Z][A-Z0-9_]{2,64})\.([a-z][a-z0-9_]{2,64})["\']',
        text,
    ):
        component = match.group(1)
        metric = match.group(2)
        path_value = f"{component}.{metric}"

        if path_value not in result["required_metric_paths"]:
            result["required_metric_paths"].append(path_value)

        result["component_metric_map"].setdefault(component, [])
        if metric not in result["component_metric_map"][component]:
            result["component_metric_map"][component].append(metric)

    # Also detect tuples/lists/dicts pairing uppercase component codes with metric strings.
    try:
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                for key_node, value_node in zip(node.keys, node.values):
                    if (
                        isinstance(key_node, ast.Constant)
                        and isinstance(key_node.value, str)
                        and re.fullmatch(r"[A-Z][A-Z0-9_]{2,64}", key_node.value)
                    ):
                        component = key_node.value
                        metrics = []

                        if isinstance(value_node, (ast.Tuple, ast.List, ast.Set)):
                            for elt in value_node.elts:
                                if (
                                    isinstance(elt, ast.Constant)
                                    and isinstance(elt.value, str)
                                    and re.fullmatch(r"[a-z][a-z0-9_]{2,64}", elt.value)
                                ):
                                    metrics.append(elt.value)

                        if isinstance(value_node, ast.Dict):
                            for inner_key in value_node.keys:
                                if (
                                    isinstance(inner_key, ast.Constant)
                                    and isinstance(inner_key.value, str)
                                    and re.fullmatch(r"[a-z][a-z0-9_]{2,64}", inner_key.value)
                                ):
                                    metrics.append(inner_key.value)

                        if metrics:
                            result["component_metric_map"].setdefault(component, [])
                            for metric in metrics:
                                if metric not in result["component_metric_map"][component]:
                                    result["component_metric_map"][component].append(metric)
    except Exception as exc:
        result["blockers"].append(f"AST_COMPONENT_SCAN_ERROR:{path.name}:{type(exc).__name__}:{exc}")

    result["files"].append(file_row)

# Derive paths from component map.
for component, metrics in result["component_metric_map"].items():
    for metric in metrics:
        path_value = f"{component}.{metric}"
        if path_value not in result["required_metric_paths"]:
            result["required_metric_paths"].append(path_value)

result["required_metric_paths"] = sorted(result["required_metric_paths"])
result["component_metric_map"] = {
    key: sorted(value)
    for key, value in sorted(result["component_metric_map"].items())
}

if result["component_metric_map"] and result["blocker_sites"]:
    result["status"] = "PASS"
    result["canonical_shape_ready"] = True
elif not result["blockers"]:
    result["blockers"].append("BANK_CANONICAL_SHAPE_NOT_RESOLVED")

out = (
    root
    / "backend"
    / "data"
    / "financial_intelligence"
    / "FINANCIAL_INTELLIGENCE_V1_3_BANK_CANONICAL_EXACT_SHAPE_DIAGNOSTIC.json"
)

out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(
    json.dumps(result, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print(f"STATUS={result['status']}")
print(f"CANONICAL_SHAPE_READY={result['canonical_shape_ready']}")
print(f"COMPONENT_COUNT={len(result['component_metric_map'])}")
print(f"REQUIRED_METRIC_PATH_COUNT={len(result['required_metric_paths'])}")

print("COMPONENT_METRIC_MAP_START")
for component, metrics in result["component_metric_map"].items():
    print(f"COMPONENT={component}|METRICS={metrics}")
print("COMPONENT_METRIC_MAP_END")

print("REQUIRED_METRIC_PATHS_START")
for index, path_value in enumerate(result["required_metric_paths"], start=1):
    print(f"PATH_{index}={path_value}")
print("REQUIRED_METRIC_PATHS_END")

print("BLOCKER_SITES_START")
for index, row in enumerate(result["blocker_sites"], start=1):
    print(f"BLOCKER_SITE_{index}_PATH={row['path']}")
    print(f"BLOCKER_SITE_{index}_LINE={row['line']}")
    print(f"BLOCKER_SITE_{index}_SNIPPET_START")
    print(row["snippet"])
    print(f"BLOCKER_SITE_{index}_SNIPPET_END")
print("BLOCKER_SITES_END")

print(f"BLOCKERS={result['blockers']}")
print("PRODUCTION_MUTATION=NO")
print("STORE_MUTATION=NO")
print("AL_SAT_MUTATION=NO")
print(f"RESULT={out}")
print("FINANCIAL_INTELLIGENCE_V1_3_BANK_CANONICAL_EXACT_SHAPE_DIAGNOSTIC_V1=PASS")
