# Hisse Robotu V1.1.1 — Kullanım Kılavuzu

Hisse Robotu kişisel araştırma, teknik analiz ve risk karar desteği amacıyla geliştirilmiştir. Emir göndermez. Sonuçlar yatırım tavsiyesi değildir.

## 1. V1.1.1 bakım paketini kurma

V1.1.1 bakım ZIP’ini bir klasöre çıkarın. PowerShell’i proje klasöründe açın:

```powershell
Set-Location D:\Projects\Hisse-Robotu
```

Paketteki doğrulama betiğini çalıştırın:

```powershell
powershell -ExecutionPolicy Bypass -File <paketin-cikarildigi-klasor>\V1.1.1-Bakim-Kur-ve-Dogrula.ps1
```

Betik şu işlemleri yapar:

1. Değiştirilecek dosyaların tarihli yedeğini alır.
2. V1.1.1 bakım dosyalarını doğru klasörlere kopyalar.
3. Güncel analiz geçmişi ve uyumluluk testlerini çalıştırır.
4. Tüm `backend/tests` regresyonunu bir kez çalıştırır.
5. Sistem kontrolünü çalıştırır.
6. Python sözdizimini doğrular.
7. Temiz kaynak ZIP’i, SHA-256 dosyası ve sürüm manifesti üretir.

Herhangi bir adım başarısız olursa betik hata koduyla durur ve V1.1.1 bakımı başarılı sayılmaz.

## 2. Programı başlatma

```powershell
Set-Location D:\Projects\Hisse-Robotu
.\Hisse-Robotu-Baslat.ps1
```

Programı kapatmak için çalıştığı PowerShell penceresinde `Ctrl+C` kullanın.

## 3. Ana çalışma modları

### Güncel Teknik Analiz

Tek hisse için haftalık ana trend, günlük teyit, saatlik zamanlama, teknik göstergeler, giriş, stop, hedef ve risk/getiri planı gösterir. Veri tazeliği kilidi geçilmiş başarılı sonuçlar otomatik olarak `Analiz Geçmişi`ne kaydedilir. Aynı veri ve aynı plan kimlikleriyle tekrar çalıştırılan analiz yeni bir kopya oluşturmaz; mevcut kayıt zaman damgasıyla güncellenir.

### BIST Toplu Tarama

Kayıtlı liste, özel liste, BIST 30, BIST 100, BIST 500 veya BIST Tüm evrenini tarar. Teknik skor, hacim, RSI, ATR, giriş, stop, hedef ve risk/getiri alanlarıyla adayları sıralar.

### Momentum Keşif

E0–E3 hazırlık aşamalarını, kırılım başlangıcını, kalıcı hazırlık hafızasını, göreceli gücü, hacim eğimini ve direnç yakınlığını inceler.

### Tarihsel Yeniden Oynatma

Kesim tarihinden sonraki fiyatları aday üretiminden gizler. Sonraki 5/10/20 günlük kapanış getirileri ile dönem içi gerçek en yüksek ve en düşük fiyat yalnızca performans ölçümünde kullanılır.

### İşlem Kayıp Analizi

Tamamlanmış gerçek veya deneme işlemlerini inceler. Stop, hedef, risk/getiri, pozisyon büyüklüğü, günlük/haftalık zarar ve ardışık zarar kurallarını değerlendirir.

### Açık Pozisyon İzleme

Giriş, lot, ilk stop ve hedefleri girilmiş pozisyon için dinamik stop, açık kâr/zarar ve hedef ilerlemesi gösterir.

### Analiz Geçmişi

Tek hisse backtest, portföy backtest ve Güncel Teknik Analiz sonuçlarını tarih, sembol ve analiz türüne göre yeniden görüntüler. Güncel teknik analiz kayıtlarında fiyat veri tarihi, teyit skoru, karar, plan tipi, giriş/stop/hedefler, lot/risk bilgileri ve analiz kimlikleri saklanır. Kayıt özeti CSV olarak indirilebilir ve analiz geçmişi ZIP yedeğine dahil edilir. Güncel teknik analiz kayıtları backtest getiri/düşüş özetine veya performans karşılaştırmasına karıştırılmaz.

