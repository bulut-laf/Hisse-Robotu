# Sprint-173 — Resmî Kaynak Adapter Konsolidasyonu ve Ortak Güvenlik Çekirdeği

Amaç: Sprint-166–172 arasında devreye alınan yedi kontrollü resmî kaynak
adapterinin tekrar eden ağ/güvenlik kodunu tek ortak çekirdekte toplamak.

## Kaynaklar

- KAP
- TCMB
- TÜİK
- SPK
- Hazine ve Maliye Bakanlığı
- Borsa İstanbul
- Resmî Gazete

## Değişmeyen davranış

Her adapter kendi dosyasında tutmaya devam eder:

- izin verilen host/path doğrulaması
- tekil detay URL kimliği
- redirect sonrası aynı içerik kimliği kontrolü
- kaynak-özel HTML ayrıştırma
- tarih/başlık/olay türü/kapsam kuralları
- hisse/sektör çıkarımına ilişkin kaynak-özel sınırlar
- ağ erişiminin varsayılan kapalı olması
- dry-run ve açık arşivleme onayı

## Ortak çekirdeğe taşınanlar

`official_source_http.py`:

- varsayılan timeout: 10 saniye
- izin verilen timeout: 1–30 saniye
- ortak maksimum yanıt boyutu: 2 MB
- standart GET + User-Agent
- HTTP / bağlantı / timeout hata eşleme
- HTML Content-Type zorunluluğu
- ikinci boyut kontrolü (injected fetcher dahil)
- UTF-8, ardından ISO-8859-9 çözümleme

Adapterlerin `_default_fetch` fonksiyonları korunur; böylece mevcut test-enjeksiyon
sözleşmesi ve dış API değişmez.

## Güvenlik ilkeleri

- URL whitelist mantığı ortak çekirdeğe taşınmaz; kaynak dosyalarında kalır.
- Bir adapterin parser veya redirect kimliği diğer adapterleri etkilemez.
- Otomatik polling, toplu scraping ve arka plan taraması yoktur.
- Yeni skor, fiyat yönü, AL/SAT, teknik skor veya AI etkisi yoktur.
- PDF/ek otomatik takip davranışı eklenmez.

Bu sprint davranış genişletme değil, bakım maliyeti ve güvenlik sapmasını azaltan
mimari konsolidasyondur.
