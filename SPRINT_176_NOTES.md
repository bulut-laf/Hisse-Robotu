# Sprint-176 — Kaynak Operasyon Geçmişi ve Son Başarılı Çekim Tanılaması

Amaç: Kullanıcının Kaynak Besleme ekranında açıkça başlattığı resmî kaynak
işlemlerini ağ açmadan, haber arşivinden ayrı bir yerel audit günlüğünde izlemek.

## Kayıt edilen işlemler

- PREVIEW_BLOCKED — kullanıcı önizleme düğmesine bastı ancak ağ onayı kapalıydı
- PREVIEW_SUCCESS — tek URL fetch + parse + dry-run başarılı
- PREVIEW_ERROR — açık kullanıcı onaylı önizleme hata verdi
- ARCHIVE_SUCCESS — kullanıcı açık arşivleme düğmesiyle kaydı arşivledi
- ARCHIVE_DUPLICATE — arşiv katmanı tekrar kaydı engelledi
- ARCHIVE_ERROR — açık arşivleme işlemi hata verdi

## Kalıcı veri

Yeni dosya:

`~/.hisse_robotu/news_center/official_source_operations.jsonl`

Bu dosya haber arşivi veritabanından ayrıdır.

Saklanır:
- işlem ID
- kanonik kaynak adı
- işlem türü
- UTC zaman
- güvenli kaynak referansı
- en fazla 500 karakter kısa sonuç/hata

Saklanmaz:
- haber gövdesi
- HTML yanıt
- API anahtarı
- kullanıcı adı/parola
- query string
- fragment

URL referansı audit öncesi kullanıcı bilgisi/query/fragment kaldırılarak
güvenli hale getirilir.

## UI

Kaynak Besleme ekranına "Kaynak operasyon geçmişi" bölümü eklenir.

Kaynak başına:
- son önizleme zamanı
- son önizleme sonucu
- son arşiv işlemi
- son arşiv sonucu
- son başarılı kullanım

Ayrıca:
- okunan operasyon sayısı
- son 24 saat operasyon sayısı
- en son başarılı kullanım
- geçersiz JSONL satır sayısı
- son 50 operasyon

gösterilir.

## Kritik sınırlar

- Bu özellik canlı kaynak sağlık testi değildir.
- Yeni ping/HEAD/GET üretmez.
- Otomatik polling/toplu scraping/arka plan taraması yoktur.
- Yalnız kullanıcının zaten var olan açık işlemleri loglanır.
- Audit yazma hatası ana fetch/arşiv akışını durdurmaz.
- Audit günlüğünü temizleyen/silen bir UI eklenmez.
- Haber gövdesi audit günlüğüne yazılmaz.
- Yeni skor, fiyat yönü, AL/SAT, teknik skor veya AI yorumu yoktur.
