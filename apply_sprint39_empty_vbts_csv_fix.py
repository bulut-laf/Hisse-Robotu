from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / 'backend' / 'app' / 'compliance' / 'manual_vbts_csv.py'
BACKUP = TARGET.with_suffix('.py.sprint39-empty-csv.bak')

def fail(message: str) -> None:
    print(f'HATA: {message}')
    raise SystemExit(1)

def main() -> None:
    if not TARGET.exists():
        fail(f'Dosya bulunamadı: {TARGET}')

    source = TARGET.read_text(encoding='utf-8')
    shutil.copy2(TARGET, BACKUP)

    old = (
        '            for row_number, row in enumerate(reader, start=2):\n'
        '                measures.append(\n'
        '                    _row_to_measure(\n'
        '                        row,\n'
        '                        row_number=row_number,\n'
        '                    )\n'
        '                )\n'
    )
    new = old + (
        '\n            if not measures:\n'
        '                raise ManualVbtsCsvError(\n'
        '                    "VBTS CSV dosyası kayıt içermiyor."\n'
        '                )\n'
    )

    if old in source and 'VBTS CSV dosyası kayıt içermiyor.' not in source:
        source = source.replace(old, new, 1)
    elif 'VBTS CSV dosyası kayıt içermiyor.' not in source:
        fail('CSV kayıt döngüsü beklenen biçimde bulunamadı.')

    compile(source, str(TARGET), 'exec')
    TARGET.write_text(source, encoding='utf-8', newline='\n')

    print('Boş VBTS CSV güvenlik kontrolü eklendi.')
    print(f'Yedek: {BACKUP}')

if __name__ == '__main__':
    main()
