# Sprint-165 — Güvenilir Kaynak Besleme Hazırlık Katmanı

Amaç: Haber Merkezi'ni ileride KAP/TCMB/TÜİK/Borsa İstanbul gibi kaynaklara
bağlayabilmek için ağ erişiminden bağımsız, güvenli bir normalize-et/doğrula/
önizle/arşivle sözleşmesi kurmak.

## Bu sprintte var

- `FeedItem`: adapterlerin üretmek zorunda olduğu standart haber girdi modeli.
- Güvenilir kaynak sözlüğü ile alias/domain doğrulaması.
- Kaynak adının kanonik hale getirilmesi.
- Dry-run/preview: arşive yazmadan kaynak ve duplicate doğrulaması.
- Mevcut 10.000 haber içinde deterministik SHA-256 duplicate kontrolü.
- Açık `import_item()` çağrısı olmadan arşive yazmama.
- Arşiv UNIQUE content_hash kilidini son savunma olarak koruma.
- İstenirse açık `existing_event_id` ile mevcut olaya bağlama; otomatik yanlış
  olay eşleştirmesi yapmama.
- Kaynak Besleme durum ekranı.

## Bu sprintte yok

- HTTP/ağ erişimi
- scraping
- RSS/API endpoint çağrısı
- zamanlayıcı/background worker
- otomatik KAP/TCMB/TÜİK çekme
- haber metninden hisse/sektör tahmini
- yeni birleşik skor
- fiyat yönü / AL/SAT
- teknik skor değişikliği
- AI yorumu

Sprint-166'da her resmî kaynak adapteri ayrı güvenlik sözleşmesiyle açılabilir.
