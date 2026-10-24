# Sprint-84 Rev1 — Ön Yükseliş Hazırlık Streamlit Ekranı

Eklenen analiz modu:
- Ön Yükseliş Hazırlık

Çalışma türleri:
- Güncel hazırlık
- Tarihsel yeniden oynatma

Kontroller:
- Hisse listesi
- Minimum gösterim skoru
- Maksimum son gün primi
- Tarihsel kesim tarihi

Çıktılar:
- Hazırlık skoru ve E1–E4 aşaması
- Dirence uzaklık, RSI, MACD histogram eğimi
- Hacim 3/10 oranı ve ATR daralması
- Son gün getirisi ve risk/ödül
- Olumlu işaretler ve riskler
- Tarihsel modda 1/3/5/10/20 günlük performans
- CSV dışa aktarımı

Güvenlik:
- Kesim sonrası fiyatlar aday üretiminde kullanılmaz.
- Yüksek primli hisseler erken aday sayılmaz.
- Veri tazeliği ve VBTS güvenlik mantığı değiştirilmez.
