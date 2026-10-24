# Sprint-156 — Sektör Etki Haritası

## Amaç

Sprint-153 deterministik etki bağlantılarını sektör bazında toplulaştırmak ve
Haber Merkezi içinde hangi sektörlerin güncel olay akışında öne çıktığını
açıklanabilir biçimde göstermek.

## Eklenenler

- `sector_impact.py` bağımsız toplulaştırma motoru.
- Yalnız `SECTOR` hedefli deterministik etki bağlantıları kullanılır.
- Son 24 saat / 3 gün / 7 gün / tüm arşiv dönem filtresi.
- Sektör başına olay sayısı, yüksek önem (>=80) olay sayısı.
- DIRECT ve SENSITIVITY bağlantı sayıları ayrı gösterilir.
- En yüksek olay önemi ve bağlantı güveni.
- Son olay zamanı ve etki etiketleri.
- Sektör–olay detay tablosu.

## Güvenlik sınırları

- Pozitif/negatif fiyat yönü üretilmez.
- AL/SAT kararı üretilmez.
- Teknik analiz skoru değiştirilmez.
- AI kullanılmaz.
- Sektör uydurulmaz; yalnız Sprint-153 etki motorunun ürettiği bağlantılar kullanılır.
- Haber arşivi ve SQLite şeması değiştirilmez.
- Sprint-155 Aktif Gölge Portföy / Trader yönetimi değiştirilmez.
