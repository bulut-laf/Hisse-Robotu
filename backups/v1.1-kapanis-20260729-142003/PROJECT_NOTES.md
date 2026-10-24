# Hisse Robotu — Proje Notları

## Proje Bilgisi

- Proje: Hisse Robotu
- Sürüm hedefi: V1.0
- Platform: Windows / PowerShell / Python
- Python sürümü: 3.14.6
- Kullanım amacı: Kişisel BIST hisse analizi
- Son güncelleme: 27 Temmuz 2026

## Güncel Durum

Hisse Robotu çekirdek hedefler açısından tamamlanmış ve kullanıma hazırdır.

### Sprint-32 — Tamamlandı

- Otomatik testler: 541/541 başarılı
- Sistem kontrolleri: 14/14 başarılı
- Uyarı: 0
- Hata: 0
- Python dosyası sözdizimi kontrolü: 152 dosya başarılı
- Son kullanıcı başlatıcısı: Başarıyla doğrulandı
- Streamlit arayüzü: Başarıyla açıldı

### Doğrulanan Ana Zincirler

- Güncel piyasa verilerinin alınması
- Teknik analiz
- Tek hisse backtest akışı
- İşlem planı üretimi
- Risk yönetimi
- Açık pozisyon izleme
- Analiz geçmişine kayıt
- Analiz geçmişini yeniden okuma
- CSV rapor üretimi
- PDF rapor üretimi

## Programı Başlatma

Program aşağıdaki dosya kullanılarak açılır:

D:\Projects\Hisse-Robotu\Hisse-Robotu-Baslat.ps1

PowerShell üzerinden alternatif başlatma komutu:

.\Hisse-Robotu-Baslat.ps1

## Temel Dosyalar

- Hisse-Robotu-Baslat.ps1
- requirements.txt
- PROJECT_NOTES.md
- backend/
- tests/

## Sprint-33 — V1.0 Paketleme

Durum: Tamamlandı

Tamamlanan işlemler:

- Güncel kaynak yedeği oluşturuldu.
- Kaynak paketindeki 156 dosya başarıyla açılarak doğrulandı.
- requirements.txt dosyası doğrulandı.
- Son kullanıcı başlatıcısı proje klasöründe doğrulandı.
- PROJECT_NOTES.md oluşturuldu.

Kaynak yedeği:

C:\Users\user\Downloads\Hisse-Robotu-Source-Snapshot.zip

## V1.0 Sonrası Çalışma İlkesi

Yeni özellikler doğrudan eklenmeyecektir.

Program gerçek kullanım sırasında gözlemlenecek; yalnızca ortaya çıkan somut hata, eksiklik veya kullanım ihtiyacına göre geliştirme yapılacaktır.


## Sprint-34 — BIST Toplu Tarama ve Aday Sıralama

Durum: Geliştirme ve otomatik doğrulama tamamlandı; kullanıcı ortamı kurulumu bekleniyor.

Eklenen yetenekler:

- Yeni `BIST Toplu Tarama` analiz modu.
- Kayıtlı izleme listesi, özel liste, BIST 30, BIST 100, BIST 500 ve BIST Tüm evrenleri.
- Borsa İstanbul resmi endeks bileşenleri CSV kaynağından güncelleme.
- Ağ erişimi olmadığında yerel önbellek ve paketlenmiş resmi anlık görüntüye geri dönüş.
- Yüzlerce sembol için parça bazlı toplu yfinance veri indirme.
- Gevşek, Dengeli ve Sıkı tarama profilleri.
- Teknik skor, hacim, risk/getiri ve teknik görünüme göre otomatik eleme.
- Giriş, stop, hedef, risk/getiri, RSI, ATR ve hacim oranı içeren aday tablosu.
- `Teknik aday` ve `Teyit bekliyor` sınıflandırması.
- Elenen hisseler ve veri hataları için açıklamalı ayrıntı ekranları.

Doğrulama sonucu:

- Otomatik testler: 555/555 başarılı.
- Sistem kontrolleri: 16/16 başarılı.
- Python kaynak dosyaları: 159 dosya sözdizimi kontrolünden geçti.
- BIST evren anlık görüntüsü: 27/07/2026.
- Evren boyutları: BIST 30 = 30, BIST 100 = 100, BIST 500 = 500, BIST Tüm = 574.

Not:

Gerçek BIST toplu taramasının kullanıcı bilgisayarında ağ erişimi ve yfinance veri sağlayıcısıyla son kullanıcı doğrulaması Sprint-34 paketi kurulduktan sonra yapılacaktır.


## Sprint-35 — BIST Momentum Keşif ve Erken Uyarı Motoru

Durum: Geliştirme ve otomatik doğrulama tamamlandı; kullanıcı ortamı kurulumu bekleniyor.

Eklenen yetenekler:

