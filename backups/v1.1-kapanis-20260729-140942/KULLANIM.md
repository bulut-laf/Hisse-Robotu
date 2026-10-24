# Hisse Robotu V1.0 — Kullanım Kılavuzu

Hisse Robotu kişisel araştırma ve teknik karar desteği amacıyla geliştirilmiştir. Üretilen sonuçlar yatırım tavsiyesi değildir.

## Programı başlatma

Proje klasöründe PowerShell açın ve şu komutu çalıştırın:

```powershell
.\Hisse-Robotu-Baslat.ps1
```

Başlatıcı sanal ortamı ve gerekli paketleri kontrol ederek Streamlit arayüzünü açar.

## Sistem kontrolü

Programın temel dosyalarını ve ana iş akışlarını internet kullanmadan doğrulamak için:

```powershell
python -m backend.run_system_check
```

## Ana analiz modları

### Tek Hisse

Seçilen hissenin geçmiş verisi üzerinde backtest yapar. İşlemleri, toplam getiriyi, kazanma oranını, maksimum düşüşü ve kâr faktörünü gösterir.

### Güncel Teknik Analiz

Bir hisse için haftalık ana trend, günlük yön teyidi, saatlik giriş zamanlaması ve işlem planı üretir. Giriş, stop, hedef ve pozisyon büyüklüğü ayrı ayrı gösterilir.

### Momentum Keşif

BIST evrenini güçlü hareket başlamadan önce veya hareketin ilk aşamasında yakalamak amacıyla tarar. Göreceli güç, 5/20/60 günlük fiyat ivmesi, hacim birikimi, sıkışma, 20 günlük zirve yakınlığı, trend yapısı, likidite ve risk kalitesi birlikte puanlanır.

Sonuç sınıfları:

- **E0 — Sıkışma Oluşuyor:** Fiyat veya ATR aralığı daralıyor; yön henüz kesinleşmemiş.
- **E1 — Hacim Birikimi Başladı:** Son günlerde kademeli hacim artışı var; fiyat yapısı izleniyor.
- **E2 — Dirence Yaklaşıyor:** Fiyat 20 günlük dirence en fazla yaklaşık %5 uzakta.
- **E3 — Kırılım Öncesi Erken Uyarı:** Direnç yakınlığı, göreceli güç eğimi, hacim, RSI/MACD ve trend birlikte hazırlanıyor.
- **B — Kırılım Başladı:** 20 günlük direnç üzerinde hareket başlamış aday.
- **C — İşleme Hazır Aday:** Momentum, mevcut teknik skor ve risk/getiri koşulları birlikte güçlü aday.
- **K — Kalıcı Hazırlık Adayı:** Günlük sınıf geçici olarak zayıflasa da son 30 gündeki tekrarlayan E0-E3 hazırlık sinyalleri nedeniyle izleme listesinde tutulur.
- **D — Aşırı Yükselmiş:** Kısa vadede fazla uzamış; peşinden koşma riski taşıyan hisse.

Momentum skoru doğrudan alım önerisi değildir. E0–E3/B/C sınıfındaki hisseler Güncel Teknik Analiz bölümünde yeniden doğrulanmalıdır. KAP ve şirket haberleri bu sürümde otomatik puanlanmaz; ayrıca kontrol edilmelidir. Tarama sonuçları yerel momentum geçmişine kaydedilir. Adayın listede kaç gündür bulunduğu, ilk görülmeden sonraki getirisi, son sınıf zinciri, yakın direnç ve direnç üzerindeki kırılım tetik seviyesi gösterilir. Günlük koşullarda kısa süreli olarak “İzleme Dışı” kalan bir hisse, yakın geçmişte en az iki E0-E3 hazırlık sinyali üretmişse en fazla 10 günlük hafıza penceresinde **K — Kalıcı Hazırlık Adayı** olarak izlenmeye devam eder.

**Tarihsel yeniden oynatma (walk-forward):** Momentum Keşif ekranındaki bu seçenek, seçilen kesim tarihinden sonraki fiyatları aday üretiminden gizler. Sistem o tarihte hangi hisseleri bulduğunu gösterir. Sonraki 5, 10 ve 20 işlem günündeki kapanış getirileri ayrı tutulur; ayrıca mevcut ileri veri penceresindeki gerçek en yüksek/en düşük fiyat, bu seviyelerin tarihleri, gerçek azami yükseliş ve azami ters hareket hesaplanır. Yakın direnç, kırılım tetik seviyesi ve dirence uzaklık da kesim anındaki değerlerle gösterilir. On veya daha az sembollü özel/kayıtlı listelerde son altı haftalık sınıf zinciri otomatik yeniden üretilir. Kesimde “İzleme Dışı” kalan hisseler de nedenleriyle ayrı tabloda gösterilir. Bu yöntem geleceği görme hatasını azaltır ve GRSEL benzeri hareketlerin gerçekten önceden bulunup bulunamadığını nesnel biçimde test etmeye yarar.

### BIST Toplu Tarama

Seçilen hisse evrenini topluca tarar ve araştırmaya değer adayları sıralar.

Tarama evrenleri:

