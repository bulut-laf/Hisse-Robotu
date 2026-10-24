from __future__ import annotations

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "backend" / "dashboard.py"
BACKUP = TARGET.with_suffix(".py.sprint39-kap-status-card.bak")


def fail(message: str) -> None:
    print(f"HATA: {message}")
    raise SystemExit(1)


def ensure_os_import(source: str) -> str:
    if "\nimport os\n" in source or source.startswith("import os\n"):
        return source

    anchor = "from __future__ import annotations\n"
    if anchor in source:
        return source.replace(anchor, anchor + "\nimport os\n", 1)

    return "import os\n" + source


def add_status_function(source: str) -> str:
    if "def kap_vbts_durum_karti_goster()" in source:
        return source

    function_text = 'def kap_vbts_durum_karti_goster() -> bool:\n    """KAP/VBTS korumasının kullanılabilirlik durumunu gösterir."""\n\n    gerekli_ayarlar = {\n        "HISSE_ROBOTU_KAP_BASE_URL": "temel adres",\n        "HISSE_ROBOTU_KAP_ENDPOINT_PATH": "servis yolu",\n        "HISSE_ROBOTU_KAP_API_KEY_HEADER": "API anahtar başlığı",\n        "HISSE_ROBOTU_KAP_COLLECTION_KEY": "yanıt liste anahtarı",\n    }\n\n    eksik_ayarlar = [\n        aciklama\n        for degisken, aciklama in gerekli_ayarlar.items()\n        if not os.getenv(degisken, "").strip()\n    ]\n\n    if eksik_ayarlar:\n        st.error(\n            "KAP/VBTS koruması kullanılamıyor — Toplu tarama kilitli."\n        )\n        st.caption(\n            "Resmî KAP abonelik ve erişim ayarları tanımlanmadan "\n            "VBTS tedbirleri doğrulanamaz. Eksik ayarlar: "\n            + ", ".join(eksik_ayarlar)\n        )\n        return False\n\n    st.success(\n        "KAP/VBTS koruması yapılandırıldı. "\n        "Toplu tarama tedbir filtresiyle çalışacaktır."\n    )\n    st.caption(\n        "Canlı erişim, resmî KAP abonelik sözleşmesi ve yetkilendirilmiş "\n        "erişim bilgilerine bağlıdır."\n    )\n    return True\n\n'
    anchor = "def bist_toplu_tarama_sonucu_goster("
    if anchor not in source:
        fail("Durum kartı fonksiyonu için ekleme noktası bulunamadı.")

    return source.replace(anchor, function_text + anchor, 1)


def add_status_call(source: str) -> str:
    call = "    kap_vbts_durum_karti_goster()\n"

    if call in source:
        return source

    candidates = (
        "def bist_toplu_tarama_formu() -> None:\n",
        "def toplu_tarama_formu() -> None:\n",
    )

    for anchor in candidates:
        if anchor in source:
            return source.replace(anchor, anchor + call, 1)

    fail("Toplu Tarama formu fonksiyonu bulunamadı.")
    return source


def main() -> None:
    if not TARGET.exists():
        fail(f"Dosya bulunamadı: {TARGET}")

    source = TARGET.read_text(encoding="utf-8")
    shutil.copy2(TARGET, BACKUP)

    updated = ensure_os_import(source)
    updated = add_status_function(updated)
    updated = add_status_call(updated)

    compile(updated, str(TARGET), "exec")
    TARGET.write_text(updated, encoding="utf-8", newline="\n")

    print("Sprint-39 KAP/VBTS durum kartı eklendi.")
    print(f"Yedek: {BACKUP}")


if __name__ == "__main__":
    main()
