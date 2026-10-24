from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / 'backend' / 'dashboard.py'
BACKUP = TARGET.with_suffix('.py.sprint39-manual-vbts-wiring.bak')

def fail(message: str) -> None:
    print(f'HATA: {message}')
    raise SystemExit(1)

def main() -> None:
    if not TARGET.exists():
        fail(f'Dosya bulunamadı: {TARGET}')

    source = TARGET.read_text(encoding='utf-8')
    shutil.copy2(TARGET, BACKUP)

    old_import = (
        'from backend.app.compliance.dashboard_market_scanner_factory import (\n'
        '    DashboardMarketScannerFactoryError,\n'
        '    build_protected_market_scanner,\n'
        ')\n'
    )
    new_import = (
        'from backend.app.compliance.dashboard_market_scanner_source_factory import (\n'
        '    DashboardMarketScannerSourceError,\n'
        '    build_dashboard_market_scanner,\n'
        ')\n'
    )

    if old_import in source:
        source = source.replace(old_import, new_import, 1)
    elif new_import not in source:
        fail('Dashboard VBTS kaynak fabrikası import bloğu bulunamadı.')

    old_block = (
        '            kap_vbts_service = build_kap_vbts_service(\n'
        '                http_get=requests.get,\n'
        '            )\n'
        '            tarama_servisi = build_protected_market_scanner(\n'
        '                kap_vbts_service=kap_vbts_service,\n'
        '            )\n'
    )
    new_block = (
        '            tarama_servisi = build_dashboard_market_scanner()\n'
    )

    if old_block in source:
        source = source.replace(old_block, new_block, 1)
    elif new_block not in source:
        fail('Eski KAP/VBTS servis kurulum bloğu bulunamadı.')

    source = source.replace(
        'DashboardMarketScannerFactoryError,',
        'DashboardMarketScannerSourceError,',
        1,
    )

    compile(source, str(TARGET), 'exec')
    TARGET.write_text(source, encoding='utf-8', newline='\n')

    print('Sprint-39 dashboard manuel VBTS bağlantısı uygulandı.')
    print(f'Yedek: {BACKUP}')

if __name__ == '__main__':
    main()
