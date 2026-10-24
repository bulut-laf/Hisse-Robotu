# Sprint-170 — Beşinci Kontrollü Resmî Kaynak Adapteri (Hazine ve Maliye Bakanlığı)

Amaç: KAP, TCMB, TÜİK ve SPK ile doğrulanan kontrollü kaynak modelini Hazine
ve Maliye Bakanlığı tekil haber/basın duyurusu sayfalarına genişletmek.

## Kapsam

Yalnız tek bir resmî HMB detay URL'si:

- `https://www.hmb.gov.tr/haberler/<slug>`
- `https://www.hmb.gov.tr/duyuru/<slug>`

## Güvenlik

- Ağ erişimi varsayılan KAPALI.
- Kullanıcı her HMB çekiminde ayrıca ağ onayı verir.
- Yalnız HTTPS.
- Yalnız `hmb.gov.tr` / `www.hmb.gov.tr`.
- Yalnız `/haberler/<slug>` veya `/duyuru/<slug>` tekil detay yolu.
- Query string, fragment, kullanıcı bilgisi ve özel port reddedilir.
- Yönlendirme başka hosta veya başka duyuru adresine giderse reddedilir.
- Timeout 10 saniye; izin verilen aralık 1-30 saniye.
- 2 MB yanıt sınırı.
- HTML dışı yanıt reddedilir.
- Otomatik liste taraması, polling, toplu scraping veya arka plan taraması yok.

## Ayrıştırma ve sınıflandırma

Yalnız duyuru tarihi, başlık ve görünür metin alınır. Hisse veya sektör çıkarılmaz.

Başlıkta açık ifade varsa:
- borçlanma / ihale / tahvil / kira sertifikası / nakit gerçekleşmeleri / borç stoku
  → `BORCLANMA_FINANSMAN + TURKEY_MACRO`
- enflasyon / fiyat istikrarı → `ENFLASYON + TURKEY_MACRO`
- döviz / kambiyo → `DOVIZ + TURKEY_MACRO`
- finansal istikrar / kamu finansmanı / mali disiplin / bütçe
  → `DIGER + TURKEY_MACRO`
- diğer → `DIGER + OTHER`

Genel “Basın Duyurusu” başlığında gövdeden piyasa etkisi tahmin edilmez.

## Arşivleme

HMB URL → çek → FeedItem → dry-run → duplicate kontrolü → ayrı açık kullanıcı
onayı → Haber Merkezi arşivi.

Yeni birleşik/gizli skor, fiyat yönü, AL/SAT, teknik skor veya AI yorumu yoktur.
