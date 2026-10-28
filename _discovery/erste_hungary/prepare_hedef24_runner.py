from pathlib import Path
import re
import json

disc = Path("_discovery/erste_hungary")
source = disc / "run_erste_hungary_f3_nav_recovery_full.py"
portfolio = disc / "hedef24_portfolio_prepared_20261027.json"
target = disc / "run_hedef24_nav_recovery_20261027.py"

if not source.exists():
    raise SystemExit(f"SOURCE_MISSING={source}")
if not portfolio.exists():
    raise SystemExit(f"PORTFOLIO_MISSING={portfolio}")

data = json.loads(portfolio.read_text(encoding="utf-8"))

if isinstance(data, list):
    rows = data
elif isinstance(data, dict):
    rows = next(
        (v for v in data.values()
         if isinstance(v, list) and v and isinstance(v[0], dict)
         and "isin" in v[0]),
        None
    )
    if rows is None:
        raise SystemExit("PORTFOLIO_SCHEMA_NOT_RECOGNIZED")
else:
    raise SystemExit("PORTFOLIO_SCHEMA_NOT_RECOGNIZED")

isins = list(dict.fromkeys(
    str(row["isin"]).strip().upper()
    for row in rows if row.get("isin")
))
if len(isins) != 24:
    raise SystemExit(f"EXPECTED_24_ISINS_GOT={len(isins)}")

code = source.read_text(encoding="utf-8")

old_targets = re.compile(
    r'targets\s*=\s*\[\s*str\(row\["isin"\]\).*?'
    r'if str\(row\.get\("f3_state"\)\) == "UNAVAILABLE"\s*\]',
    re.S
)
replacement = (
    'portfolio_data = json.loads((DISC / '
    '"hedef24_portfolio_prepared_20261027.json").read_text(encoding="utf-8"))\n'
    'if isinstance(portfolio_data, dict):\n'
    '    portfolio_data = next((v for v in portfolio_data.values() '
    'if isinstance(v, list) and v and isinstance(v[0], dict) '
    'and "isin" in v[0]), [])\n'
    'targets = list(dict.fromkeys(str(row["isin"]).strip().upper() '
    'for row in portfolio_data if row.get("isin")))'
)
code, count = old_targets.subn(replacement, code, count=1)
if count != 1:
    raise SystemExit("TARGET_BLOCK_REPLACEMENT_FAILED; ORIGINAL_UNCHANGED")

for old, new in [
    ("f1_f2_f3_evidence_v2_full_20261020.json",
     "hedef24_f1_f2_f3_evidence_20261027.json"),
    ("f1_f2_f3_evidence_v2_summary_full_20261020.json",
     "hedef24_f1_f2_f3_summary_20261027.json"),
    ("f3_nav_recovery_v1_full_20261020.json",
     "hedef24_f3_nav_recovery_20261027.json"),
]:
    code = code.replace(old, new)

target.write_text(code, encoding="utf-8")
print("RUNNER_CREATED=PASS")
print(f"PORTFOLIO_ISINS={len(isins)}")
print(f"RUNNER={target}")
