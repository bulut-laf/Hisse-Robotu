# Sprint-161 — Hisse Haberleri ve Sembol Bazlı Haber Görünümü

## Amaç

Mevcut Haber Merkezi arşivini hisse bazında hızlı okunabilir hale getirmek.
Yeni veri kaynağı, otomatik internet, scraping veya AI eklenmez.

## Temel sözleşme

- Yalnız `MarketEvent.symbols` alanında açıkça bulunan semboller kullanılır.
- Haber metninden hisse sembolü tahmin edilmez.
- Bir olay + bir hisse = tek satırdır.
- Aynı olayın çoklu haber kaynakları satırı çoğaltmaz; haber/kaynak sayıları özetlenir.
- Ana sıralama en son haber yayın zamanıdır; eşitlikte mevcut önem skoru kullanılır.
- Mevcut 0–100 önem skoru dışında yeni skor üretilmez.
- KAP varlığı yalnız güvenilir kaynak sözlüğünün gerçek KAP çözümlemesiyle işaretlenir.
- Gölge Portföy teması yalnız açık pozisyon sembolüyle doğrudan kesişimdir.
- Fiyat yönü, AL/SAT, teknik skor veya AI yorumu üretilmez.

## Görünüm

- Son 24 saat / 3 gün / 7 gün / tüm arşiv
- Asgari önem filtresi
- Hisse filtresi
- Yalnız Gölge Portföy filtresi
- Hisse / olay / önem >=80 / çok kaynaklı / birincil kaynak / KAP içeren metrikleri
- Son yayın, son başlık, haber sayısı, kaynak sayısı, kaynaklar, KAP ve portföy bilgisi

## Değiştirilmeyenler

- Haber Merkezi SQLite şeması
- KAP Akışı
- Ekonomik Takvim
- Bugünün Önemli Gelişmeleri
- Sektör Etki Haritası
- Portföy Etki Radarı
- Sprint-157 görsel girdi ve retry katmanı
- teknik skor / AL-SAT karar motoru