- Yeni `Momentum Keşif` analiz modu.
- BIST Tüm dahil bütün mevcut tarama evrenleriyle çalışma.
- Göreceli güç, 5/20/60 günlük fiyat ivmesi ve hacim birikimi puanları.
- Sıkışma, 20 günlük zirve yakınlığı ve hacimli kırılım tespiti.
- Trend, likidite ve risk kalitesi bileşenleriyle 100 puanlık momentum potansiyeli.
- A — Erken Keşif, B — Kırılım Başladı, C — İşleme Hazır Aday ve D — Aşırı Yükselmiş sınıfları.
- Mevcut teknik skor ve risk/getiri planıyla ikinci katman doğrulama.
- Tarama geçmişi, listede gün sayısı ve ilk görülmeden sonraki getiri takibi.
- Özel Liste alanının pasif kalması sorununun giderilmesi.
- Kayıtlı izleme listelerinde UTF-8 BOM karakterinin otomatik temizlenmesi.

Doğrulama sonucu:

- Otomatik testler: 565/565 başarılı.
- Yeni momentum ve geçmiş testleri dahil edildi.
- Sistem kontrolü Sprint-35 sürümüne yükseltildi ve momentum keşif zinciri eklendi.

Not:

KAP/şirket haber katalizörü bu sürümde otomatik puanlanmaz. Momentum adayları kesin alım önerisi değildir ve ayrıntılı güncel teknik analizde doğrulanmalıdır.

## Sprint-35 Rev1 — Kırılım Öncesi Erken Uyarı ve Walk-Forward

Durum: Geliştirme ve otomatik doğrulama tamamlandı; kullanıcı ortamı kurulumu bekleniyor.

Eklenen yetenekler:

- Momentum hazırlığı E0, E1, E2 ve E3 aşamalarına ayrıldı.
- E0: fiyat/ATR sıkışması; E1: hacim birikimi; E2: dirence yaklaşma; E3: kırılım öncesi erken uyarı.
- 20 günlük yakın direnç ve dirence yüzdesel uzaklık hesabı.
- Son 5 günlük göreceli güç eğimi ve kesitsel güç eğimi sıralaması.
- Kademeli hacim eğimi, RSI eğimi, MACD histogram eğimi ve yakın EMA kesişimi ölçümleri.
- Kırılım gerçekleşmeden önce trend, hacim, momentum ve direnç yakınlığını birlikte değerlendiren E3 sınıflandırması.
- Momentum aday tablosuna yakın direnç, hacim eğimi ve göreceli güç eğimi alanları.
- Tarihsel yeniden oynatma (walk-forward): kesim tarihinden sonraki fiyatlar aday üretiminden gizlenir.
- Aday sonrası 5/10/20 günlük getiri, 20 günlük azami yükseliş ve azami ters hareket ölçümü.
- Sistem kontrolüne tarihsel yeniden oynatma zinciri eklendi.

Doğrulama sonucu:

- Otomatik testler: 571/571 başarılı.
- Sistem kontrolleri: 18/18 başarılı.
- Python kaynak dosyaları: 165 dosya sözdizimi kontrolünden geçti.

Çalışma ilkesi:

E0–E3 sınıfları alım kararı değildir. E3 adayı bile kırılım, çoklu zaman dilimi teyidi, hacim ve risk/getiri açısından Güncel Teknik Analiz ekranında yeniden doğrulanmalıdır. Walk-forward sonuçları geçmiş başarı ölçümüdür; gelecek performansı garanti etmez.

## Sprint-35 Rev2 — Sinyal Hafızası ve Gerçek İleri Fiyat Aralığı

Durum: Geliştirme ve otomatik doğrulama tamamlandı; kullanıcı ortamı kurulumu bekleniyor.

Eklenen yetenekler:

- Yeni `K — Kalıcı Hazırlık Adayı` sınıfı.
- Günlük sınıfı geçici olarak İzleme Dışı kalan hisseler için 30 günlük hazırlık geçmişi ve 10 günlük hafıza penceresi.
- Son altı sınıfın tarihli sinyal zinciri, son hazırlık sinyali ve son güçlü sinyal tarihi.
- İzleme Dışı kalan hisseler için açıklamalı eleme nedeni.
- Yakın direncin %0,20 üzerindeki kırılım tetik seviyesi.
- Tarihsel yeniden oynatmada 5/10/20 günlük kapanış getirilerinin ayrı gösterimi.
- İleri veri penceresinde kapanış yerine gerçek `High` ve `Low` değerlerinden dönem içi en yüksek/en düşük fiyat hesabı.
- Gerçek azami yükseliş, pozitif büyüklük olarak azami ters hareket ve bu seviyelerin tarihleri.
- On veya daha az sembollü özel/kayıtlı listelerde son altı haftalık sınıf geçmişinin otomatik yeniden üretilmesi.
- Tarihsel testte İzleme Dışı sonuçların gizlenmemesi; ham skor, direnç uzaklığı ve elenme nedeninin ayrı tabloda gösterilmesi.
- Momentum canlı taramasında Kalıcı Hazırlık sayacı ve İzleme Dışı nedenler tablosu.

