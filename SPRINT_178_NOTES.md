# Sprint-178 — Haber Merkezi V1 Kararlı Sürüm ve Tam Sistem Doğrulaması

Yeni özellik eklenmez. Sprint-149–177 zinciri V1.0.0 olarak kilitlenir.

Yeni bileşenler:
- `backend/app/news_center/v1_release.py`: V1 manifesti ve ağsız backend doğrulama
- `backend/scripts/verify_news_center_v1.py`: kullanıcı bilgisayarında sistem kontrolü
- `HABER_MERKEZI_V1_RELEASE.md`: kararlı sürüm kapsam/sınır belgesi

V1 sistem kontrolü:
- semver sürüm
- 7 aktif resmî adapter
- 7/7 adapter hazır
- 49/49 yapısal kontrol
- ağ probe yok
- Tier-1 registry
- HTTP timeout 1/10/30
- 2 MB sınır
- audit olay sözleşmesi
- yetenek ve güvenlik manifestleri
- UI/backend kaynak eşitliği
- V1 sürüm kimliği
- 14 sekme
- eski Streamlit width API yok
- Günlük Operasyon güvenlik sınırları

Yeni kaynak, skor, AL/SAT, AI karar mekanizması, polling, scraping veya background
tarama eklenmez.


## Rev6 Windows/onarım düzeltmesi

- Windows yerel codepage'inden bağımsız UTF-8 stdout/stderr kilidi eklendi.
- `PYTHONUTF8=1` ve `PYTHONIOENCODING=utf-8` kurulum doğrulamasında zorunlu.
- Önceki başarısız rollback sonrasında eksik kalabilen V1 dosyaları tam kapanış setinden yeniden kurulur.
