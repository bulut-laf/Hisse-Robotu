from __future__ import annotations

from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    path = root / "backend/app/funds/tefas_adapter.py"

    text = path.read_text(encoding="utf-8-sig")

    start_marker = "def fetch_tefas_fund_history_rows("
    start = text.find(start_marker)
    if start < 0:
        raise RuntimeError("TARGET_FUNCTION_NOT_FOUND")

    next_def = text.find("\ndef ", start + len(start_marker))
    end = len(text) if next_def < 0 else next_def + 1

    block = text[start:end]

    local_import = "    from urllib.request import Request, urlopen\n\n"
    if local_import not in block:
        raise RuntimeError("TARGET_LOCAL_URLOPEN_IMPORT_NOT_FOUND")

    new_block = block.replace(local_import, "", 1)
    new_text = text[:start] + new_block + text[end:]

    compile(new_text, str(path), "exec")

    backup = (
        root
        / "_backup"
        / "FIN_INTEL_V1_1_TEFAS_URLOPEN_BOUNDARY_FINAL_V5"
    )
    backup.mkdir(parents=True, exist_ok=True)

    dst = backup / path.name
    if not dst.exists():
        dst.write_bytes(path.read_bytes())

    path.write_text(new_text, encoding="utf-8")

    verify = path.read_text(encoding="utf-8")
    vstart = verify.find(start_marker)
    vnext = verify.find("\ndef ", vstart + len(start_marker))
    vend = len(verify) if vnext < 0 else vnext + 1
    vblock = verify[vstart:vend]

    if local_import in vblock:
        raise RuntimeError("TARGET_LOCAL_IMPORT_STILL_PRESENT")

    print(f"TARGET={path}")
    print(f"BACKUP={backup}")
    print("TARGET_FUNCTION=fetch_tefas_fund_history_rows")
    print("LOCAL_URLOPEN_IMPORT=REMOVED")
    print("NETWORK_BOUNDARY=MODULE_LEVEL_URLOPEN")
    print("FIN_INTEL_V1_1_TEFAS_URLOPEN_BOUNDARY_FINAL_V5=PASS")


if __name__ == "__main__":
    main()