- Kayıtlı İzleme Listesi
- BIST 30
- BIST 100
- BIST 500
- BIST Tüm
- Özel Liste

Özel Liste kutusu her zaman yazılabilir durumdadır; yalnızca tarama evreni “Özel Liste” seçildiğinde kullanılır. Kayıtlı liste okuyucusu UTF-8 BOM işaretini otomatik temizler.

Tarama profilleri:

- **Gevşek:** Ön eleme için daha fazla sonuç gösterir.
- **Dengeli:** Skor, hacim, teknik görünüm ve risk/getiri koşullarını birlikte uygular.
- **Sıkı:** Yalnızca güçlü, hacim destekli ve pozitif teknik görünümleri gösterir.

Sonuç tablosunda teknik skor, son kapanış, giriş, stop, hedef, risk/getiri, hacim oranı, RSI ve ATR bulunur. “Teknik aday” veya “Teyit bekliyor” ifadeleri kesin alım önerisi değildir; ayrıntılı güncel analizde doğrulanacak araştırma listesidir.

BIST endeks bileşenleri, resmi Borsa İstanbul CSV kaynağından güncellenir. Ağ bağlantısı yoksa program son yerel önbelleği veya paketlenmiş anlık görüntüyü kullanır.

### Açık Pozisyon İzleme

Giriş fiyatı, lot, ilk stop ve hedefleri girilmiş açık pozisyonu güncel verilerle izler. Dinamik stop, açık kâr/zarar ve hedef ilerlemesini gösterir.

### Aynı Veri Karşılaştırması

İki farklı backtest ayarını aynı fiyat verisi üzerinde çalıştırarak ayar değişikliğinin etkisini karşılaştırır.

### Çoklu Hisse Portföyü

Birden fazla hisseyi geçmiş veride birlikte backtest eder. Bu bölüm güncel aday taraması değil, portföy geçmiş performans analizidir.

### Analiz Geçmişi

Kaydedilen tek hisse ve portföy analizlerini listeler, filtreler, karşılaştırır ve güvenli biçimde yedekler.

## Kayıtlı izleme listesi

Kişisel hisse listenizi şu dosyada tutabilirsiniz:

```text
backend\watchlists\favoriler.txt
```

Her satıra bir sembol yazabilir veya virgülle ayırabilirsiniz:

```text
THYAO
ASELS
TUPRS
SAHOL
KCHOL
```

## Programı kapatma

Programın çalıştığı PowerShell terminalinde `Ctrl+C` tuşlarına basın.

## Sorun giderme

Paketleri doğrulamak için:

```powershell
python -m pip check
```

Eksik paketleri kurmak için:

```powershell
python -m pip install -r requirements.txt
```

Bir hata için yardım isterken analiz modu, hisse sembolü, ekrandaki hata mesajı ve terminalin son satırlarını paylaşın.

## İşlem Kayıp Analizi ve Güvenlik Kilidi

Bu bölüm tamamlanmış gerçek veya deneme işlemlerini ayrı günlüklerde inceler. Aracı kurum hesabına bağlanmaz; yalnızca kullanıcı tarafından elle girilen veya CSV ile aktarılan kayıtları kullanır.

Dört alt bölüm bulunur:

- **Kayıp özeti:** Net kâr/zarar, başarı oranı, kâr faktörü, işlem başına beklenti, azami düşüş ve zarar serisini gösterir.
- **İşlem ekle:** Giriş/çıkış, lot, sermaye, stop, hedef, masraf, sinyal sınıfı ve disiplin işaretlerini kaydeder.
- **CSV aktarımı:** Hazır şablonu indirir, tamamlanmış işlemleri topluca içe aktarır ve mevcut günlüğü dışa verir.
- **Yeni işlem ön kontrolü:** Emir göndermeden önce stop, hedef, risk/getiri, pozisyon büyüklüğü, günlük/haftalık zarar ve ardışık zarar sınırlarını kontrol eder.

Varsayılan güvenlik kuralları:

- Stop-loss olmadan yeni işlem açılamaz.
- Minimum risk/getiri oranı 1:2'dir.
- İşlem başına planlanan risk sermayenin %1'ini aşamaz.
- Tek pozisyon sermayenin %30'unu aşamaz.
- Günlük zarar %2'ye veya haftalık zarar %4'e ulaştığında yeni işlem kilitlenir.
- Üç ardışık zarardan sonra yeni işlem kilitlenir.
- Kaybeden pozisyona ekleme ve aşırı yükselmiş bölgede yeni giriş engellenir.

Bu sınırlar kullanıcı tarafından değiştirilebilir. Daha gevşek sınır seçmek riski azaltmaz. Güvenlik kontrolünden geçmek kazanç garantisi veya alım önerisi değildir.

İşlem günlüğünün yerel kayıt dosyası:

```text
C:\Users\<kullanıcı>\.hisse_robotu\islem_gunlugu\islemler.json
```

CSV şablonundaki zorunlu alanlar hesap türü, sembol, giriş/çıkış tarihleri, giriş/çıkış fiyatları, lot ve işlem anındaki sermayedir. Ondalık ayırıcı olarak nokta veya virgül kullanılabilir.
