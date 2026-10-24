# Sprint-150 — Haber Merkezi Arayüz Doğrulaması ve Manuel Kayıt Akışı

## Amaç
Sprint-149 çekirdeğini değiştirmeden manuel haber kullanım akışını kullanıcı seviyesinde sağlamlaştırmak.

## Değişiklikler
- Boş arşivde “mevcut olaya bağla” akışının ekranı erken kapatması engellendi.
- Arşiv üstüne Olay / Haber / Önem ≥80 / Çok kaynaklı olay özet metrikleri eklendi.
- Olay Arşivi sekmesine “Olay detayı” alanı eklendi.
- Seçilen olayın deterministik önem bileşenleri, sektörleri, hisseleri ve bağlı haber kaynakları birlikte gösterilir.
- `NewsArchive.list_news_for_event()` ile tek olaya bağlı haberların güvenli ve sıralı okunması eklendi.
- Başarılı manuel kayıtta olay kimliği, önem skoru ve güncel kaynak sayısı görünür.

## Değişmeyenler
- SQLite şeması değişmedi.
- Deterministik önem formülü değişmedi.
- Haber/olay veri modeli değişmedi.
- AI eklenmedi.
- Otomatik internet/KAP akışı eklenmedi.
- Teknik analiz skoru ve işlem karar motoru ile bağlantı kurulmadı.

## Güvenlik
Kurulum, Sprint-149’dan gelen iki çekirdek dosyanın SHA-256 değerlerini doğrular. Beklenmeyen yerel değişiklik varsa dosya üzerine yazmak yerine kurulum durur. Hedef test veya tam regresyon başarısız olursa değişiklikler geri alınır.
