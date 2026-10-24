from __future__ import annotations

from pathlib import Path
import ast
import shutil
from datetime import datetime


def main():
    root = Path(r"D:\Projects\Hisse-Robotu")
    path = root / "backend" / "app" / "funds" / "tefas_adapter.py"

    if not path.exists():
        raise SystemExit(f"TARGET_MISSING:{path}")

    original = path.read_text(encoding="utf-8-sig")
    text = original

    old_sig = "period: int = 12,"
    if old_sig in text:
        text = text.replace(old_sig, "period: int = 1,", 1)
    elif "period: int = 1," not in text:
        raise SystemExit("PERIOD_DEFAULT_ANCHOR_NOT_FOUND")

    lines = text.splitlines()
    start = None
    end = None

    for i, line in enumerate(lines):
        if line.strip() == "if period < 1 or period > 12:":
            start = i
            j = i + 1
            while j < len(lines):
                if lines[j].strip().startswith("validate_official_source_timeout("):
                    end = j
                    break
                j += 1
            break

    if start is not None:
        if end is None:
            raise SystemExit("PERIOD_VALIDATION_END_NOT_FOUND")
        lines[start:end] = [
            "    if period != 1:",
            '        raise ValueError("TEFAS history verified contract requires period=1.")',
            "",
        ]
        text = "\n".join(lines) + ("\n" if original.endswith("\n") else "")
    elif "if period != 1:" not in text:
        raise SystemExit("PERIOD_VALIDATION_ANCHOR_NOT_FOUND")

    old_body = '{"fonKodu": code, "dil": "TR", "periyod": int(period)}'
    if old_body in text:
        text = text.replace(
            old_body,
            '{"fonKodu": code, "dil": "TR", "periyod": 1}',
            1,
        )
    elif '"periyod": 1' not in text:
        raise SystemExit("REQUEST_BODY_PERIOD_ANCHOR_NOT_FOUND")

    ast.parse(text)

    backup = (
        root
        / "_backup"
        / (
            "FIN_INTEL_V1_2_TEFAS_PERIOD1_REPAIR_"
            + datetime.now().strftime("%Y%m%d_%H%M%S")
        )
    )
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup / path.name)

    path.write_text(text, encoding="utf-8", newline="\n")

    print(f"TARGET={path}")
    print(f"BACKUP={backup}")
    print("VERIFIED_PERIOD_DEFAULT=1")
    print("UNVERIFIED_PERIOD_REJECT_BEFORE_NETWORK=True")
    print("REQUEST_BODY_PERIYOD=1")
    print("PRODUCTION_SOURCE_MUTATION=TEFAS_PERIOD_CONTRACT_REPAIR_ONLY")
    print("STORE_MUTATION=NO")
    print("AL_SAT_MUTATION=NO")
    print("FIN_INTEL_V1_2_TEFAS_PERIOD1_REGRESSION_REPAIR_V1=PASS")


if __name__ == "__main__":
    main()
