# Sprint-171 — Altıncı Kontrollü Resmî Kaynak Adapteri (Borsa İstanbul)

Amaç: KAP, TCMB, TÜİK, SPK ve HMB ile doğrulanan kontrollü kaynak modelini
Borsa İstanbul tekil duyuru detay sayfalarına genişletmek.

## Kapsam

Yalnız tek bir resmî Borsa İstanbul duyuru detay URL'si:

`https://www.borsaistanbul.com/duyuru/<ID>/<SLUG>`

## Güvenlik

- Ağ erişimi varsayılan KAPALI.
- Kullanıcı her Borsa İstanbul çekiminde ayrıca ağ onayı verir.
- Yalnız HTTPS.
- Yalnız `borsaistanbul.com` / `www.borsaistanbul.com`.
- Yalnız `/duyuru/<id>/<slug>` detay yolu.
- Query string, fragment, kullanıcı bilgisi ve özel port reddedilir.
- Yönlendirme başka hosta veya başka duyuru ID/slug adresine giderse reddedilir.
- Timeout 10 saniye; izin verilen aralık 1-30 saniye.
- 2 MB yanıt sınırı.
- HTML dışı yanıt reddedilir.
- Otomatik liste taraması, polling, toplu scraping veya arka plan taraması yok.
- Duyuru içindeki ek/PDF/Excel bağlantıları otomatik takip edilmez.

## Ayrıştırma

- Duyuru tarihi
- Başlık
- HTML detay sayfasındaki görünür duyuru metni

İlk sürümde hisse veya sektör çıkarılmaz. Duyuru içinde hisse kodları veya tablo
bulunsa bile otomatik sembol bağlantısı kurulmaz.

## Deterministik sınıflandırma

Başlık açıkça piyasa işleyişi/prosedür/kural/pazar/takas/emir/devre kesici veya
işleme açılma-açılmama değişikliği içeriyorsa:

- `REGULASYON`
- `BIST_WIDE`

Başlık açıkça BIST/endeks değişikliği içeriyorsa:

- `DIGER`
- `BIST_WIDE`

Gong, kurumsal etkinlik veya kapsamı açık olmayan diğer duyurular:

- `DIGER`
- `OTHER`

Gövde metninden piyasa kapsamı, hisse, sektör veya fiyat yönü tahmin edilmez.

## Arşivleme

Borsa İstanbul URL → çek → FeedItem → dry-run → duplicate kontrolü →
ayrı açık kullanıcı onayı → Haber Merkezi arşivi.

Yeni birleşik/gizli skor, fiyat yönü, AL/SAT, teknik skor veya AI yorumu yoktur.