## 4. VBTS kayıt hazırlama

VBTS kayıtları yalnızca resmî KAP bildiriminden doğrulanmalıdır.

Arayüzde:

1. `BIST Toplu Tarama` bölümünü açın.
2. `VBTS kayıt yönetimi` panelini genişletin.
3. Hisse sembolünü yazın.
4. Tedbir türünü yazın.
5. Başlangıç ve bitiş tarihlerini girin.
6. Resmî KAP bildirim referansını girin.
7. `Resmî KAP bildirimiyle doğruladım` kutusunu işaretleyin.
8. Kaydı ekleyin.

CSV şeması:

```text
symbol,measure_type,start_date,end_date,source_reference
```

Örnek:

```text
THYAO,Açığa satış ve kredili işlem yasağı,2026-07-29,2026-08-28,KAP-BILDIRIM-REFERANSI
```

Örnek satır yalnızca biçimi gösterir; gerçek tedbir ve referans resmî KAP bildirimiyle doğrulanmalıdır.

## 5. VBTS yaşam döngüsü

- **Aktif:** Bugün başlangıç ve bitiş tarihleri arasındadır; tarama filtresinde kullanılır.
- **Gelecekte başlayacak:** Arşivde tutulur, henüz aktif filtreye girmez.
- **Süresi dolmuş:** Arşivde tutulur, aktif taramada kullanılmaz.

Arayüz süresi dolmuş kayıtları kalıcı temizlemek için ayrıca onay ister.

## 6. Güvenlik kilidi

Toplu tarama düğmesi aşağıdaki durumlardan birinde devre dışı kalır:

- VBTS senkronizasyonu başarısız
- Sistem sağlık kontrolü başarısız
- Aktif CSV ile arşiv uyumsuz
- Aktif veri eksik, boş, bozuk veya eski
- Yedek bütünlüğü bozuk
- Denetim günlüğü bozuk
- VBTS kaynağı hazırlanamadı

Düğme durumu teknik olarak atlatılsa bile tarama başlamadan önce ikinci bir kod denetimi çalışır.

### Kilit açılmıyorsa

1. Paneldeki sağlık mesajını okuyun.
2. KAP/VBTS kaydının tarihlerini ve referansını kontrol edin.
3. `data\vbts` klasöründeki arşiv ve aktif CSV’nin erişilebilir olduğunu doğrulayın.
4. Bozuk yedek uyarısında yedeği değiştirmeyin; sağlam bir yedekten geri yükleyin.
5. Şu kontrolleri çalıştırın:

```powershell
python -m pytest backend\tests\test_v11_closeout_vbts_manager.py backend\tests\test_v11_closeout_dashboard_lock.py -q
python -m backend.run_system_check
```

## 7. VBTS yedek ve geri yükleme

`VBTS yedekleri ve denetim günlüğü` panelinde:

- Yedekleri görüntüleyebilirsiniz.
- Yedeğin kayıtlarını geri yüklemeden önce önizleyebilirsiniz.
- Geri yükleme için hem onay kutusu hem `GERİ YÜKLE` metni gerekir.
- Denetim günlüğünü CSV olarak indirebilirsiniz.
- Saklanacak yedek sayısını belirleyip eski yedekleri temizleyebilirsiniz.

Yedekler SHA-256 manifestiyle doğrulanır. Değiştirilmiş veya bozuk yedek geri yüklenmez.

## 8. Kayıtlı izleme listesi

```text
backend\watchlists\favoriler.txt
```

Her satıra bir sembol yazabilirsiniz:

```text
THYAO
ASELS
TUPRS
SAHOL
KCHOL
```

## 9. Sistem kontrolü ve testler

Sistem kontrolü:

```powershell
python -m backend.run_system_check
```

Tam regresyon:

```powershell
python -m pytest backend\tests -q
```

Sözdizimi kontrolü:

```powershell
python -m compileall backend -q
```

Paket doğrulaması:

