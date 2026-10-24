param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    throw "PYTHON_MISSING=$Python"
}

$oldPythonPath = $env:PYTHONPATH
$tmp = Join-Path $env:TEMP "hisse_daily10_baseline17_exact_recovery_v1.py"

try {
    Write-Host "=== HISSE ROBOTU — BASELINE 17 EXACT RECOVERY V1 ==="
    Write-Host "MODE=READ_ONLY"
    Write-Host "PRODUCTION_MUTATION=NO"
    Write-Host "TARGET_DATE=2026-08-17"
    Write-Host "TARGET_SHA256=04017af0e22aefd23b02f75cc96fa71a4f80b5c1dc6ee661dd57f1052e4712ef"
    Write-Host "GOAL=LOCATE_EXACT_HISTORICAL_BIST_CSV_BYTES"

    $env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($oldPythonPath)) {
        $ProjectRoot
    } else {
        "$ProjectRoot;$oldPythonPath"
    }

    $code = @'
from __future__ import annotations

import hashlib
import os
import sys
import zipfile
from pathlib import Path

from backend.app.analysis.bist_universe import bist_bilesen_csvsini_ayristir

project = Path(sys.argv[1])
target_sha = "04017af0e22aefd23b02f75cc96fa71a4f80b5c1dc6ee661dd57f1052e4712ef"

userprofile = Path(os.environ.get("USERPROFILE", ""))
temp = Path(os.environ.get("TEMP", ""))

roots = []
for p in (
    project,
    project.parent,
    userprofile / "Downloads",
    userprofile / "Desktop",
    userprofile / "Documents",
    userprofile / "OneDrive",
    temp,
):
    if p and p.exists():
        try:
            rp = p.resolve()
        except OSError:
            rp = p
        if rp not in roots:
            roots.append(rp)

skip_names = {
    ".git", ".venv", "node_modules", "__pycache__",
    ".pytest_cache", "AppData", "$Recycle.Bin",
}
candidate_tokens = (
    "bist_endeks_bilesenleri",
    "hisse_endeks_ds",
)

checked_files = 0
checked_zip_members = 0
matches = []
seen_paths = set()

def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def maybe_parse(raw: bytes, source: str):
    try:
        u = bist_bilesen_csvsini_ayristir(
            raw,
            evren_adi="BIST Tüm",
            endeks_kodu="XUTUM",
            kaynak=source,
            resmi_kaynaktan_guncel=False,
        )
        return len(u.semboller), u.tarih
    except Exception as exc:
        return None, f"PARSE_FAIL:{type(exc).__name__}:{exc}"

def consider_raw(raw: bytes, source: str):
    sha = digest(raw)
    if sha != target_sha:
        return
    count, meta = maybe_parse(raw, source)
    matches.append((source, len(raw), count, meta))

def walk_files(base: Path):
    stack = [base]
    while stack:
        current = stack.pop()
        try:
            entries = list(current.iterdir())
        except (OSError, PermissionError):
            continue

        for entry in entries:
            try:
                if entry.is_dir():
                    if entry.name in skip_names:
                        continue
                    # Avoid recursive OneDrive placeholder/system trees beyond useful depth.
                    stack.append(entry)
                    continue
            except OSError:
                continue

            yield entry

for root in roots:
    print(f"SEARCH_ROOT={root}")
    for path in walk_files(root):
        try:
            key = str(path.resolve())
        except OSError:
            key = str(path)
        if key in seen_paths:
            continue
        seen_paths.add(key)

        low = path.name.lower()
        suffix = path.suffix.lower()

        if suffix == ".csv" and any(tok in low for tok in candidate_tokens):
            checked_files += 1
            try:
                raw = path.read_bytes()
            except (OSError, PermissionError):
                continue
            consider_raw(raw, f"FILE::{path}")
            continue

        if suffix == ".zip":
            try:
                with zipfile.ZipFile(path, "r") as zf:
                    for name in zf.namelist():
                        base = Path(name).name.lower()
                        if not (
                            base.endswith(".csv")
                            and any(tok in base for tok in candidate_tokens)
                        ):
                            continue
                        checked_zip_members += 1
                        try:
                            raw = zf.read(name)
                        except (KeyError, RuntimeError):
                            continue
                        consider_raw(raw, f"ZIP::{path}::{name}")
            except (OSError, PermissionError, zipfile.BadZipFile):
                continue

print()
print("=== SEARCH SUMMARY ===")
print(f"SEARCH_ROOT_COUNT={len(roots)}")
print(f"CHECKED_CSV_FILES={checked_files}")
print(f"CHECKED_ZIP_MEMBERS={checked_zip_members}")
print(f"EXACT_SHA_MATCH_COUNT={len(matches)}")

print()
print("=== EXACT BASELINE MATCHES ===")
if not matches:
    print("EXACT_BASELINE=NONE")
else:
    for source, size, count, meta in matches:
        print(
            f"EXACT_BASELINE=FOUND | bytes={size} | "
            f"xutum_symbols={count if count is not None else '-'} | "
            f"universe_date={meta} | source={source}"
        )

print()
print("=== FINAL BASELINE RECOVERY DECISION ===")
if matches:
    print("BASELINE17_EXACT_RECOVERY=PROVEN")
    print(
        "NEXT=USE_EXACT_SHA_MATCH_READ_ONLY_TO_RECONCILE_17_TO_25_AND_BUILD_TARGET_UNIVERSES"
    )
else:
    print("BASELINE17_EXACT_RECOVERY=NOT_FOUND_ON_LOCAL_SEARCH_ROOTS")
    print(
        "NEXT=USE_KNOWN_17_AUG_SHA_AS_PROVEN_EXISTENCE_EVIDENCE;"
        "RECONSTRUCT_FROM_NEAREST_PRIOR_CANONICAL_SNAPSHOT_PLUS_OFFICIAL_XUTUM_CHANGE_LEDGER"
    )

print("BASELINE17_EXACT_RECOVERY_CHECK=PASS")
'@

    [System.IO.File]::WriteAllText(
        $tmp,
        $code,
        (New-Object System.Text.UTF8Encoding($false))
    )

    & $Python $tmp $ProjectRoot
    if ($LASTEXITCODE -ne 0) {
        throw "BASELINE17_EXACT_RECOVERY_CHECK_FAIL"
    }
}
finally {
    if (Test-Path -LiteralPath $tmp) {
        Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
    }

    if ($null -eq $oldPythonPath) {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    } else {
        $env:PYTHONPATH = $oldPythonPath
    }
}
