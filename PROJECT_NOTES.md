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


## Sprint-47 — Piyasa Rejimi ve Endeks Analizi

Durum: Uygulama paketi hazırlandı; kullanıcı ortamı kurulumu ve son kullanıcı doğrulaması bekleniyor.

Eklenenler:

- XU100, XU030 ve XUTUM için günlük/haftalık piyasa rejimi motoru.
- Pozitif, Seçici ve Riskli sınıflandırması.
- Trend, momentum, hacim, kırılım ve nötr başlangıçlı piyasa genişliği skorları.
- Saatlik veri bulunamadığında analizi durdurmadan devam etme.
- Eski günlük veride güvenlik kilidi.
- Endeksler için işlem planı, lot, stop ve hedef üretmeme.
- Streamlit Piyasa Rejimi ekranı ve üç endeks karşılaştırması.
- pytest.ini ile backups/releases test toplama çakışmasının kalıcı biçimde önlenmesi.

## Sprint-68 — Temel Analiz V1 Kapanışı

Durum: Otomatik kapanış paketi hazırlandı; kullanıcı ortamında hedef test, tam regresyon ve görsel doğrulama bekleniyor.

Temel Analiz V1 kapsamı:

- Dönemsel finansal veri modeli ve veri tazeliği kilidi
- Manuel CSV/JSON ve yapılandırılabilir KAP veri kaynağı
- Finansal oranlar ve 0–100 temel kalite skoru
- Kârlılık, büyüme, borçluluk, likidite ve nakit akışı alt skorları
- Temel skor yerel deposu ve dönemsel geçmiş
- Şirket ve sektör karşılaştırmaları
- Sektör bazlı temel skor sıralaması
- Sektör güç haritası ve dönemsel sektör değişimi
- Temel analiz CSV/PDF özet raporu
- Rapor arşivi, geçmiş rapor karşılaştırması, arama ve filtreleme
- Filtrelenmiş CSV ve seçilmiş raporlar için toplu PDF
- Temel analiz ayarları ve varsayılan değerlere güvenli dönüş
- Teknik skor, BIST taraması ve VBTS güvenlik zincirinden ayrıştırma
- Alım/satım tavsiyesi üretmeme ilkesi

Kapanış doğrulaması tamamlanmadan Temel Analiz V1 tamamlanmış sayılmaz. Gerekli ölçütler:

1. Sprint-68 hedef testlerinin tamamı geçmelidir.
2. Tüm `backend/tests` regresyonu geçmelidir.
3. `python -m backend.run_system_check` kullanıma hazır sonucu vermelidir.
4. `python -m compileall backend -q` hatasız tamamlanmalıdır.
5. Streamlit Temel Analiz ekranında görsel kontrol yapılmalıdır.
6. CSV ve PDF indirme düğmeleri gerçek dosya üretmelidir.
7. Rapor arşivi ve ayar dosyaları yerel olarak oluşturulmalıdır.
8. Temel Analiz V1 snapshot ZIP’i ve SHA-256 özeti üretilmelidir.


## Sprint-69–74 — Teknik Analiz V1.2

Durum: Kapanış doğrulama paketi hazırlandı. Kullanıcı ortamındaki hedef test,
tam regresyon, sistem kontrolü, Python sözdizimi kontrolü ve snapshot üretimi
başarıyla tamamlanmadan sürüm kapanmış sayılmaz.

Teknik Analiz V1.2 kapsamı:

- RSI ve MACD histogram için normal pozitif/negatif uyumsuzluk
- RSI ve MACD histogram için gizli pozitif/negatif uyumsuzluk
- Günlük ve haftalık uyumsuzluk analizi
- Pivot mesafesi, belirginlik, hacim teyidi ve güven düzeyi
- Günlük/haftalık teknik karar matrisi
- İzlemeye Değer / Temkinli İzle / Uygun Değil sınıflandırması
- Olumlu ve olumsuz gerekçelerin ayrı gösterimi
- 5/10/20 işlem günü sinyal sonuç takibi
- Kapanış getirisi, MFE, MAE, hedef ve stop ölçümü
- Gösterge mevcut/yok katkı karşılaştırması
- Minimum örnek güvenlik kilidi
- Tekrarlayan gösterge adaylarının analizi
- Zamansal olarak ayrılmış walk-forward eğitim ve doğrulama pencereleri
- Kalite, ATR, risk/getiri, trend, momentum, hacim ve uyumsuzluk kalibrasyonu
- Kararlı bölge / İzlenebilir / Aşırı uyum riski değerlendirmesi
- CSV dışa aktarımları
- Gelecek fiyatların yalnızca sonuç ölçümünde kullanılması
- Alım/satım tavsiyesi veya kazanç garantisi üretmeme

