from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / 'backend' / 'app' / 'compliance' / 'kap_settings.py'
BACKUP = TARGET.with_suffix('.py.sprint38-auth-prefix.bak')

def fail(message: str) -> None:
    print(f'HATA: {message}')
    raise SystemExit(1)

def main() -> None:
    if not TARGET.exists():
        fail(f'Dosya bulunamadı: {TARGET}')

    source = TARGET.read_text(encoding='utf-8')
    shutil.copy2(TARGET, BACKUP)

    old = (
        '            api_key_prefix=os.getenv(\n'
        '                "HISSE_ROBOTU_KAP_API_KEY_PREFIX",\n'
        '                "",\n'
        '            ),\n'
    )
    new = (
        '            api_key_prefix=os.getenv(\n'
        '                "HISSE_ROBOTU_KAP_API_KEY_PREFIX",\n'
        '            ),\n'
    )

    if old in source:
        source = source.replace(old, new, 1)
    elif new not in source:
        fail('API anahtar öneki ayarı beklenen biçimde bulunamadı.')

    compile(source, str(TARGET), 'exec')
    TARGET.write_text(source, encoding='utf-8', newline='\n')

    print('Authorization varsayılan Bearer davranışı düzeltildi.')
    print(f'Yedek: {BACKUP}')

if __name__ == '__main__':
    main()
