# Sprint-182 Rev3 — Görüntü Tabanlı PDF Fallback V1 / Legacy Wiring Uyumluluğu

## Amaç
Metin katmanı bulunmayan veya taranmış PDF bültenlerinin, kullanıcının açık onayıyla Gemini üzerinden yalnız metin çıkarımı yapılarak mevcut **Seans Öncesi Bağlam** akışına aktarılması.

## Rev3 nedeni
Sprint-182 Rev2 hedef testleri geçti ancak tam backend regresyonunda iki eski wiring sözleşmesi başarısız oldu:

- `test_sprint137e2_dashboard_wiring.py::test_market_context_dashboard_is_imported`
- `test_sprint157_rev3_legacy_wiring_compat.py::test_legacy_sprint137e2_import_satiri_korunur`

Kök neden Rev2'nin `backend/dashboard.py` içindeki tarihsel `market_context_dashboard` importunu tamamen `market_context_dashboard_s182` ile değiştirmesiydi.

## Rev3 düzeltmesi
- Tarihsel import satırı **aynen korunur**:
  `from backend.app.ui.market_context_dashboard import render_market_context_dashboard`
- Mevcut route çağrısının adı **değiştirilmez**:
  `render_market_context_dashboard(...)`
- Sprint-182 wrapper ayrı bir alias ile eklenir ve yerel `render_market_context_dashboard` adı kontrollü olarak wrapper'a bağlanır.
- Böylece runtime'da Sprint-182 fallback çalışırken eski Sprint-137E2 / Sprint-157 Rev3 kaynak sözleşmeleri de korunur.
- Rev2'de kullanıcı tarafından görülen iki regresyon testi Rev3 hedef test grubuna özellikle eklenir; tam regresyona kadar beklenmez.

## Değişmeyen güvenlik sınırları
- PDF otomatik olarak arşivlenmez.
- Kullanıcı açık onay vermeden Gemini çağrısı yapılmaz.
- Çıkarılan metin kullanıcı gözden geçirip aktar demeden mevcut bağlam formuna yazılmaz.
- AI yalnız metin çıkarır; özet, AL/SAT, hedef, stop, teknik skor veya fiyat yönü üretmez.
- Haber Merkezi ve teknik/trader motorları değiştirilmez.
- Sağlayıcı hatasında mevcut Metin/TXT/PDF/JPG/PNG akışı korunur.
- Maksimum PDF boyutu 15 MB'dir.

## Beklenen teknik sonuç
Rev2 koşusunda toplam 2965 test toplandı: 2963 geçti, yalnız iki legacy wiring testi başarısız oldu. Rev3'ün hedefi aynı test setinde **2965 passed / 0 failed** sonucudur.