Teknik Analiz V1.2 kapanış ölçütleri:

1. Sprint-69–73 hedef testlerinin tamamı geçmelidir.
2. Tüm `backend/tests` regresyonu geçmelidir.
3. `python -m backend.run_system_check` kullanıma hazır sonucu vermelidir.
4. `python -m compileall backend -q` hatasız tamamlanmalıdır.
5. Dashboard'da uyumsuzluk, karar matrisi, sinyal sonuçları, gösterge katkısı
   ve walk-forward ekranları açılmalıdır.
6. Sonuç, katkı ve kalibrasyon CSV indirmeleri gerçek dosya üretmelidir.
7. Teknik Analiz V1.2 kaynak snapshot ZIP'i oluşturulmalıdır.
8. Snapshot için SHA-256 özeti ve release JSON kaydı oluşturulmalıdır.

Canlı veri, emir defteri ve scalping entegrasyonu bu sürümün kapsamında değildir.
Bu alanlar günlük/haftalık sistemin gerçek ve gölge işlem sonuçları yeterli örnek
oluşturduktan sonra yeniden değerlendirilecektir.


---

## Hisse Robotu V1.3 — Operasyon ve Kalibrasyon Zinciri

**Sprint kapsamı:** Sprint-75–81

Tamamlanan ana başlıklar:

- Sprint-75 — Gecikmeli Veri Pilotu
- Sprint-76 — Günlük Operasyon Paneli
- Sprint-77 — Otomatik Sinyal Kaydı ve Sonuç Güncelleme
- Sprint-78 — Gölge Portföy ve İşlem Günlüğü
- Sprint-79 — Haftalık Performans Raporu
- Sprint-80 — Başarı Karşılaştırması
- Sprint-81 — V1.3 Kalibrasyon Kararı ve Snapshot

V1.3 kalibrasyon kararı; gecikmeli veri ölçümleri, tamamlanan 5/10/20 günlük
sinyal sonuçları, gölge portföy kapanışları ve yeterli örnekleme ulaşan
rejim/sektör/gösterge karşılaştırmalarını birlikte değerlendirir.

Karar sınıfları:

- Devam
- Temkinli Devam
- Kalibrasyon Gerekli

Gecikmeli gün içi veri kesin işlem sinyali değildir. Gölge Portföy gerçek emir
göndermez ve gerçek para kullanmaz. Snapshot yalnızca hedef testler, tam
regresyon ve sistem kontrolü başarılı olduktan sonra oluşturulur.

## Seans Sonu Alis Adaylari — V7 Kapanisi

**Tarih:** 2026-10-09

**Hedef testler:** 7 passed  
**Tam regresyon:** 4155 passed, 1 skipped, 0 failed

Tamamlananlar:
- 5 dakikalik gun ici hareket kaniti.
- Veri tazeligi ve aday dogrulama katmani.
- Kapanis davranisi kaniti.
- Seans sonu karar kapisi: ALIS_ADAYI / BEKLE / ELENDI.
- EodCandidateOutput: yalnizca mevcut adaylari aktarir ve siralamayi korur.
- Mevcut Top-5 aday secim mantigi degistirilmedi.

Notlar:
- BOM kaynakli test toplama sorunu giderildi.
- Nanosecond donusum uyarisi hata olmadigi icin sonraki bakima birakildi.
- Tavan serisi ve Gunun 5 Hissesi arastirmasi aktif sprintler tamamlanana kadar ertelendi.

## Seans Sonu Alis Adaylari - V8 Kapanisi

**Tarih:** 2026-10-09

**Hedef testler:** 42 passed, 0 failed
**Tam regresyon:** 4156 passed, 1 skipped, 0 failed
**Uyari:** delayed_data_pilot.py:288 nanosecond donusum uyarisi devam ediyor; testleri basarisiz yapmadi.

Tamamlananlar:
- Canonical close akisi mevcut EVENING karar zincirine delege olmaya devam eder.
- EOD dogrulama katmani mevcut adaylarin sirasini koruyarak ayri cikti arsivine yazar.
- EOD arsivleme hatalari mevcut karar sonucunu degistirmeyecek sekilde izole edildi.
- Top-5 aday secim mantigi degistirilmedi.

