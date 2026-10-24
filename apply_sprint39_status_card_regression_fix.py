from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / 'backend' / 'tests' / 'test_dashboard_kap_status_card.py'
BACKUP = TARGET.with_suffix('.py.sprint39-status-card-regression.bak')

def fail(message: str) -> None:
    print(f'HATA: {message}')
    raise SystemExit(1)

def main() -> None:
    if not TARGET.exists():
        fail(f'Dosya bulunamadı: {TARGET}')

    source = TARGET.read_text(encoding='utf-8')
    shutil.copy2(TARGET, BACKUP)

    old = (
        '    assert "KAP/VBTS koruması" in source\n'
        '    assert "Toplu tarama kilitli" in source\n'
        '    assert "abonelik" in source.lower()\n'
    )
    new = (
        '    assert "VBTS veri kaynağı seçilmedi" in source\n'
        '    assert "Toplu tarama kilitli" in source\n'
        '    assert "Manuel VBTS koruması aktif" in source\n'
    )

    if old in source:
        source = source.replace(old, new, 1)
    elif new not in source:
        fail('Eski durum kartı beklentisi bulunamadı.')

    compile(source, str(TARGET), 'exec')
    TARGET.write_text(source, encoding='utf-8', newline='\n')

    print('Sprint-39 durum kartı testi yeni kaynak akışına uyarlandı.')
    print(f'Yedek: {BACKUP}')

if __name__ == '__main__':
    main()
