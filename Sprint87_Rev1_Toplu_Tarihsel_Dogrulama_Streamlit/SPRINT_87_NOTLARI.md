# Sprint-87 Rev1 — Toplu Tarihsel Doğrulama Streamlit Ekranı

Eklenen analiz modu:
- Ön Yükseliş Toplu Doğrulama

Ekran kontrolleri:
- Hisse listesi
- Başlangıç tarihi
- Bitiş tarihi
- Kesim adımı
- Minimum hazırlık skoru

Çıktılar:
- Toplam kesim sayısı
- Aday sayısı
- Başarı oranı
- Yanlış pozitif oranı
- Performans etiketi dağılımı
- E1/E2/E3/E4 aşama bazlı sonuç tablosu
- Ayrıntılı tarihsel kayıt tablosu
- Ayrıntılı CSV
- Özet CSV

Kritik kural:
Kesim tarihinden sonraki fiyatlar aday üretiminde kullanılmaz.
Bu sprint yalnızca mevcut Sprint-86 doğrulama motorunu görselleştirir;
otomatik kalibrasyon veya eşik değişikliği yapmaz.