Arsiv durumu:
- Arsiv kaydi bulundu; son kayit tarihi: 2026-08-28, durum: NO_CANDIDATES.

## V9 PERFORMANCE MEASUREMENT CLOSEOUT

Date: 2026-10-09

### Validation result
- Full regression: 4170 passed, 1 skipped, 0 failed.
- Runtime: 311.36 seconds.
- One known non-failing warning remains: nanosecond conversion in `backend/app/data/delayed_data_pilot.py:288`.
- V9 measurement validation tests: 3 passed.
- Synthetic tests cover T+1/T+3/T+5 returns, MFE/MAE, same-day deferral, and data-fetch failure isolation.

### V9 components
- V9A: EOD candidate performance contract and separate JSON archive.
- V9B: Runtime settlement using market data and base-date reference prices.
- V9C Rev1: Historical settlement and best-effort scheduled hook.
- Performance validation pack added no production-source changes.

### Operational limitation
The current EOD archive contained one historical NO_CANDIDATES record dated 2026-08-28. A safe isolated settlement saved a performance record with candidate_count 0. Actual candidate-level performance remains unverified until normal production flow records candidates and sufficient future market sessions are available.

### Safety and architecture
- Do not manually trigger the production canonical close for validation.
- Performance settlement must not change the legacy AL/BEKLE decision chain, candidate ordering, or buy symbols.
- Keep the EOD performance archive separate from the existing decision archive.
- Next: after a normal session produces EOD candidates, verify T+1/T+3/T+5 settlement.

## Dashboard Menu Order Fix - 2026-10-16

- Status: PASS
- Scope: Sorted the ANALIZ_MODLARI menu in backend/dashboard.py using Turkish alphabetical order.
- Integrity: 27 menu items; 27 unique items.
- Dashboard backup: backend/dashboard.py.menu-order.bak
- Full regression: 4188 passed, 1 skipped, 1 warning.
- Duration: 277.21 seconds (4 minutes 37 seconds).
- Failed tests: 0.
- Scope protection: No AL-SAT functionality or trading decision logic was intentionally changed.
- Next step: Continue the current active sprint; do not start another module until the current sprint is complete.

## Sprint-1 — Opportunity Radar Kapanış Kontrolü (2026-10-16)

- Target tests: 24 passed in 8.14 seconds.
- Full regression, latest run: 4188 passed, 1 skipped, 1 warning.
- Latest full regression duration: 266.41 seconds.
- Failed tests: 0.
- Git status: Git repository not detected at project root; no repository initialization performed.
- Scope protection: No intentional changes to existing AL-SAT functionality or trading decision logic.
- Remaining verification: Identify the skipped test and warning details before marking all closure checks fully verified.

## Sprint-1 — Son Regresyon Doğrulaması (2026-10-16)

- Tam regresyon: 4189 passed, 0 failed.
- Süre: 248.78 saniye.
- Uyarılar: 293; ayrı inceleme gerekli.
- Finansal kabul testi: 1 passed; gerçek TUPRS fixture yolu düzeltildi.
- Fixture: backend/tests/fixtures/financial_intelligence/TUPRS_1643116_2026_2.xls
- AL-SAT motoru: Bu doğrulama kapsamında değiştirilmedi.
- Sonraki adım: Uyarıları sınıflandır ve kaynaklarını incele.

## Sprint-1 — SQLite Bağlantı ve Regresyon Kapanışı (2026-10-16)

- SQLite bağlantı kapatma: `scan_history.py` ve `scan_history_reader.py` bağlantı blokları düzeltildi.
- Hedef test: `test_scan_history_reader.py` — 7 passed.
- Uyarı kontrolü: hedef testte `ResourceWarning` / `unclosed database` bulunmadı.
- lişkili testler: 14 passed, 4175 deselected.
- Gecikmeli veri hedef testleri: 9 passed.
- Tam regresyon: 4189 passed, 0 failed; 228.41 saniye.
- Kalan uyarı: `backend/app/data/delayed_data_pilot.py:288`, nanosaniye hassasiyeti dönüşümü.
- AL-SAT motoru: değiştirilmedi.
- Durum: test regresyonu başarılı; kalan uyarı engelleyici değil, ayrı takip edilecek.

## Sprint-1 - Ortak Nihai Aday Seçimi V1 Entegrasyon Kapanışı (2026-10-17)

