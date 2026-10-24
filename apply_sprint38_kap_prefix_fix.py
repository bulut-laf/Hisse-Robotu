from __future__ import annotations

from pathlib import Path
import shutil


PROJECT_ROOT = Path(__file__).resolve().parent
TARGET = PROJECT_ROOT / "backend" / "app" / "compliance" / "kap_http_source.py"
BACKUP = TARGET.with_suffix(".py.sprint38-prefix.bak")


def fail(message: str) -> None:
    print(f"HATA: {message}")
    raise SystemExit(1)


def main() -> None:
    if not TARGET.exists():
        fail(f"Dosya bulunamadı: {TARGET}")

    source = TARGET.read_text(encoding="utf-8")
    shutil.copy2(TARGET, BACKUP)

    old_signature = '        api_key_prefix: str = "Bearer",\n'
    new_signature = '        api_key_prefix: str | None = None,\n'

    if old_signature in source:
        source = source.replace(
            old_signature,
            new_signature,
            1,
        )
    elif new_signature not in source:
        fail("api_key_prefix imzası beklenen biçimde bulunamadı.")

    old_normalization = (
        "        normalized_api_key_prefix = api_key_prefix.strip()\n"
    )
    new_normalization = (
        "        normalized_api_key_prefix = (\n"
        "            api_key_prefix.strip()\n"
        "            if api_key_prefix is not None\n"
        "            else (\n"
        '                "Bearer"\n'
        '                if normalized_api_key_header.lower() == "authorization"\n'
        '                else ""\n'
        "            )\n"
        "        )\n"
    )

    if old_normalization in source:
        source = source.replace(
            old_normalization,
            new_normalization,
            1,
        )
    elif new_normalization not in source:
        fail("api_key_prefix normalizasyonu bulunamadı.")

    compile(source, str(TARGET), "exec")
    TARGET.write_text(source, encoding="utf-8", newline="\n")

    print("KAP API anahtar öneki düzeltildi.")
    print(f"Yedek: {BACKUP}")


if __name__ == "__main__":
    main()
