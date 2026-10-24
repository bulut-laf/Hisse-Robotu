# Sprint-174 — Resmî Kaynak Sağlık Kontrolü ve Tanılama Katmanı

Amaç: Yedi kontrollü resmî kaynak adapterinin çalışma sözleşmesini uygulama
içinden, internet erişimi açmadan ve kaynakları otomatik sorgulamadan
gözlemlenebilir hale getirmek.

## Neden yeni kaynak eklenmedi?

Sprint-166–172 arasında KAP, TCMB, TÜİK, SPK, HMB, Borsa İstanbul ve
Resmî Gazete için kontrollü adapterler kuruldu. Sprint-173 ortak HTTP/güvenlik
çekirdeğini merkezileştirdi. Bu aşamada yeni kaynak eklemekten önce mevcut
adapterlerin yapısal durumunu tek yerden görünür kılmak bakım ve güvenlik
açısından daha değerlidir.

## Yapısal tanılama

Her adapter için şu kontroller yapılır:

1. Kanonik kaynak adı güvenilir Tier-1 sözlüğünde kayıtlı mı?
2. Örnek resmî alan adı aynı kanonik kaynakla eşleşiyor mu?
3. Kaynak-özel URL doğrulayıcı örnek güvenli URL sözleşmesini kabul ediyor mu?
4. Adapter varsayılan ayarlarla oluşturulabiliyor mu?
5. `network_enabled` varsayılan olarak `False` mı?
6. Timeout ortak çekirdeğin varsayılan 10 saniye değerinde mi?
7. Ağ kilidi gerçek/injected fetcher çağrılmadan önce isteği durduruyor mu?

Toplam: 7 kaynak × 7 kontrol = 49 yapısal kontrol.

## Kritik güvenlik kararı

Bu tanılama bir canlı internet sağlık testi değildir.

- Kaynaklara ping atmaz.
- HEAD/GET isteği yapmaz.
- Arka planda URL taramaz.
- Kullanıcı onayı olmadan ağ açmaz.
- Kaynağın o anda internette erişilebilir olduğunu iddia etmez.

Canlı erişim doğrulaması mevcut adapterlerin tek URL önizleme akışıyla ve
kullanıcının açık ağ onayıyla yapılmaya devam eder.

## Arayüz

Kaynak Besleme ekranına:

- Yapısal sağlık özeti
- geçen/toplam kontrol sayısı
- canlı ağ testi durumu
- varsayılan ağ kilidi
- kaynak bazında HAZIR/HATA tablosu
- hata varsa açık tanılama notları

eklenir.

Aktif adapter isimleri ve sayısı artık aynı merkezi adapter sağlık
kayıtlarından türetilir; UI içinde `7` ve kaynak listesi iki ayrı yerde
elle tutulmaz.

## Değişmeyen davranışlar

- KAP, TCMB, TÜİK, SPK, HMB, Borsa İstanbul ve Resmî Gazete URL/parser
  sözleşmeleri değişmez.
- Tek URL + açık ağ onayı korunur.
- Dry-run + açık arşivleme onayı korunur.
- Otomatik polling/toplu scraping/arka plan taraması yoktur.
- Yeni skor, fiyat yönü, AL/SAT, teknik skor veya AI yorumu yoktur.
