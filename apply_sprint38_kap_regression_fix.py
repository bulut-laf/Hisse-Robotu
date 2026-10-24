from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
SETTINGS = ROOT / 'backend' / 'app' / 'compliance' / 'kap_settings.py'
TEST_SETTINGS = ROOT / 'backend' / 'tests' / 'test_kap_settings.py'
TEST_FACTORY = ROOT / 'backend' / 'tests' / 'test_kap_factory.py'

def fail(message: str) -> None:
    print(f'HATA: {message}')
    raise SystemExit(1)

def backup(path: Path) -> None:
    shutil.copy2(path, path.with_suffix(path.suffix + '.sprint38-regression.bak'))

def patch_validation_order() -> None:
    if not SETTINGS.exists():
        fail(f'Dosya bulunamadı: {SETTINGS}')
    source = SETTINGS.read_text(encoding='utf-8')
    backup(SETTINGS)
    start = source.find('        contract_values = {')
    try_pos = source.find('        try:\n            timeout_seconds = float(timeout_raw)', start)
    end_marker = '            ) from exc\n'
    end = source.find(end_marker, try_pos)
    if start < 0 or try_pos < 0 or end < 0:
        fail('KapSettings doğrulama blokları bulunamadı.')
    end += len(end_marker)
    contract_block = source[start:try_pos]
    timeout_block = source[try_pos:end]
    updated = source[:start] + timeout_block + '\n' + contract_block + source[end:]
    compile(updated, str(SETTINGS), 'exec')
    SETTINGS.write_text(updated, encoding='utf-8', newline='\n')

def add_contract_env_to_test(source: str, test_name: str) -> str:
    marker = f'def {test_name}('
    start = source.find(marker)
    if start < 0:
        fail(f'Test bulunamadı: {test_name}')
    next_test = source.find('\ndef test_', start + len(marker))
    end = len(source) if next_test < 0 else next_test
    block = source[start:end]
    if 'HISSE_ROBOTU_KAP_ENDPOINT_PATH' in block:
        return source
    first_setenv = block.find('    monkeypatch.setenv(')
    if first_setenv < 0:
        fail(f'Ortam ayarı ekleme noktası bulunamadı: {test_name}')
    absolute = start + first_setenv
    insertion_point = source.find('\n    )', absolute)
    if insertion_point < 0:
        fail(f'setenv kapanışı bulunamadı: {test_name}')
    insertion_point += len('\n    )')
    extra = (
        "\n    monkeypatch.setenv(\n"
        "        'HISSE_ROBOTU_KAP_ENDPOINT_PATH',\n"
        "        'notifications',\n"
        "    )\n"
        "    monkeypatch.setenv(\n"
        "        'HISSE_ROBOTU_KAP_API_KEY_HEADER',\n"
        "        'Authorization',\n"
        "    )\n"
        "    monkeypatch.setenv(\n"
        "        'HISSE_ROBOTU_KAP_COLLECTION_KEY',\n"
        "        'notifications',\n"
        "    )"
    )
    return source[:insertion_point] + extra + source[insertion_point:]

def patch_tests() -> None:
    for path in (TEST_SETTINGS, TEST_FACTORY):
        if not path.exists():
            fail(f'Dosya bulunamadı: {path}')
        backup(path)
    settings_source = TEST_SETTINGS.read_text(encoding='utf-8')
    settings_source = add_contract_env_to_test(settings_source, 'test_kap_ayarlari_ortam_degiskenlerinden_yuklenir')
    settings_source = add_contract_env_to_test(settings_source, 'test_kap_api_anahtari_istege_bagli_olabilir')
    compile(settings_source, str(TEST_SETTINGS), 'exec')
    TEST_SETTINGS.write_text(settings_source, encoding='utf-8', newline='\n')
    factory_source = TEST_FACTORY.read_text(encoding='utf-8')
    factory_source = add_contract_env_to_test(factory_source, 'test_kap_factory_ortam_ayarlarindan_servis_olusturur')
    compile(factory_source, str(TEST_FACTORY), 'exec')
    TEST_FACTORY.write_text(factory_source, encoding='utf-8', newline='\n')

def main() -> None:
    patch_validation_order()
    patch_tests()
    print('Sprint-38 KAP regresyon uyumluluğu uygulandı.')

if __name__ == '__main__':
    main()