- Durum: PASS
- Kapsam: Ortak Nihai Aday Seçimi V1 modülü ve aday adaptörlerinin Opportunity Radar panosuna salt okunur entegrasyonu.
- Görünüm: Ortak aday listesi; hisse, kaynaklar, zaman dilimleri, kanıt sayısı, veri durumu ve gerekçeler.
- Karar güvenliği: Liste AL-SAT kararı üretmez; mevcut AL-SAT karar zincirinin değiştirilmesi amaçlanmadı.
- Hedef testler: 15 passed, 0 failed.
- Tam regresyon: 4189 passed, 0 failed.
- Tam regresyon süresi: 299.03 saniye.
- Yedek: `backend/app/ui/opportunity_radar_dashboard.py.sprint1_common_candidates.bak`
- Git: Proje kökünde Git deposu tespit edilmedi; depo başlatılmadı.
- Sonraki adım: Opportunity Radar panosunu uygulamada açıp gerçek sonuçlarla ortak aday tablosunu görsel olarak doğrula. Ardından sprint kapanışını tamamla.

## Sprint-2 - Gemini Aday De?erlendirmesi Kapan??? (2026-10-17)

- Durum: PASS
- Kapsam: Ortak Nihai Aday Listesi i?in iste?e ba?l?, salt okunur Gemini de?erlendirme mod?l? ve F?rsat Radar? aray?z entegrasyonu.
- G?venlik: Gemini aday s?ralamas?n? ve AL-SAT kararlar?n? de?i?tirmez; otomatik i?lem yetkisi NONE.
- Hedef testler: 11 passed, 0 failed.
- F?rsat Radar? hedef testleri: 7 passed, 0 failed.
- Birle?ik do?rulama: 42 passed, 0 failed.
- Tam regresyon: 4195 passed, 0 failed; 276.49 saniye.
- Kaynak do?rulamas?: Test dosyas?ndaki UTF-8 BOM kald?r?ld?; Streamlit API uyumluluk ve sistem kontrol? testleri yeniden ge?ti.
- Canl? aray?z do?rulamas?: F?rsat Radar? PDF ??kt?s?nda Gemini de?erlendirme b?l?m? ve GLYHO de?erlendirmesi g?r?nt?lendi.
- Sa?lay?c?/model: gemini / gemini-3.5-flash-lite.
- De?erlendirme s?n?r?: GLYHO ??kt?s? do?rulama eksiklerini ve eksik teknik alanlar? belirtti; al?m-sat?m karar? ?retmedi.
- Git: Proje k?k?nde Git deposu tespit edilmedi; depo ba?lat?lmad?.
- AL-SAT motoru: Bu sprint kapsam?nda de?i?tirilmedi.
- Yedek: PROJECT_NOTES.md.sprint2_gemini_closure_20261017_214316.bak
- Sonraki ad?m: Yeni bir sprint ba?latmadan ?nce bu kapan?? kayd?n? ve canl? aray?z do?rulamas?n? referans al.


## Erste Hungary Official Eligibility UI - 2026-10-18

- Restored `backend/app/ui/fund_analysis_center.py` from the validated pre-official-status backup after detecting text corruption.
- Added read-only official status columns to the Erste Hungary F1-F4 Evidence view: official status, ranking eligibility, last official NAV date, and source.
- Funds without a matching official-status record display `HAYIR` for ranking eligibility; this UI display does not integrate the status data into production ranking.
- Official status artifact: `_discovery/erste_hungary/official_fund_status_review_v1.json`.
- Targeted tests: `test_erste_hungary_official_eligibility_view_v1.py` - 2 passed; `test_fund_analysis_center_ui_v1.py` - 7 passed.
- Full regression was not run.
- Production decisions and rank history were not intentionally modified.
- Safety invariants: `automatic_trade_authority = NONE`; `forced_fill = False`.
- Follow-up: separately assess any future production-ranking integration; do not infer fund investability from the UI eligibility label alone.


## Regression Closure - 2026-10-22

- Status: PASS
- Latest reported full regression: 4201 passed, 0 failed; 314.11 seconds.
- Erste Hungary F1-F4 evidence surface: 929 records; canonical IDs unique.
- Evidence classification test now validates record count, allowed classifications, and unique IDs without hardcoding the distribution.
- Target tests: 12 passed.
- Focused system-check test: 1 passed.
- Production evidence data and AL-SAT decision chain were not intentionally changed in this closure.
- Safety invariants: automatic_trade_authority = NONE; forced_fill = False.
- Note: a separate regression report file was not located; the test result is recorded from the verified console output.
