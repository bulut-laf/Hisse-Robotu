from __future__ import annotations

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "backend" / "dashboard.py"
BACKUP = TARGET.with_suffix(".py.sprint39-source-aware-vbts-status.bak")


def fail(message: str) -> None:
    print(f"HATA: {message}")
    raise SystemExit(1)


def main() -> None:
    if not TARGET.exists():
        fail(f"Dosya bulunamadı: {TARGET}")

    source = TARGET.read_text(encoding="utf-8")
    shutil.copy2(TARGET, BACKUP)

    start_marker = "def kap_vbts_durum_karti_goster() -> bool:\n"
    end_marker = "def bist_toplu_tarama_sonucu_goster("

    start = source.find(start_marker)
    end = source.find(end_marker, start)

    if start < 0 or end < 0:
        fail("Mevcut KAP/VBTS durum kartı fonksiyonu bulunamadı.")

    new_function = 'def kap_vbts_durum_karti_goster() -> bool:\n    """Seçilen VBTS veri kaynağının kullanılabilirlik durumunu gösterir."""\n\n    source_name = os.getenv("HISSE_ROBOTU_VBTS_SOURCE", "").strip().lower()\n\n    if not source_name:\n        st.error("VBTS veri kaynağı seçilmedi — Toplu tarama kilitli.")\n        st.caption(\n            "HISSE_ROBOTU_VBTS_SOURCE ortam değişkeni tanımlanmalıdır. "\n            "Desteklenen kaynak: manual_csv."\n        )\n        return False\n\n    if source_name == "manual_csv":\n        csv_path_raw = os.getenv("HISSE_ROBOTU_VBTS_CSV_PATH", "").strip()\n\n        if not csv_path_raw:\n            st.error(\n                "Manuel VBTS kaynağı seçildi — CSV dosyası tanımlı değil."\n            )\n            st.caption(\n                "HISSE_ROBOTU_VBTS_CSV_PATH ortam değişkeni "\n                "güncel ve doğrulanmış dosyayı göstermelidir."\n            )\n            return False\n\n        try:\n            load_dashboard_vbts_dataset()\n        except DashboardManualVbtsError as exc:\n            st.error("Manuel VBTS kaynağı kullanılamıyor — Toplu tarama kilitli.")\n            st.caption(str(exc))\n            return False\n\n        st.success("Manuel VBTS koruması aktif.")\n        st.caption(\n            "Toplu tarama güncel ve doğrulanmış manuel VBTS CSV "\n            "filtresiyle çalışacaktır."\n        )\n        return True\n\n    st.error(f"VBTS veri kaynağı desteklenmiyor: {source_name}")\n    st.caption("Toplu tarama kilitli.")\n    return False\n\n'
    updated = source[:start] + new_function + source[end:]

    compile(updated, str(TARGET), "exec")
    TARGET.write_text(updated, encoding="utf-8", newline="\n")

    print("Sprint-39 kaynak duyarlı VBTS durum kartı uygulandı.")
    print(f"Yedek: {BACKUP}")


if __name__ == "__main__":
    main()
