# Sprint-121 — İlk Gerçek Kullanım Değerlendirmesi ve Model Kararı

- Sprint-120 örneklem yeterliliği kararı, ilk gerçek kullanım performans raporuna bağlandı.
- Karar sınıfları: Modeli koru / İncele / Kalibrasyon adayı.
- Başarı oranı, yanlış pozitif oranı, ortalama tetiklenme süresi, deneme portföyü getirisi ve maksimum düşüş birlikte değerlendirilir.
- Örneklem yetersizse iyi görünen ara sonuçlar model değişikliği için kullanılmaz.
- Tek veya iki zayıf ölçüt otomatik kalibrasyon başlatmaz; inceleme önerir.
- Üç veya daha fazla temel zayıflık varsa yalnız kontrollü kalibrasyon adayı üretilir.
- Bu sprint üretim eşiklerini otomatik değiştirmez.
