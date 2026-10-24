from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "backend" / "dashboard.py"
SOURCE = ROOT / "dashboard.sprint46.py"
BACKUP = TARGET.with_suffix(".py.sprint46-vbts-integrity.bak")


def main() -> None:
    if not TARGET.exists():
        raise SystemExit(f"HATA: Dosya bulunamadı: {TARGET}")
    if not SOURCE.exists():
        raise SystemExit(f"HATA: Paket dashboard dosyası bulunamadı: {SOURCE}")

    shutil.copy2(TARGET, BACKUP)
    source = SOURCE.read_text(encoding="utf-8")
    compile(source, str(TARGET), "exec")
    TARGET.write_text(source, encoding="utf-8", newline="\n")
    print("Sprint-46 dashboard güncellemesi uygulandı.")
    print(f"Yedek: {BACKUP}")


if __name__ == "__main__":
    main()
