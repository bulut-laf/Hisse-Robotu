# Hisse Robotu — Proje Notları

## Proje bilgisi

- Proje: Hisse Robotu
- Sürüm: 1.1.1
- Platform: Windows / PowerShell / Python
- Python: 3.14.6
- Kullanım amacı: Kişisel BIST teknik analiz ve risk karar desteği
- Son güncelleme: 29 Temmuz 2026

## Güncel durum

Hisse Robotu V1.0 çekirdek işlevleri tamamlanmıştır. Sprint-34 ile Sprint-46 arasında toplu tarama, momentum keşfi, walk-forward doğrulama, işlem kayıp analizi, veri tazeliği güvenlik kilidi ve KAP/VBTS uyum katmanı eklenmiştir.

V1.1 kapanışı 29 Temmuz 2026 tarihinde tamamlandı. V1.1.1 bakım paketi, gerçek kullanım sırasında tespit edilen Güncel Teknik Analiz → Analiz Geçmişi bağlantı eksikliğini giderir ve tüm doğrulamalar başarılı olmadan kurulumu tamamlanmış saymaz.

## Ana yetenekler

- Güncel teknik analiz ve çoklu zaman dilimi teyidi
- Tek hisse ve çoklu hisse backtest
- BIST toplu tarama ve aday sıralama
- Momentum keşif, E0–E3 hazırlık aşamaları ve sinyal hafızası
- Tarihsel yeniden oynatma; kesim tarihinden sonraki veriyi aday üretiminden gizleme
- İşlem planı, stop, hedef, risk/getiri ve pozisyon büyüklüğü
- Açık pozisyon izleme
- İşlem kayıp analizi ve yeni işlem güvenlik ön kontrolü
- Veri tazeliği kilidi
- KAP/VBTS manuel resmî kayıt yönetimi
- VBTS aktif/arşiv yaşam döngüsü
- VBTS yedekleme, geri yükleme, SHA-256 bütünlük kontrolü ve denetim günlüğü
- CSV/PDF raporları; backtest, portföy ve güncel teknik analiz geçmişi

## V1.1 kapanışında düzeltilen kritik noktalar

1. VBTS senkronizasyon veya sağlık hatası artık yalnızca ekranda yazı göstermiyor; toplu tarama düğmesini gerçekten devre dışı bırakıyor.
2. Düğme durumu atlatılsa bile tarama başlamadan önce ikinci bir kod düzeyi güvenlik denetimi çalışıyor.
3. VBTS otomatik senkronizasyonu durum kartlarından önce yapılıyor; ilk ekran açılışında eski durum gösterilmesi önleniyor.
4. Aktif VBTS CSV değişmemişse her Streamlit yeniden çalıştırmasında yeni yedek oluşturulmuyor.
5. Yedek adlarında mikrosaniye kullanılıyor; aynı saniyedeki işlemlerin birbirinin üzerine yazması önleniyor.
6. Senkronizasyon durum dosyası, test veya tarihsel kontrolde verilen gerçek denetim tarihini kaydediyor.
7. Eski yedekler manifestte güvenilir başlangıç kaydı olarak kabul edilmeden önce CSV yapısal doğrulamasından geçiriliyor.
8. Kullanım kılavuzu ve proje notları V1.1 durumuyla eşleştirildi.

## KAP/VBTS güvenlik politikası

KAP/VBTS tedbir kayıtları yalnızca resmî KAP bildiriminden doğrulanarak girilir. Manuel kaynak şeması:

```text
symbol,measure_type,start_date,end_date,source_reference
```

Aşağıdaki durumlarda BIST toplu taraması çalışmaz:

- VBTS kaynağı tanımlı değilse
- Aktif CSV eksik, boş, bozuk veya süresi geçmişse
- Kayıt arşivi ile aktif CSV uyumsuzsa
- Yedek SHA-256 bütünlüğü bozuksa
- Denetim günlüğü okunamıyorsa
- Otomatik senkronizasyon tamamlanamıyorsa
- Resmî KAP referansı doğrulanmamışsa

Süresi dolan kayıtlar aktif filtreden çıkarılır; kullanıcı isterse arşivden ayrıca temizleyebilir.

## Doğrulama durumu

