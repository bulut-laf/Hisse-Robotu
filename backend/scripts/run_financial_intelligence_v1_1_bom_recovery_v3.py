from __future__ import annotations

from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    backend = root / "backend"

    bom = bytes.fromhex("efbbbf")
    repaired = []

    for path in backend.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue

        raw = path.read_bytes()
        if raw.startswith(bom):
            path.write_bytes(raw[len(bom):])
            repaired.append(str(path))

    # Hard verification: no Python source under backend may retain UTF-8 BOM.
    remaining = []
    for path in backend.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        if path.read_bytes().startswith(bom):
            remaining.append(str(path))

    print(f"BOM_FILES_REPAIRED={len(repaired)}")
    for path in repaired:
        print(f"BOM_REPAIRED={path}")

    print(f"BOM_FILES_REMAINING={len(remaining)}")
    for path in remaining:
        print(f"BOM_REMAINING={path}")

    if remaining:
        raise SystemExit("UTF8_BOM_REPAIR_INCOMPLETE")

    print("FIN_INTEL_V1_1_BOM_RECOVERY_V3=PASS")


if __name__ == "__main__":
    main()
