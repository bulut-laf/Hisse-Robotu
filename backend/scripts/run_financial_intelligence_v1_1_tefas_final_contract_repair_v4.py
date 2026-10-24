from __future__ import annotations

from pathlib import Path


def patch_tefas_adapter(path: Path) -> None:
    text = path.read_text(encoding="utf-8-sig")
    original = text

    inner_import = "    from urllib.request import Request, urlopen\n\n"
    if inner_import in text:
        text = text.replace(inner_import, "", 1)

    lines = text.splitlines(keepends=True)
    branch = None
    for i, line in enumerate(lines):
        if line == "    if period <= 0:\n":
            branch = i
            break

    if branch is None:
        raise RuntimeError("TEFAS_PERIOD_VALIDATION_ANCHOR_NOT_FOUND")
    if branch + 1 >= len(lines) or "raise ValueError" not in lines[branch + 1]:
        raise RuntimeError("TEFAS_PERIOD_VALIDATION_BODY_NOT_FOUND")

    already = any(
        "verified live history contract supports only period=12" in line
        for line in lines
    )
    if not already:
        insert_at = branch + 2
        verified = [
            "    if int(period) != 12:\n",
            "        raise ValueError(\n",
            '            f"TEFAS verified live history contract supports only period=12; period={period}"\n',
            "        )\n",
            "\n",
        ]
        lines[insert_at:insert_at] = verified

    text = "".join(lines)
    compile(text, str(path), "exec")

    if text == original:
        raise RuntimeError("TEFAS_ADAPTER_NOT_CHANGED")

    path.write_text(text, encoding="utf-8")


def patch_nonblocking_refresh(path: Path) -> None:
    text = path.read_text(encoding="utf-8-sig")
    original = text

    old = '''        if _JOB is not None:
            if _JOB.status == "RUNNING":
                if now - _JOB.started_at > timeout_seconds:
                    _JOB.generation += 1
                    _JOB.status = "TIMEOUT"
                    return TefasUniverseRefreshState(status="TIMEOUT")
                return TefasUniverseRefreshState(status="RUNNING")
'''

    new = '''        if _JOB is not None:
            # Timeout is a wall-clock contract for the queued job. A late worker
            # result must not overwrite or bypass the bounded timeout outcome.
            if now - _JOB.started_at > timeout_seconds:
                _JOB.generation += 1
                _JOB.status = "TIMEOUT"
                return TefasUniverseRefreshState(status="TIMEOUT")

            if _JOB.status == "RUNNING":
                return TefasUniverseRefreshState(status="RUNNING")
'''

    if old not in text:
        if "Timeout is a wall-clock contract for the queued job." in text:
            return
        raise RuntimeError("TEFAS_REFRESH_TIMEOUT_BLOCK_NOT_FOUND")

    text = text.replace(old, new, 1)
    compile(text, str(path), "exec")

    if text == original:
        raise RuntimeError("TEFAS_REFRESH_NOT_CHANGED")

    path.write_text(text, encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    adapter = root / "backend/app/funds/tefas_adapter.py"
    refresh = root / "backend/app/funds/tefas_universe_nonblocking_refresh.py"

    backup = root / "_backup" / "FIN_INTEL_V1_1_TEFAS_FINAL_CONTRACT_REPAIR_V4"
    backup.mkdir(parents=True, exist_ok=True)

    for src in (adapter, refresh):
        dst = backup / src.name
        if not dst.exists():
            dst.write_bytes(src.read_bytes())

    patch_tefas_adapter(adapter)
    patch_nonblocking_refresh(refresh)

    print(f"ADAPTER={adapter}")
    print(f"REFRESH={refresh}")
    print(f"BACKUP={backup}")
    print("TEFAS_NETWORK_BOUNDARY=MODULE_LEVEL_URLOPEN")
    print("TEFAS_VERIFIED_PERIOD=12")
    print("TEFAS_TIMEOUT_PRECEDENCE=ENFORCED")
    print("FIN_INTEL_V1_1_TEFAS_FINAL_CONTRACT_REPAIR_V4=PASS")


if __name__ == "__main__":
    main()