- Sprint-45 son doğrulanmış tam regresyon: **766/766 başarılı**
- Sprint-46 hızlı doğrulama: **57/57 başarılı**
- V1.1 kapanış düzeltmeleri ilgili regresyon grubu: **70/70 başarılı**
- V1.1 final hedefli testleri: **72/72 başarılı**
- V1.1 final tam regresyonu: **788/788 başarılı**
- V1.1 sistem kontrolü: **21 başarılı / 0 uyarı / 0 hata**
- Python kaynak doğrulaması: **239 dosya başarılı**
- V1.1 kapanış durumu: **29 Temmuz 2026 tarihinde tamamlandı**

## Programı başlatma

```powershell
Set-Location D:\Projects\Hisse-Robotu
.\Hisse-Robotu-Baslat.ps1
```

Alternatif:

```powershell
python -m streamlit run backend\dashboard.py
```

## Ana dosyalar

```text
backend/
backend/tests/
data/
database/
docs/
frontend/
Hisse-Robotu-Baslat.ps1
requirements.txt
PROJECT_NOTES.md
KULLANIM_KILAVUZU.md
VERSION
```

## Yerel veriler

Kullanıcıya ait analiz geçmişi, işlem günlüğü, veri önbellekleri, VBTS arşivi, denetim günlüğü ve yedekler kaynak kodun parçası değildir. Final kaynak arşivi oluşturulurken hassas veya çalışma anında üretilen veriler dışarıda bırakılır.

## Bilinen sınırlamalar

- Resmî tatil takvimi otomatik güncellenmez; kapalı gün listesi politika katmanına ayrıca verilebilir.
- KAP/VBTS tedbirleri otomatik web kazıma ile alınmaz; resmî KAP kaydı kullanıcı tarafından doğrulanarak girilir.
- Veri sağlayıcı veya internet erişimi kesilirse güncel analiz ve tarama tamamlanamayabilir.
- Program emir göndermez ve aracı kurum hesabına bağlanmaz.
- Üretilen sonuçlar yatırım tavsiyesi veya kazanç garantisi değildir.

## Kapanış ölçütü

V1.1 kapanışı aşağıdaki ölçütlerle tamamlandı:

1. Kapanış dosyaları yedeklenerek kuruldu.
2. İlgili V1.1 testleri geçti.
3. Tüm `backend/tests` regresyonu geçti.
4. Sistem kontrolü geçti.
5. Python kaynakları sözdizimi kontrolünden geçti.
6. Temiz kaynak ZIP’i ve SHA-256 dosyası üretildi.
7. `RELEASE-V1.1.json` gerçek test sonuçları ve dosya özetleriyle oluşturuldu.


## V1.1.1 — Güncel Teknik Analiz Geçmişi Bakımı

Durum: Paket hazırlandı; kullanıcı ortamında tam doğrulama bekleniyor.

Gerçek kullanım doğrulamasında Güncel Teknik Analiz sonucunun `Analiz Geçmişi`ne kaydedilmediği tespit edildi. V1.1.1 bakım paketi bu eksik zinciri tamamlar.

Eklenenler:

- Başarılı ve veri tazeliği kilidini geçen Güncel Teknik Analiz sonucunun otomatik kaydı.
- Sembol, fiyat veri tarihi, teknik teyit skoru/durumu, işlem kararı ve plan tipi.
- Giriş bölgesi, referans giriş, stop-loss, hedef 1/2 ve risk/ödül alanları.
- Sermaye, azami risk oranı, risk bütçesi, lot, pozisyon tutarı ve planlanan risk.
- Veri, teknik analiz ve işlem planı kimlikleri.
- Güncel analiz özetini UTF-8 CSV olarak indirme.
- Güncel analiz kayıtlarının mevcut analiz geçmişi ZIP yedekleme/geri yükleme zincirine dahil edilmesi.
- Güncel analiz kayıtlarının backtest performans özeti ve karşılaştırmasına karıştırılmaması.
- Eski V1.1 metadata kayıtlarıyla geriye dönük uyumluluk.

V1.1.1 sürüm doğrulaması, hedefli testler, tam `backend/tests` regresyonu, sistem kontrolü ve Python sözdizimi kontrolü başarıyla geçmeden tamamlanmış sayılmaz.
