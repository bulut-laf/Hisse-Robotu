# Sprint-172 — Yedinci Kontrollü Resmî Kaynak Adapteri (Resmî Gazete)

Amaç: KAP, TCMB, TÜİK, SPK, HMB ve Borsa İstanbul ile doğrulanan kontrollü
kaynak modelini Resmî Gazete tekil HTML mevzuat maddelerine genişletmek.

## Kapsam

Yalnız tek bir resmî Resmî Gazete HTML mevzuat URL'si:

`https://www.resmigazete.gov.tr/eskiler/YYYY/MM/YYYYMMDD-N.htm`

## Güvenlik

- Ağ erişimi varsayılan KAPALI.
- Kullanıcı her Resmî Gazete çekiminde ayrıca ağ onayı verir.
- Yalnız HTTPS.
- Yalnız `resmigazete.gov.tr` / `www.resmigazete.gov.tr`.
- Yalnız `/eskiler/YYYY/MM/YYYYMMDD-N.htm` tekil HTML maddesi.
- Klasör yılı/ayı ile dosya tarihi uyuşmazsa reddedilir.
- Query string, fragment, kullanıcı bilgisi ve özel port reddedilir.
- Yönlendirme başka hosta veya başka mevzuat maddesine giderse reddedilir.
- Timeout 10 saniye; izin verilen aralık 1-30 saniye.
- 2 MB yanıt sınırı.
- HTML dışı yanıt reddedilir.
- Günlük sayı indeksi, PDF/ek veya aynı sayının diğer maddeleri otomatik takip edilmez.
- Otomatik liste taraması, polling, toplu scraping veya arka plan taraması yok.

## Tarih ve içerik

Yayın tarihi resmî arşiv URL'sindeki `YYYYMMDD` alanından alınır.
Klasör yıl/ay bilgisiyle çapraz doğrulanır.

HTML içinden:
- mevzuat başlığı
- görünür mevzuat metni

alınır.

Hisse veya sektör çıkarılmaz.

## Deterministik sınıflandırma

Başlık açıkça:

- sermaye/pay piyasası/Borsa İstanbul → `REGULASYON + BIST_WIDE`
- döviz/kambiyo → `DOVIZ + TURKEY_MACRO`
- borçlanma/tahvil/Hazine bonosu/kira sertifikası
  → `BORCLANMA_FINANSMAN + TURKEY_MACRO`
- enflasyon/fiyat istikrarı → `ENFLASYON + TURKEY_MACRO`
- vergi/KDV/ÖTV/bütçe/kamu maliyesi/bankacılık/finansal düzenleme
  → `REGULASYON + TURKEY_MACRO`
- diğer kanun/yönetmelik/tebliğ/karar/genelge
  → `REGULASYON + OTHER`
- mevzuat niteliği açık olmayan içerik → `DIGER + OTHER`

Gövde metninden piyasa kapsamı, hisse, sektör veya fiyat yönü tahmin edilmez.

## Arşivleme

Resmî Gazete URL → çek → FeedItem → dry-run → duplicate kontrolü →
ayrı açık kullanıcı onayı → Haber Merkezi arşivi.

Yeni birleşik/gizli skor, fiyat yönü, AL/SAT, teknik skor veya AI yorumu yoktur.
