from __future__ import annotations

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "backend" / "tests" / "test_dashboard_vbts_duplicate_message.py"
BACKUP = TARGET.with_suffix(".py.sprint41-scope-fix.bak")


def fail(message: str) -> None:
    print(f"HATA: {message}")
    raise SystemExit(1)


def main() -> None:
    if not TARGET.exists():
        fail(f"Dosya bulunamadı: {TARGET}")

    source = TARGET.read_text(encoding="utf-8")
    shutil.copy2(TARGET, BACKUP)

    old = '''    section = source[start:start + 2500]

    assert 'st.error("VBTS CSV dosyası bulunamadı:' not in section
    assert "Manuel VBTS kaynağı kullanılamıyor" not in section
'''

    new = '''    next_def = source.find("\ndef ", start + len(marker))
    assert next_def >= 0

    section = source[start:next_def]

    assert 'st.error("VBTS CSV dosyası bulunamadı:' not in section
    assert "Manuel VBTS kaynağı kullanılamıyor" not in section
'''

    if old not in source:
        fail("Eski test kesiti bulunamadı.")

    updated = source.replace(old, new, 1)
    compile(updated, str(TARGET), "exec")
    TARGET.write_text(updated, encoding="utf-8", newline="\n")

    print("Sprint-41 VBTS test kapsamı düzeltildi.")
    print(f"Yedek: {BACKUP}")


if __name__ == "__main__":
    main()
