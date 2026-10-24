# Sprint-166 — İlk Kontrollü Resmî Kaynak Adapteri (KAP)

Amaç: Sprint-165'te kurulan normalize et → doğrula → dry-run → açık import →
arşiv zincirine ilk gerçek ağ adapterini eklemek.

## Kapsam

İlk adapter yalnız KAP içindir ve yalnız tek bir resmî bildirim detay URL'si ile
çalışır:

`https://www.kap.org.tr/tr/Bildirim/<numara>`

## Güvenlik

- Ağ erişimi varsayılan KAPALI.
- Kullanıcı her çekimde "Bu işlem için KAP ağına bağlan" onayını açmalıdır.
- Yalnız HTTPS kabul edilir.
- Yalnız `kap.org.tr` / `www.kap.org.tr` kabul edilir.
- Kullanıcı bilgisi, özel port, query string veya fragment reddedilir.
- Yalnız `/tr/Bildirim/<numara>` detay yolu kabul edilir.
- Yönlendirme başka hosta veya başka bildirim numarasına giderse işlem reddedilir.
- Timeout 10 saniye, izin verilen aralık 1-30 saniye.
- Yanıt üst sınırı 2 MB.
- HTML dışı yanıt reddedilir.
- Otomatik listeleme, polling, arka plan taraması veya toplu scraping yoktur.

## Ayrıştırma

KAP sayfasından yalnız görünür metin kullanılarak:
- Gönderim Tarihi
- Özet Bilgi
- Açıklamalar
- İlgili Şirketler
çıkarılır.

Hisse kodları yalnız "İlgili Şirketler" alanından gelir; açıklama metninden
hisse tahmini yapılmaz. Sektör tahmini yapılmaz.

## Arşivleme

- Çekim önce FeedItem üretir.
- FeedIngestionService.preview() dry-run yapar.
- Duplicate SHA-256 kontrolü yapılır.
- Kullanıcı ayrıca "Önizlemeyi arşive aktar" düğmesine basmadan kayıt yazılmaz.

Yeni birleşik/gizli skor, fiyat yönü, AL/SAT, teknik skor veya AI yorumu yoktur.

## Rev1 — Streamlit API uyumluluğu

- KAP düğmelerindeki `use_container_width=True` kaldırıldı.
- Güncel proje standardı `width="stretch"` kullanıldı.
- UI sözleşme testine eski parametrenin geri gelmesini engelleyen regresyon kontrolü eklendi.