```powershell
python -m pip check
```

## 10. Sorun bildirirken

Şunları birlikte paylaşın:

- Analiz modu
- Hisse sembolü veya tarama evreni
- Ekrandaki hata mesajı
- PowerShell’in son satırları
- `RELEASE-V1.1.1.json` içindeki test durumu
- Sorun VBTS ile ilgiliyse sağlık panelindeki dört durum: kayıt arşivi, aktif CSV, yedek bütünlüğü, denetim günlüğü

## 11. Temel Analiz V1

### Temel analiz ekranını açma

1. Programı başlatın.
2. Sol menüden `Temel Analiz` seçin.
3. Finansal veri kaynağını seçin.
4. Manuel kullanımda örnek CSV/JSON dosyasını yükleyin.
5. Veri tazeliği kilidini kontrol edin.
6. Analizi oluşturun.

### Temel kalite skoru

Temel kalite skoru 0–100 aralığındadır ve şu bileşenlerden oluşur:

- Kârlılık
- Büyüme
- Borçluluk
- Likidite
- Nakit akışı

Toplam skor ve alt skorlar yatırım tavsiyesi değildir. Teknik skorla birleştirilmez ve varsayılan olarak BIST taramasını filtrelemez.

### Temel skor geçmişi

Geçerli skorlar yerel depoda tutulur:

```text
backend\data\fundamental_scores.json
```

Ekranda dönemsel toplam skor ve alt skor değişimleri gösterilir. Eski, gelecek tarihli, kilitli veya uyumsuz kayıtlar karşılaştırmadan çıkarılır.

### Sektör karşılaştırması

Sektör referans CSV şeması:

```text
symbol,sector,market_cap
```

`market_cap` isteğe bağlıdır. F/K ve PD/DD yalnızca bu alan sağlandığında hesaplanır. Sektör ve piyasa değeri sistem tarafından tahmin edilmez.

### Rapor ve arşiv

Temel analiz ekranı:

- UTF-8 CSV raporu
- PDF özet raporu
- Yerel rapor arşivi
- Geçmiş rapor karşılaştırması
- Filtrelenmiş arşiv CSV’si
- Seçilen raporlar için toplu PDF

üretebilir.

Rapor arşivi:

```text
backend\data\fundamental_report_archive.json
```

### Temel analiz ayarları

`Temel analiz ayarları` panelinden:

- Güçlü, Dengeli ve İzlenmeli eşikleri
- Sektör karşılaştırması için asgari şirket sayısı
- Sektör değişim eşiği
- Skor geçmişi azami yaşı
- Rapor arşivi azami yaşı
- Varsayılan arşiv sıralaması

değiştirilebilir.

Ayar dosyası:

```text
backend\data\fundamental_analysis_settings.json
```

Geçersiz veya çelişen ayarlar kaydedilmez. `Varsayılan ayarlara dön` düğmesi güvenli başlangıç değerlerini geri yükler.

### Temel Analiz V1 görsel doğrulama listesi

- Ayarlar paneli açılıyor.
- Manuel finansal veri yükleniyor.
- Veri tazeliği durumu görünüyor.
- Toplam skor ve beş alt skor görünüyor.
- Skor geçmişi tablosu ve grafiği görünüyor.
- Sektör referans dosyası yüklenebiliyor.
- Sektör medyanı karşılaştırması görünüyor.
- Sektör sıralaması ve güç haritası görünüyor.
- CSV ve PDF raporları indirilebiliyor.
- Rapor arşivi listeleniyor.
- Arşiv filtreleri çalışıyor.
- Varsayılan ayarlara dönüş çalışıyor.
- Teknik skor, BIST taraması ve VBTS güvenlik davranışı değişmiyor.


# Teknik Analiz V1.2 Kullanımı

## RSI/MACD uyumsuzluk

`Güncel Teknik Analiz` sonucundaki `RSI/MACD uyumsuzluk` sekmesi günlük ve
haftalık veriyi ayrı değerlendirir. Normal ve gizli pozitif/negatif
uyumsuzluklar; pivot mesafesi, fiyat/osilatör farkı, hacim teyidi ve güven
düzeyiyle gösterilir.