GRSEL doğrulama örneği:

- 17/07/2026 E3 sinyal fiyatı: 315,75.
- Sonraki görülen en yüksek fiyat: 358,75.
- Gerçek azami yükseliş: yaklaşık %13,62.
- Önceki hazırlık zinciri: E1 → E1 → E1 → E0 → İzleme Dışı/Kalıcı İzleme → E3.

Doğrulama sonucu:

- Otomatik testler: 575/575 başarılı.
- Sistem kontrolleri: 18/18 başarılı.
- Sistem kontrol sürümü: Sprint-35 Rev2.

Çalışma ilkesi:

Kalıcı hazırlık veya E3 sinyali doğrudan alım kararı değildir. Adaylar Güncel Teknik Analiz ekranında çoklu zaman dilimi, hacim, giriş, stop ve risk/getiri açısından yeniden doğrulanmalıdır.


## Sprint-36 — İşlem Kayıp Analizi ve Güvenlik Kilidi

Durum: Geliştirme ve otomatik doğrulama tamamlandı; kullanıcı ortamı kurulumu bekleniyor.

Eklenen yetenekler:

- Yeni `İşlem Kayıp Analizi` analiz modu.
- Gerçek ve deneme hesapları için ayrı tamamlanmış işlem günlüğü.
- Elle işlem kaydı, CSV şablonu, CSV içe aktarma ve dışa aktarma.
- Giriş/çıkış, lot, sermaye, stop, hedef, masraf, sinyal sınıfı ve işlem disiplini işaretleri.
- Net kâr/zarar, başarı oranı, kâr faktörü, işlem başına beklenti, azami düşüş ve ardışık zarar ölçümleri.
- Stop eksikliği, yetersiz risk/getiri, fazla işlem riski, büyük pozisyon, geç giriş, kaybedene ekleme ve aşırı yükselmiş giriş için kayıp nedeni teşhisi.
- Stop ve hedef olmadan işlem kilidi.
- İşlem başına risk, pozisyon/sermaye, günlük zarar, haftalık zarar ve ardışık zarar sınırları.
- Kaybeden pozisyona ekleme ve aşırı yükselmiş bölgede giriş engeli.
- Yeni işlem ön kontrolü; emir göndermez ve yalnızca tanımlı güvenlik kurallarını değerlendirir.
- İşlem günlüğü için kullanıcı profilinde atomik JSON kayıt ve tekrarlanan CSV içe aktarmada kayıt tekilleştirme.
- Sistem kontrolüne işlem kayıp analizi ve güvenlik kilidi zinciri eklendi.

Çalışma ilkesi:

Kayıp nedenleri yalnızca kullanıcının günlüğe girdiği verilerden türetilir. Eksik stop, hedef, sermaye veya disiplin işaretleri teşhisi değiştirir. Güvenlik kilidinin açık olması kazanç garantisi veya yatırım tavsiyesi değildir; yalnızca belirlenen risk sınırlarının aşılmadığını gösterir.


# Sprint-37 — Veri Tazeliği Güvenlik Kilidi

## Amaç

Momentum, toplu tarama ve güncel teknik analiz sonuçlarının eski günlük kapanış verisiyle kullanılmasını önlemek.

## Eklenenler

- İstanbul saati ve BIST kapanış saati (18:10) esas alınarak beklenen son tamamlanmış işlem günü hesabı.
- Veri sağlayıcının kapanış barını yayınlaması için 20 dakikalık güvenlik süresi.
- Seans içinde önceki tamamlanmış işlem gününün normal kabul edilmesi.
- Seans kapanışı sonrasında bugünkü tamamlanmış bar yoksa veri tazeliği kilidi.
- Hafta sonlarında son cuma barının beklenen tarih kabul edilmesi.
- Momentum Keşif, BIST Toplu Tarama ve Güncel Teknik Analiz ekranlarında ayrı veri tazeliği kartı.
- Son fiyat veri tarihi, beklenen tarih, iş günü gecikmesi ve toplu taramadaki eski sembol sayısının gösterimi.
- Eski, boş veya gelecek tarihli veride aday sıralaması, teknik teyit, stop, hedef ve lot değerlerinin ekranda durdurulması.
- Sistem kontrolüne veri tazeliği güvenlik zinciri.

## Not

Resmî tatil günleri için politika katmanı kapalı tarih listesi kabul eder. İlk sürüm hafta sonlarını otomatik yönetir; resmî tatil takviminin otomatik güncellenmesi sonraki veri altyapısı geliştirmesinde ele alınacaktır.

## Yerel doğrulama

- Yeni veri tazeliği testleri: 5/5 başarılı.
- Momentum, toplu tarama, canlı analiz ve sistem kontrolü regresyon grubu: 58/58 başarılı.
- Değiştirilen Python dosyaları sözdizimi kontrolünden geçti.
- Tam test paketi ve çevrimdışı sistem kontrolü kullanıcı bilgisayarındaki kurulum sırasında çalıştırılır.

