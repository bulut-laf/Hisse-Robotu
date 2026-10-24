# Sprint-181 — Toplu Haber Özetleme ve Önem Süzme V1

## Amaç
Halka Açık Haber Akışı V1.1 önizlemesindeki **yeni RSS kayıtlarını arşive aktarmadan önce**, kullanıcının açık komutuyla topluca AI özetine dönüştürmek.

## Kapsam
- "Yeni haberleri AI ile topluca özetle" kullanıcı butonu.
- Yalnız yeni/duplicate olmayan RSS kayıtları AI girdisine girer.
- Üç kanalın mevcut üst sınırı olan 120 kayıt tek toplu özet çağrısında desteklenir.
- RSS gövdesi güvenli maliyet sınırı için kayıt başına en fazla 600 karakter ile prompta taşınır.
- AI çıktısı: kısa piyasa özeti, en fazla 10 öne çıkan gelişme, önem etiketi, neden önemli, kaynak kayıt kimlikleri, ana temalar ve izlenecek teyit/veri başlıkları.
- Kaynak kimlikleri yalnız mevcut RSS kayıtlarından seçilebilir; uydurma kaynak kimliği validator tarafından reddedilir.
- AI özeti arşive yazmaz; arşiv aktarımı ayrı açık onay olarak korunur.
- Otomatik AI, otomatik polling veya toplu haber sayfası scraping eklenmez.
- AI teknik analiz skoru, AL/SAT, hedef, stop veya fiyat yönü üretmez.
- Sprint-180 Rev1 performans koruması korunur: tabloda yalnız en yeni 20 kayıt çizilir; tüm önizleme aktarım/özet hesabında tutulur.

## AI sağlayıcı
Mevcut Hisse Robotu ortam değişkenleri kullanılır:
- `HISSE_ROBOTU_AI_PROVIDER` (varsayılan `gemini`)
- `HISSE_ROBOTU_GEMINI_MODEL` (varsayılan `gemini-3.5-flash-lite`)
- `GEMINI_API_KEY`
- OpenAI seçiliyse mevcut `HISSE_ROBOTU_OPENAI_MODEL` / `OPENAI_API_KEY`

## Güvenlik sınırı
Bu sprint haberleri **özetler ve önceliklendirir**; işlem karar motorunu veya teknik skorları değiştirmez.
