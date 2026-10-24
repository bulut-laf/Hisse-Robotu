# Sprint-85 Rev1 — Momentum Kapısı ve Performans Etiketi

Kalibrasyon bulgusu:
- SAHOL ve KCHOL, negatif MACD histogram eğimine rağmen E2/E3 üretmişti.
- TUPRS güçlü olumlu kontrol, THYAO sınırlı hareket örneğiydi.

Düzeltmeler:
- E2-E4 için momentum bileşeni en az 10/20 olmalı.
- Negatif MACD histogram eğimi olan aday en fazla E1 olabilir.
- E3-E4 için RSI eğimi pozitif olmalı.
- Tarihsel sonuçlara performans etiketi eklendi:
  - Başarılı
  - Sınırlı hareket
  - Yanlış pozitif
  - Geç giriş
  - Yetersiz veri
  - Aday değil
- CSV/DataFrame ve Streamlit tarihsel tablo performans etiketini gösterir.

Güvenlik:
- Kesim sonrası fiyatlar aday üretiminde kullanılmaz.
- Bu sprint toplam skor ağırlıklarını değiştirmez; yalnızca zorunlu momentum kapısı ekler.
