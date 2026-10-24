from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / 'backend' / 'tests' / 'test_dashboard_kap_wiring.py'
BACKUP = TARGET.with_suffix('.py.sprint39-regression.bak')

def fail(message: str) -> None:
    print(f'HATA: {message}')
    raise SystemExit(1)

def main() -> None:
    if not TARGET.exists():
        fail(f'Dosya bulunamadı: {TARGET}')

    source = TARGET.read_text(encoding='utf-8')
    shutil.copy2(TARGET, BACKUP)

    source = source.replace(
        'def test_dashboard_korumali_tarama_fabrikasini_import_eder() -> None:',
        'def test_dashboard_vbts_kaynak_fabrikasini_import_eder() -> None:',
        1,
    )
    source = source.replace(
        'backend.app.compliance.dashboard_market_scanner_factory',
        'backend.app.compliance.dashboard_market_scanner_source_factory',
    )
    source = source.replace(
        'build_protected_market_scanner',
        'build_dashboard_market_scanner',
    )
    source = source.replace(
        'DashboardMarketScannerFactoryError',
        'DashboardMarketScannerSourceError',
    )
    source = source.replace(
        'def test_dashboard_toplu_taramada_korumali_fabrikayi_kullanir() -> None:',
        'def test_dashboard_toplu_taramada_vbts_kaynak_fabrikasini_kullanir() -> None:',
        1,
    )

    compile(source, str(TARGET), 'exec')
    TARGET.write_text(source, encoding='utf-8', newline='\n')

    print('Eski dashboard KAP wiring testi Sprint-39 akışına uyarlandı.')
    print(f'Yedek: {BACKUP}')

if __name__ == '__main__':
    main()
