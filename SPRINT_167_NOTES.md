# Sprint-167 — İkinci Kontrollü Resmî Kaynak Adapteri (TCMB)

Amaç: Sprint-166 KAP adapteri ile doğrulanan güvenli modeli TCMB basın
duyurularına genişletmek.

## Kapsam

Yalnız tek bir resmî TCMB basın duyurusu detay URL'si:

`https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Duyurular/Basin/<YIL>/DUY<YIL>-<NO>`

## Güvenlik

- Ağ erişimi varsayılan KAPALI.
- Kullanıcı her TCMB çekiminde ayrıca ağ onayı verir.
- Yalnız HTTPS.
- Yalnız `tcmb.gov.tr` / `www.tcmb.gov.tr`.
- Yalnız TCMB `Duyurular/Basin/<yıl>/DUY<yıl>-<no>` detay yolu.
- URL yıl bilgileri uyuşmazsa reddedilir.
- Query string, fragment, kullanıcı bilgisi ve özel port reddedilir.
- Yönlendirme başka hosta veya başka duyuru numarasına giderse reddedilir.
- Timeout 10 saniye; izin verilen aralık 1-30 saniye.
- 2 MB yanıt sınırı.
- HTML dışı yanıt reddedilir.
- Otomatik liste taraması, polling, toplu scraping veya arka plan taraması yok.

## Ayrıştırma

- Duyuru tarihi
- Başlık
- Görünür duyuru metni

Hisse veya sektör çıkarılmaz. TCMB basın duyurusu `TURKEY_MACRO` kapsamındadır.

Olay türü yalnız açıklanabilir başlık kurallarıyla:
- faiz / para politikası → `PARA_POLITIKASI`
- makroihtiyati / zorunlu karşılık → `REGULASYON`
- döviz / bağımsız "kur" ifadesi → `DOVIZ`
- diğer → `DIGER`

Alt dize yanlış pozitiflerini önlemek için "kur" kelime sınırıyla eşleştirilir.
AI sınıflandırması yoktur.

## Arşivleme

TCMB URL → çek → FeedItem → dry-run → duplicate kontrolü →
ayrı açık kullanıcı onayı → Haber Merkezi arşivi.

Yeni birleşik/gizli skor, fiyat yönü, AL/SAT, teknik skor veya AI yorumu yoktur.
