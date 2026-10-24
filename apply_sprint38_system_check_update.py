from __future__ import annotations

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent
SYSTEM_CHECK = ROOT / "backend" / "app" / "diagnostics" / "system_check.py"
TEST_FILE = ROOT / "backend" / "tests" / "test_system_check.py"


def fail(message: str) -> None:
    print(f"HATA: {message}")
    raise SystemExit(1)


def backup(path: Path) -> None:
    shutil.copy2(
        path,
        path.with_suffix(path.suffix + ".sprint38-system-check.bak"),
    )


def patch_system_check() -> None:
    if not SYSTEM_CHECK.exists():
        fail(f"Dosya bulunamadı: {SYSTEM_CHECK}")

    source = SYSTEM_CHECK.read_text(encoding="utf-8")
    backup(SYSTEM_CHECK)

    source = source.replace(
        'SISTEM_KONTROL_SURUMU = "Sprint-37"',
        'SISTEM_KONTROL_SURUMU = "Sprint-38"',
        1,
    )

    call_line = "    kontroller.append(_kap_vbts_guvenlik_kontrolu())\n"
    if call_line not in source:
        anchor = "    kontroller.append(_canli_analiz_zinciri_kontrolu())\n"
        if anchor not in source:
            fail("KAP/VBTS kontrol çağrısı için ekleme noktası bulunamadı.")
        source = source.replace(anchor, anchor + "\n" + call_line, 1)

    function_text = 'def _kap_vbts_guvenlik_kontrolu() -> SystemCheckItem:\n    basla = perf_counter()\n\n    import os\n\n    from backend.app.compliance.kap_settings import KapSettings\n\n    degiskenler = (\n        "HISSE_ROBOTU_KAP_BASE_URL",\n        "HISSE_ROBOTU_KAP_API_KEY",\n        "HISSE_ROBOTU_KAP_TIMEOUT_SECONDS",\n        "HISSE_ROBOTU_KAP_ENDPOINT_PATH",\n        "HISSE_ROBOTU_KAP_API_KEY_HEADER",\n        "HISSE_ROBOTU_KAP_COLLECTION_KEY",\n        "HISSE_ROBOTU_KAP_API_KEY_PREFIX",\n    )\n    onceki = {ad: os.environ.get(ad) for ad in degiskenler}\n\n    try:\n        for ad in degiskenler:\n            os.environ.pop(ad, None)\n\n        guvenli_durdu = False\n        try:\n            KapSettings.from_environment()\n        except ValueError as exc:\n            guvenli_durdu = "KAP temel adresi" in str(exc)\n\n        os.environ["HISSE_ROBOTU_KAP_BASE_URL"] = "https://kap.test/api"\n        os.environ["HISSE_ROBOTU_KAP_API_KEY"] = "test-anahtari"\n        os.environ["HISSE_ROBOTU_KAP_ENDPOINT_PATH"] = "disclosures"\n        os.environ["HISSE_ROBOTU_KAP_API_KEY_HEADER"] = "X-API-KEY"\n        os.environ["HISSE_ROBOTU_KAP_COLLECTION_KEY"] = "disclosures"\n\n        ayarlar = KapSettings.from_environment()\n        yapilandirma_dogru = (\n            ayarlar.endpoint_path == "disclosures"\n            and ayarlar.api_key_header == "X-API-KEY"\n            and ayarlar.collection_key == "disclosures"\n            and ayarlar.api_key_prefix == ""\n        )\n\n        uygun = guvenli_durdu and yapilandirma_dogru\n        durum = BASARILI if uygun else BASARISIZ\n        aciklama = (\n            "Eksik ayarlarda güvenli durdurma ve sözleşmeye bağlı "\n            "endpoint, başlık ve yanıt anahtarı yapılandırması doğrulandı."\n            if uygun\n            else "KAP/VBTS güvenlik yapılandırması doğrulanamadı."\n        )\n\n        return SystemCheckItem(\n            ad="KAP/VBTS güvenli yapılandırma",\n            durum=durum,\n            aciklama=aciklama,\n            kritik=True,\n            sure_ms=(perf_counter() - basla) * 1000,\n        )\n    except Exception as exc:\n        return SystemCheckItem(\n            ad="KAP/VBTS güvenli yapılandırma",\n            durum=BASARISIZ,\n            aciklama=f"KAP/VBTS kontrolü çalıştırılamadı: {exc}",\n            kritik=True,\n            sure_ms=(perf_counter() - basla) * 1000,\n        )\n    finally:\n        for ad, deger in onceki.items():\n            if deger is None:\n                os.environ.pop(ad, None)\n            else:\n                os.environ[ad] = deger\n\n'
    if "def _kap_vbts_guvenlik_kontrolu()" not in source:
        anchor = "def _veri_tazeligi_kilidi_kontrolu() -> SystemCheckItem:\n"
        if anchor not in source:
            fail("KAP/VBTS kontrol fonksiyonu için ekleme noktası bulunamadı.")
        source = source.replace(anchor, function_text + anchor, 1)

    compile(source, str(SYSTEM_CHECK), "exec")
    SYSTEM_CHECK.write_text(source, encoding="utf-8", newline="\n")


def patch_tests() -> None:
    if not TEST_FILE.exists():
        fail(f"Dosya bulunamadı: {TEST_FILE}")

    source = TEST_FILE.read_text(encoding="utf-8")
    backup(TEST_FILE)

    source = source.replace(
        'assert rapor.surum == "Sprint-37"',
        'assert rapor.surum == "Sprint-38"',
        1,
    )

    target = '    assert rapor.surum == "Sprint-38"\n'
    addition = (
        '    assert any(\n'
        '        item.ad == "KAP/VBTS güvenli yapılandırma"\n'
        '        for item in rapor.kontroller\n'
        '    )\n'
    )
    if addition not in source:
        if target not in source:
            fail("Sprint-38 test beklentisi bulunamadı.")
        source = source.replace(target, target + addition, 1)

    compile(source, str(TEST_FILE), "exec")
    TEST_FILE.write_text(source, encoding="utf-8", newline="\n")


def main() -> None:
    patch_system_check()
    patch_tests()
    print("Sprint-38 sistem kontrolü güncellendi.")


if __name__ == "__main__":
    main()
