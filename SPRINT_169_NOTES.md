# Sprint-169 — Dördüncü Kontrollü Resmî Kaynak Adapteri (SPK)

Amaç: KAP, TCMB ve TÜİK ile doğrulanan kontrollü kaynak modelini SPK Basın
Duyuruları detay sayfalarına genişletmek.

## Kapsam

Yalnız tek bir resmî SPK Basın Duyuruları detay URL'si:

`https://spk.gov.tr/duyurular/basin-duyurulari/<YIL>/<SLUG>`

## Güvenlik

- Ağ erişimi varsayılan KAPALI.
- Kullanıcı her SPK çekiminde ayrıca ağ onayı verir.
- Yalnız HTTPS.
- Yalnız `spk.gov.tr` / `www.spk.gov.tr`.
- Yalnız `/duyurular/basin-duyurulari/<yıl>/<slug>` detay yolu.
- Query string, fragment, kullanıcı bilgisi ve özel port reddedilir.
- Yönlendirme başka hosta veya başka duyuru adresine giderse reddedilir.
- Timeout 10 saniye; izin verilen aralık 1-30 saniye.
- 2 MB yanıt sınırı.
- HTML dışı yanıt reddedilir.
- Otomatik liste taraması, polling, toplu scraping veya arka plan taraması yok.

## Ayrıştırma

- Duyuru tarihi
- Başlık
- Görünür duyuru metni

Hisse veya sektör çıkarılmaz.

Olay türü ve kapsam yalnız başlıktaki açık düzenleyici ifadelerden belirlenir:
- tedbir / düzenleme / mevzuat / kurul kararı / açığa satış / pay piyasası /
  sermaye piyasası / piyasa bozucu / işlem yasağı
  → `REGULASYON` + `BIST_WIDE`
- diğer başlıklar → `DIGER` + `OTHER`

Personel, eğitim, dolandırıcılık uyarısı gibi piyasa düzenlemesi olduğu açıkça
anlaşılmayan duyurulara BIST kapsamı uydurulmaz.

## Arşivleme

SPK URL → çek → FeedItem → dry-run → duplicate kontrolü →
ayrı açık kullanıcı onayı → Haber Merkezi arşivi.

Yeni birleşik/gizli skor, fiyat yönü, AL/SAT, teknik skor veya AI yorumu yoktur.
