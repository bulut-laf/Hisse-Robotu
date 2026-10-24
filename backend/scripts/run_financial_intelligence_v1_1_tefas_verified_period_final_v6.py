from __future__ import annotations

from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    path = root / "backend/app/funds/tefas_adapter.py"

    text = path.read_text(encoding="utf-8-sig")
    original = text

    # Verified TEFAS live history V1 contract is period=1.
    text = text.replace(
        "    period: int = 12,\n",
        "    period: int = 1,\n",
        1,
    )

    text = text.replace(
        "    if int(period) != 12:\n",
        "    if int(period) != 1:\n",
        1,
    )

    text = text.replace(
        "TEFAS verified live history contract supports only period=12; period={period}",
        "TEFAS verified live history contract supports only period=1; period={period}",
        1,
    )

    # Hard verification inside target function.
    start = text.find("def fetch_tefas_fund_history_rows(")
    if start < 0:
        raise RuntimeError("TARGET_FUNCTION_NOT_FOUND")

    next_def = text.find("\ndef ", start + 1)
    end = len(text) if next_def < 0 else next_def + 1
    block = text[start:end]

    if "period: int = 1" not in block:
        raise RuntimeError("DEFAULT_PERIOD_1_NOT_APPLIED")

    if "if int(period) != 1:" not in block:
        raise RuntimeError("PERIOD_1_GUARD_NOT_APPLIED")

    if "from urllib.request import Request, urlopen" in block:
        raise RuntimeError("LOCAL_URLOPEN_IMPORT_RETURNED")

    compile(text, str(path), "exec")

    if text == original:
        raise RuntimeError("TEFAS_PERIOD_REPAIR_NOT_CHANGED")

    backup = (
        root
        / "_backup"
        / "FIN_INTEL_V1_1_TEFAS_VERIFIED_PERIOD_FINAL_V6"
    )
    backup.mkdir(parents=True, exist_ok=True)

    dst = backup / path.name
    if not dst.exists():
        dst.write_bytes(path.read_bytes())

    path.write_text(text, encoding="utf-8")

    print(f"TARGET={path}")
    print(f"BACKUP={backup}")
    print("TEFAS_VERIFIED_PERIOD=1")
    print("DEFAULT_PERIOD=1")
    print("LOCAL_URLOPEN_IMPORT=ABSENT")
    print("FIN_INTEL_V1_1_TEFAS_VERIFIED_PERIOD_FINAL_V6=PASS")


if __name__ == "__main__":
    main()