Uyumsuzluk tek başına işlem kararı değildir.

## Günlük/Haftalık karar matrisi

`Günlük/Haftalık karar matrisi` sekmesinde trend, momentum, hacim, uyumsuzluk,
destek/direnç, ATR ve risk/getiri birlikte gösterilir. Çıktı yalnızca:

- İzlemeye Değer
- Temkinli İzle
- Uygun Değil

sınıflarından birini üretir. Alım/satım tavsiyesi üretmez.

## Sinyal sonuçları

Ana menüdeki `Sinyal Sonuçları` ekranı 5, 10 ve 20 işlem günü performansını
ölçer. Referans fiyat, sinyal tarihi, karar sınıfı, günlük/haftalık yön,
uyumsuzluk, piyasa rejimi, sektör, momentum, hacim, ATR ve risk/getiri alanları
kaydedilebilir.

Kesim tarihinden sonraki fiyatlar aday veya sinyal üretiminde kullanılmaz;
yalnızca performans ölçümünde kullanılır.

## Gösterge katkısı

`Gösterge katkısı` sekmesi bir göstergenin mevcut olduğu ve olmadığı kayıtları
karşılaştırır. Küçük örneklemde sonuç üretmez. `Destekleyici`, `Zayıflatıcı`,
`Belirsiz` ve `Yetersiz örnek` sınıfları nedensellik kanıtı değildir.

## Walk-forward doğrulama

`Walk-forward doğrulama` sekmesi eğitim dönemini yalnızca geçmiş kayıtlardan,
doğrulama dönemini daha sonraki kayıtlardan oluşturur. Tek bir en iyi
kombinasyon yerine farklı pencerelerde tekrar eden kararlı parametre bölgeleri
önceliklendirilir.

## Kapanış ve snapshot

Sprint-74 kapanış betiği hedef testleri, tam regresyonu, sistem kontrolünü ve
Python sözdizimini doğruladıktan sonra aşağıdaki dosyaları üretir:

- `releases\Hisse-Robotu-Teknik-Analiz-V1.2.zip`
- `releases\Hisse-Robotu-Teknik-Analiz-V1.2.sha256`
- `releases\RELEASE-TEKNIK-ANALIZ-V1.2.json`

Doğrulamalardan biri başarısızsa snapshot oluşturulmaz.


---

## V1.3 Operasyon ve Kalibrasyon Ekranları

### Gecikmeli Veri Pilotu

Gün içi gecikme, son bar zamanı, eksik bar ve güvenlik kilidi durumunu gösterir.
Gün içi gecikmeli veri kesin alım/satım sinyali olarak kullanılmaz.

### Günlük Operasyon Paneli

Gecikmeli veri, bekleyen sinyal sonuçları, işlem günlüğü ve günlük görevleri tek
ekranda özetler.

### Otomatik Sinyal Kaydı

Aynı sembol ve tarih için mükerrer kayıt oluşturmaz. 5/10/20 günlük sonuçlar,
yeni fiyat verisi geldikçe güncellenir.

### Gölge Portföy

Gölge Portföy gerçek emir göndermez ve gerçek para kullanmaz. Pozisyonlar yalnızca
kalibrasyon, performans ölçümü ve işlem günlüğü amacıyla kaydedilir.

### Haftalık Performans Raporu

Gölge portföy sonuçlarını dönemsel olarak özetler ve CSV/PDF çıktısı üretir.

### Başarı Karşılaştırması

Rejim, sektör, gösterge, yön uyumu, hacim onayı ve kalite bandı bazında
5/10/20 günlük sonuçları karşılaştırır. Yetersiz örneklem grupları tek başına
kalibrasyon kararı için kullanılmaz.

### V1.3 Kalibrasyon Kararı

Sprint-75–80 kayıt zincirlerini birlikte değerlendirir ve şu sonuçlardan birini
üretir:

- Devam
- Temkinli Devam
- Kalibrasyon Gerekli
