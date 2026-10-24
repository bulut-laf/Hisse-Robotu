# Hisse Robotu — Proje Notları

## Proje bilgisi

- Proje: Hisse Robotu
- Sürüm: 1.1.0
- Platform: Windows / PowerShell / Python
- Python: 3.14.6
- Kullanım amacı: Kişisel BIST teknik analiz ve risk karar desteği
- Son güncelleme: 29 Temmuz 2026

## Güncel durum

Hisse Robotu V1.0 çekirdek işlevleri tamamlanmıştır. Sprint-34 ile Sprint-46 arasında toplu tarama, momentum keşfi, walk-forward doğrulama, işlem kayıp analizi, veri tazeliği güvenlik kilidi ve KAP/VBTS uyum katmanı eklenmiştir.

Bu dosyayla birlikte gelen **V1.1 Kapanış Paketi**, son kritik güvenlik düzeltmelerini uygular ve yalnızca tüm doğrulamalar başarılı olursa V1.1 kapanışını başarılı ilan eder.

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
- CSV/PDF raporları ve analiz geçmişi

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
- V1.1 final tam regresyonu: `V1.1-Kapanis-Kur-ve-Dogrula.ps1` tarafından kullanıcı bilgisayarında bir kez çalıştırılır
- Sistem kontrolü: final paket komutunda `python -m backend.run_system_check` ile çalıştırılır
- Python sözdizimi: final paket komutunda `python -m compileall backend -q` ile doğrulanır

**Önemli:** V1.1 final kapanışı, kullanıcı bilgisayarındaki tam regresyon ve sistem kontrolü başarılı olmadan tamamlanmış sayılmaz.

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

V1.1 ancak aşağıdakilerin tamamı başarılı olduğunda kapanmış sayılır:

1. Kapanış dosyaları yedeklenerek kuruldu.
2. İlgili V1.1 testleri geçti.
3. Tüm `backend/tests` regresyonu geçti.
4. Sistem kontrolü geçti.
5. Python kaynakları sözdizimi kontrolünden geçti.
6. Temiz kaynak ZIP’i ve SHA-256 dosyası üretildi.
7. `RELEASE-V1.1.json` gerçek test sonuçları ve dosya özetleriyle oluşturuldu.
