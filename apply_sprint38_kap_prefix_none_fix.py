from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / 'backend' / 'app' / 'compliance' / 'kap_settings.py'
BACKUP = TARGET.with_suffix('.py.sprint38-prefix-none.bak')

def fail(message: str) -> None:
    print(f'HATA: {message}')
    raise SystemExit(1)

def main() -> None:
    if not TARGET.exists():
        fail(f'Dosya bulunamadı: {TARGET}')

    source = TARGET.read_text(encoding='utf-8')
    shutil.copy2(TARGET, BACKUP)

    old = '        normalized_api_key_prefix = self.api_key_prefix.strip()\n'
    new = (
        '        normalized_api_key_prefix = (\n'
        '            self.api_key_prefix.strip()\n'
        '            if self.api_key_prefix is not None\n'
        '            else (\n'
        '                "Bearer"\n'
        '                if normalized_api_key_header.lower() == "authorization"\n'
        '                else ""\n'
        '            )\n'
        '        )\n'
    )

    if old in source:
        source = source.replace(old, new, 1)
    elif new not in source:
        fail('api_key_prefix normalizasyon satırı bulunamadı.')

    compile(source, str(TARGET), 'exec')
    TARGET.write_text(source, encoding='utf-8', newline='\n')

    print('KapSettings api_key_prefix None güvenliği düzeltildi.')
    print(f'Yedek: {BACKUP}')

if __name__ == '__main__':
    main()
