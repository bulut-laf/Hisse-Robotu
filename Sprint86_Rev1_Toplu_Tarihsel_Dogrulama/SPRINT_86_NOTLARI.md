# Sprint-86 Rev1 — Toplu Tarihsel Doğrulama

Amaç:
Ön Yükseliş Hazırlık Motorunu tek bir kesim tarihi yerine çok sayıda hisse ve
çok sayıda tarihsel kesimde kontrollü olarak doğrulamak.

Eklenenler:
- Tarih aralığı ve işlem günü adımıyla kesim tarihi üretimi
- Her sembol için çoklu tarihsel yeniden oynatma
- Çoklu sembol toplu doğrulama
- Minimum hazırlık skoru filtresi
- Başarılı / sınırlı / yanlış pozitif / geç giriş dağılımı
- Başarı ve yanlış pozitif oranı
- Aşama bazlı E1/E2/E3/E4 performans özeti
- CSV/DataFrame için ayrıntılı doğrulama tablosu
- Look-ahead bias regresyon testi

Bu sprintte yok:
- Streamlit toplu doğrulama ekranı
- BIST 100 veri indirme yöneticisi
- Otomatik eşik değişikliği
- Otomatik kalibrasyon kararı

Kritik kural:
Kesim tarihinden sonraki barlar aday üretiminde kullanılmaz; yalnızca ileri
performans etiketi için kullanılır.
