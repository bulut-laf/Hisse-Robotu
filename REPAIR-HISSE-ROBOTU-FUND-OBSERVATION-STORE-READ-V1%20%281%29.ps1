param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$Py = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Py)) {
    throw "PYTHON_NOT_FOUND: $Py"
}

$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$RunDir = Join-Path $ProjectRoot "_fund_observation_store_read_repair_v1\$Stamp"
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

$DiagPy = Join-Path $RunDir "repair_store.py"

$Source = @'
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))

from backend.app.funds.store import FundStoreError, fund_observation_store

store = fund_observation_store()
path = Path(store.path)
tmp = path.with_suffix(path.suffix + ".tmp")
backup_dir = root / "_fund_observation_store_read_repair_v1" / sys.argv[2] / "backup"
backup_dir.mkdir(parents=True, exist_ok=True)

print(f"STORE_PATH={path}")
print(f"STORE_EXISTS={'YES' if path.exists() else 'NO'}")
print(f"TMP_PATH={tmp}")
print(f"TMP_EXISTS={'YES' if tmp.exists() else 'NO'}")

if path.exists() and not path.is_file():
    print("NO_MUTATION=YES")
    raise SystemExit("STORE_PATH_NOT_FILE")

def parse_bytes(raw: bytes):
    # First canonical UTF-8, then BOM-tolerant UTF-8-SIG for safe diagnosis.
    try:
        text = raw.decode("utf-8")
        return json.loads(text), "UTF8"
    except Exception as utf8_exc:
        try:
            text = raw.decode("utf-8-sig")
            return json.loads(text), "UTF8_SIG"
        except Exception:
            raise utf8_exc

def valid_dict_file(candidate: Path):
    if not candidate.exists() or not candidate.is_file():
        return None
    raw = candidate.read_bytes()
    try:
        payload, mode = parse_bytes(raw)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    return payload, mode, raw

# Missing file is already a valid empty-store state according to the store contract.
if not path.exists():
    try:
        records = store.list_records()
    except Exception as exc:
        print(f"POSTCHECK_ERROR={type(exc).__name__}:{exc}")
        raise
    print(f"STORE_RECORDS={len(records)}")
    print("STORE_READ=PASS")
    print("REPAIR=NOT_REQUIRED_MISSING_STORE")
    print("STATUS_FINAL=SUCCESS")
    raise SystemExit(0)

raw = path.read_bytes()
print(f"STORE_BYTES={len(raw)}")
print(f"STORE_BOM={'YES' if raw.startswith(bytes([0xEF,0xBB,0xBF])) else 'NO'}")

current = valid_dict_file(path)

if current is not None:
    payload, mode, raw = current
    print(f"STORE_JSON=VALID")
    print(f"STORE_OBJECT=YES")
    print(f"STORE_RECORD_COUNT={len(payload)}")
    print(f"STORE_DECODE_MODE={mode}")

    if mode == "UTF8_SIG" and raw.startswith(bytes([0xEF,0xBB,0xBF])):
        backup = backup_dir / path.name
        shutil.copy2(path, backup)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(f"BACKUP={backup}")
        print("REPAIR=UTF8_BOM_REMOVED")
    else:
        print("REPAIR=NOT_REQUIRED_JSON_VALID")
else:
    print("STORE_JSON=INVALID")

    # Prefer the store's own atomic-write temp sibling. This is the only
    # automatic recovery candidate: same store, same writer contract.
    temp_valid = valid_dict_file(tmp)
    if temp_valid is None:
        # Preserve evidence and fail closed. Do not create an empty store and
        # do not guess from stale backups.
        corrupt_copy = backup_dir / (path.name + ".corrupt")
        shutil.copy2(path, corrupt_copy)
        print(f"CORRUPT_BACKUP={corrupt_copy}")

        try:
            path.read_text(encoding="utf-8")
        except Exception as exc:
            print(f"READ_ERROR={type(exc).__name__}:{exc}")
        else:
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                print(f"JSON_ERROR={type(exc).__name__}:{exc}")

        print("NO_MUTATION=YES")
        raise SystemExit("INVALID_STORE_AND_NO_VALID_ATOMIC_TMP")

    payload, mode, _ = temp_valid
    backup = backup_dir / (path.name + ".corrupt")
    shutil.copy2(path, backup)
    shutil.copy2(tmp, path)

    # Normalize BOM only if necessary.
    if mode == "UTF8_SIG":
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    print(f"CORRUPT_BACKUP={backup}")
    print(f"RECOVERED_RECORD_COUNT={len(payload)}")
    print("REPAIR=VALID_ATOMIC_TMP_RESTORED")

# Contract-level postcheck through the real application store.
try:
    records = store.list_records()
except FundStoreError as exc:
    print(f"POSTCHECK=FAILED:{exc}")
    raise

print(f"POSTCHECK=PASS")
print(f"STORE_RECORDS={len(records)}")

ap5 = [
    row for row in records
    if str(row.get("canonical_fund_id", "")).strip().lower() == "fund:tefas:ap5"
]
print(f"AP5_OBSERVATION_RECORDS={len(ap5)}")

# Additional profile read-model smoke check if the production module is importable.
try:
    from backend.app.funds.fund_profile import build_fund_profile_read_model
    from backend.app.funds.portfolio_tracking import fund_portfolio_snapshot_store

    profile = build_fund_profile_read_model(
        "fund:tefas:AP5",
        observation_store=store,
        portfolio_store=fund_portfolio_snapshot_store(),
    )
except Exception as exc:
    print(f"AP5_PROFILE_SMOKE=FAILED:{type(exc).__name__}:{exc}")
else:
    print("AP5_PROFILE_SMOKE=PASS")
    print(f"AP5_PROFILE_PRICE={getattr(profile, 'unit_price', None)}")
    print(f"AP5_PROFILE_OBSERVATION_COUNT={getattr(profile, 'observation_count', None)}")

print("AL_SAT_MUTATION=NO")
print("CANONICAL_RANKING_MUTATION=NO")
print("STATUS_FINAL=SUCCESS")
'@

Set-Content -LiteralPath $DiagPy -Value $Source -Encoding UTF8

$RunName = Split-Path -Leaf $RunDir
& $Py $DiagPy $ProjectRoot $RunName
if ($LASTEXITCODE -ne 0) {
    throw "FUND_OBSERVATION_STORE_READ_REPAIR_FAILED"
}

$env:PYTHONPATH = (Join-Path $ProjectRoot "backend")

Push-Location $ProjectRoot
try {
    & $Py -m pytest -q backend\tests\test_fund_analysis_center_ui_v1.py
    if ($LASTEXITCODE -ne 0) {
        throw "TARGET_UI_TEST_FAILED"
    }
    Write-Host "TARGET_UI_TEST=PASS"
}
finally {
    Pop-Location
}

Write-Host "FUND_OBSERVATION_STORE_READ_REPAIR_V1=COMPLETE"
