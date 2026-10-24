from __future__ import annotations

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "backend" / "dashboard.py"
BACKUP = TARGET.with_suffix(".py.sprint41-vbts-duplicate-message.bak")


def fail(message: str) -> None:
    print(f"HATA: {message}")
    raise SystemExit(1)


def main() -> None:
    if not TARGET.exists():
        fail(f"Dosya bulunamadı: {TARGET}")

    source = TARGET.read_text(encoding="utf-8")
    shutil.copy2(TARGET, BACKUP)

    marker = "def manuel_vbts_durum_paneli_goster"
    start = source.find(marker)
    if start < 0:
        fail("Manuel VBTS durum paneli fonksiyonu bulunamadı.")

    next_def = source.find("\ndef ", start + len(marker))
    if next_def < 0:
        fail("Manuel VBTS durum panelinin bitişi bulunamadı.")

    old_block = source[start:next_def]

    new_block = '''def manuel_vbts_durum_paneli_goster() -> None:
    """Manuel VBTS CSV kaynağının özet durumunu tekrar üretmeden gösterir."""

    csv_path_raw = os.getenv("HISSE_ROBOTU_VBTS_CSV_PATH", "").strip()

    if not csv_path_raw:
        st.info("VBTS CSV durumu: Dosya yolu tanımlı değil")
        return

    csv_path = Path(csv_path_raw)

    if not csv_path.exists():
        st.info("VBTS CSV durumu: Dosya bulunamadı")
        st.caption(f"Beklenen konum: {csv_path}")
        return

    try:
        dataset = load_dashboard_vbts_dataset()
    except DashboardManualVbtsError:
        st.info("VBTS CSV durumu: Dosya doğrulanamadı")
        st.caption(f"Beklenen konum: {csv_path}")
        return

    modified_at = datetime.fromtimestamp(
        csv_path.stat().st_mtime,
        tz=timezone.utc,
    ).astimezone()

    st.caption(f"VBTS CSV dosyası: {csv_path}")
    st.caption(
        "Son güncelleme: "
        + modified_at.strftime("%Y-%m-%d %H:%M:%S")
    )
    st.caption(f"Kayıt sayısı: {len(dataset.measures)}")

'''

    updated = source[:start] + new_block + source[next_def + 1:]
    compile(updated, str(TARGET), "exec")
    TARGET.write_text(updated, encoding="utf-8", newline="\n")

    print("Sprint-41 VBTS yinelenen mesaj düzeltmesi uygulandı.")
    print(f"Yedek: {BACKUP}")


if __name__ == "__main__":
    main()
