from __future__ import annotations

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "backend" / "dashboard.py"
BACKUP = TARGET.with_suffix(".py.sprint42-confirmation-text.bak")


def fail(message: str) -> None:
    print(f"HATA: {message}")
    raise SystemExit(1)


def main() -> None:
    if not TARGET.exists():
        fail(f"Dosya bulunamadı: {TARGET}")

    source = TARGET.read_text(encoding="utf-8")
    shutil.copy2(TARGET, BACKUP)

    old = "Kaydı resmî KAP bildirimiyle doğruladım."
    new = "Resmî KAP bildirimiyle doğruladım."

    if old in source:
        source = source.replace(old, new, 1)
    elif new not in source:
        fail("VBTS KAP doğrulama metni bulunamadı.")

    compile(source, str(TARGET), "exec")
    TARGET.write_text(source, encoding="utf-8", newline="\n")

    print("Sprint-42 KAP doğrulama metni düzeltildi.")
    print(f"Yedek: {BACKUP}")


if __name__ == "__main__":
    main()
