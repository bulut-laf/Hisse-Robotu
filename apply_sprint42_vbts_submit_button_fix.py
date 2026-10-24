from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "backend" / "dashboard.py"
BACKUP = TARGET.with_suffix(".py.sprint42-submit-button.bak")


def fail(message: str) -> None:
    print(f"HATA: {message}")
    raise SystemExit(1)


def main() -> None:
    if not TARGET.exists():
        fail(f"Dosya bulunamadı: {TARGET}")

    source = TARGET.read_text(encoding="utf-8")
    shutil.copy2(TARGET, BACKUP)

    if "                disabled=not resmi_onay,\n" in source:
        source = source.replace(
            "                disabled=not resmi_onay,\n",
            "",
            1,
        )

    marker = "        if ekle:\n            try:\n                record = build_vbts_record(\n"
    replacement = (
        "        if ekle:\n"
        "            if not resmi_onay:\n"
        "                st.error(\n"
        "                    \"VBTS kaydı eklemek için resmî KAP bildirimiyle \"\n"
        "                    \"doğrulama onayı verilmelidir.\"\n"
        "                )\n"
        "                return\n\n"
        "            try:\n"
        "                record = build_vbts_record(\n"
    )

    if "VBTS kaydı eklemek için resmî KAP bildirimiyle" not in source:
        if marker not in source:
            fail("VBTS gönderim doğrulama noktası bulunamadı.")
        source = source.replace(marker, replacement, 1)

    compile(source, str(TARGET), "exec")
    TARGET.write_text(source, encoding="utf-8", newline="\n")

    print("Sprint-42 VBTS ekleme düğmesi düzeltildi.")
    print(f"Yedek: {BACKUP}")


if __name__ == "__main__":
    main()
