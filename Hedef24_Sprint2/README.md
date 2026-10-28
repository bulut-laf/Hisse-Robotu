# Hedef 24 — Sprint 2: Kalıcı portföy veri katmanı

Bu paket, ayrı bir JSON tabanlı veri katmanı ve 6 hedef test sağlar. Dashboard'a bağlanmaz; `backend/dashboard.py` ve F1–F4 akışı değiştirilmez.

## Kurulum
Proje kökünde:
```powershell
.\hedef24_sprint2\INSTALL_HEDEF24_SPRINT2.ps1 -ProjectRoot "D:\Projects\Hisse-Robotu"
```
ZIP'i proje köküne çıkarınca `hedef24_sprint2` klasörü oluşmalıdır.

## Hedef testleri
```powershell
.\.venv\Scripts\python.exe -m py_compile backend\app\funds\hedef24_store.py
.\.venv\Scripts\python.exe -m pytest backend\tests\test_hedef24_store_sprint2.py -q
```

## Neler var
- JSON dosyasında kalıcı kayıt ve atomik yazma
- Başlangıç seed dosyasını içe aktarma (dolu portföyü izinsiz ezmez)
- Fon ekleme, düzenleme, onaylı çıkarma
- Tekrarlanan ISIN engeli
- Günlük NAV geçmişi (aynı fon/tarih tekrarında güncelleme)
- Alış NAV ve güncel NAV varsa birim bazlı yüzde K/Z
- İşlem yetkisi yok (`execution_authority = NONE`)

Not: Bu sprintte UI entegrasyonu yoktur; önce veri katmanı hedef testleri geçmelidir.
