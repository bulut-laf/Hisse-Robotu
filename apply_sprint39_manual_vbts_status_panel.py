from __future__ import annotations

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "backend" / "dashboard.py"
BACKUP = TARGET.with_suffix(".py.sprint39-manual-vbts-status-panel.bak")


def fail(message: str) -> None:
    print(f"HATA: {message}")
    raise SystemExit(1)


def ensure_imports(source: str) -> str:
    if "from pathlib import Path\n" not in source:
        anchor = "import os\n"
        if anchor not in source:
            fail("Path importu için ekleme noktası bulunamadı.")
        source = source.replace(
            anchor,
            anchor + "from pathlib import Path\n",
            1,
        )

    if "from datetime import datetime, timezone\n" not in source:
        anchor = "from pathlib import Path\n"
        source = source.replace(
            anchor,
            anchor + "from datetime import datetime, timezone\n",
            1,
        )

    imports = (
        "from backend.app.compliance.dashboard_manual_vbts import (\n"
        "    DashboardManualVbtsError,\n"
        "    load_dashboard_vbts_dataset,\n"
        ")\n"
    )
    if imports not in source:
        anchor = (
            "from backend.app.compliance."
            "dashboard_market_scanner_source_factory import (\n"
        )
        pos = source.find(anchor)
        if pos < 0:
            fail("Manuel VBTS importu için ekleme noktası bulunamadı.")
        source = source[:pos] + imports + source[pos:]

    return source


def add_function(source: str) -> str:
    if "def manuel_vbts_durum_paneli_goster()" in source:
        return source

    function_text = 'def manuel_vbts_durum_paneli_goster() -> None:\n    """Manuel VBTS CSV kaynağının güncellik ve içerik özetini gösterir."""\n\n    csv_path_raw = os.getenv("HISSE_ROBOTU_VBTS_CSV_PATH", "").strip()\n\n    if not csv_path_raw:\n        st.info("VBTS CSV dosyası tanımlı değil.")\n        return\n\n    csv_path = Path(csv_path_raw).expanduser()\n\n    if not csv_path.exists() or not csv_path.is_file():\n        st.warning(f"VBTS CSV dosyası bulunamadı: {csv_path}")\n        return\n\n    try:\n        now = datetime.now(timezone.utc)\n        dataset = load_dashboard_vbts_dataset(\n            now_provider=lambda: now,\n        )\n        modified_at = datetime.fromtimestamp(\n            csv_path.stat().st_mtime,\n            tz=timezone.utc,\n        )\n    except DashboardManualVbtsError as exc:\n        st.warning(f"VBTS CSV dosyası kullanılamıyor: {exc}")\n        return\n\n    st.markdown("#### Manuel VBTS Kaynağı")\n    st.caption(f"VBTS CSV dosyası: {csv_path}")\n    st.caption(\n        "Son güncelleme: "\n        + modified_at.astimezone().strftime("%d.%m.%Y %H:%M:%S")\n    )\n    st.caption(f"Kayıt sayısı: {dataset.status.record_count}")\n\n'
    anchor = "def kap_vbts_durum_karti_goster() -> bool:\n"
    if anchor not in source:
        fail("Durum paneli fonksiyonu için ekleme noktası bulunamadı.")

    return source.replace(anchor, function_text + anchor, 1)


def add_call(source: str) -> str:
    call = "    manuel_vbts_durum_paneli_goster()\n"
    if call in source:
        return source

    candidates = (
        "def bist_toplu_tarama_formu() -> None:\n",
        "def toplu_tarama_formu() -> None:\n",
    )

    for anchor in candidates:
        if anchor in source:
            marker = anchor + "    kap_vbts_durum_karti_goster()\n"
            if marker in source:
                return source.replace(
                    marker,
                    marker + call,
                    1,
                )
            return source.replace(anchor, anchor + call, 1)

    fail("Toplu Tarama formu bulunamadı.")
    return source


def main() -> None:
    if not TARGET.exists():
        fail(f"Dosya bulunamadı: {TARGET}")

    source = TARGET.read_text(encoding="utf-8")
    shutil.copy2(TARGET, BACKUP)

    updated = ensure_imports(source)
    updated = add_function(updated)
    updated = add_call(updated)

    compile(updated, str(TARGET), "exec")
    TARGET.write_text(updated, encoding="utf-8", newline="\n")

    print("Sprint-39 manuel VBTS durum paneli eklendi.")
    print(f"Yedek: {BACKUP}")


if __name__ == "__main__":
    main()
