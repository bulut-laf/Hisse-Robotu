from __future__ import annotations

from pathlib import Path
import shutil
import sys


PROJECT_ROOT = Path(__file__).resolve().parent
DASHBOARD = PROJECT_ROOT / "backend" / "dashboard.py"
BACKUP = PROJECT_ROOT / "backend" / "dashboard.py.sprint38.bak"


def fail(message: str) -> None:
    print(f"HATA: {message}")
    raise SystemExit(1)


def add_imports(source: str) -> str:
    if "import requests\n" not in source:
        anchor = "from __future__ import annotations\n"
        if anchor in source:
            source = source.replace(
                anchor,
                anchor + "\nimport requests\n",
                1,
            )
        else:
            source = "import requests\n" + source

    factory_import = (
        "from backend.app.compliance.dashboard_market_scanner_factory import (\n"
        "    DashboardMarketScannerFactoryError,\n"
        "    build_protected_market_scanner,\n"
        ")\n"
    )
    kap_import = (
        "from backend.app.compliance.kap_factory import "
        "build_kap_vbts_service\n"
    )

    if factory_import not in source:
        marker = "from backend.app.analysis.momentum_discovery import (\n"
        if marker not in source:
            fail("Import ekleme noktası bulunamadı.")
        source = source.replace(
            marker,
            factory_import + kap_import + marker,
            1,
        )

    return source


def replace_service_call(source: str) -> str:
    old = """            sonuc = BistMarketScannerService().calistir(
                istek,
                ilerleme_bildirimi=ilerleme_bildir,
            )
"""
    new = """            kap_vbts_service = build_kap_vbts_service(
                http_get=requests.get,
            )
            tarama_servisi = build_protected_market_scanner(
                kap_vbts_service=kap_vbts_service,
            )
            sonuc = tarama_servisi.calistir(
                istek,
                ilerleme_bildirimi=ilerleme_bildir,
            )
"""

    if new in source:
        return source

    if old not in source:
        fail("Doğrudan BistMarketScannerService çağrısı bulunamadı.")

    return source.replace(old, new, 1)


def extend_error_handling(source: str) -> str:
    old = """    except (ValueError, TypeError, MarketScannerError) as hata:
"""
    new = """    except (
        ValueError,
        TypeError,
        MarketScannerError,
        DashboardMarketScannerFactoryError,
    ) as hata:
"""

    if new in source:
        return source

    if old not in source:
        fail("Toplu tarama hata yakalama satırı bulunamadı.")

    return source.replace(old, new, 1)


def main() -> None:
    if not DASHBOARD.exists():
        fail(f"Dosya bulunamadı: {DASHBOARD}")

    source = DASHBOARD.read_text(encoding="utf-8")

    shutil.copy2(DASHBOARD, BACKUP)

    updated = add_imports(source)
    updated = replace_service_call(updated)
    updated = extend_error_handling(updated)

    compile(updated, str(DASHBOARD), "exec")
    DASHBOARD.write_text(updated, encoding="utf-8", newline="\n")

    print("Sprint-38 dashboard KAP/VBTS bağlantısı uygulandı.")
    print(f"Yedek: {BACKUP}")
    print(
        "Şimdi çalıştırın: "
        "python -m pytest .\\backend\\tests\\test_dashboard_kap_wiring.py -q"
    )


if __name__ == "__main__":
    main()
