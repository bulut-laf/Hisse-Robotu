Hedef 24 Sprint 3 — Portföy + Teknik Analiz + AL/SAT karar desteği

Kurulum:
1. ZIP'i D:\Projects\Hisse-Robotu içine çıkarın.
2. PowerShell'de proje köküne geçin: cd D:\Projects\Hisse-Robotu
3. .\Hedef24_Sprint3_Paket\INSTALL_HEDEF24_SPRINT3.ps1
4. Hedef doğrulama:
   .\.venv\Scripts\python.exe -m py_compile backend\app\funds\hedef24_analysis.py backend\app\ui\hedef24_terminal.py backend\dashboard.py
   .\.venv\Scripts\python.exe -m pytest backend\tests\test_hedef24_analysis_sprint3.py backend\tests\test_hedef24_store_sprint2.py -q

Neler yapar:
- Hedef24 JSON portföyünü listeler, fon bilgilerini düzenler, fon ekler/kaldırır.
- Alış bilgisi ve tarihli NAV kaydını saklar; maliyet NAV'ı ve son NAV varsa yüzde K/Z hesaplar.
- Teknik sinyal için en az 21 geçerli NAV gözlemi ister; RSI-14, 20 gözlem momentum ve ortalama hesaplar.
- NAV verisi otomatik çekilmez; kullanıcı tarafından kaydedilen veriye dayanır.
- AL/SAT metinleri karar incelemesi olarak sunulur, emir gönderilmez.
- Dashboard'daki eski Erste Hungary kanıt paneli varsa çağrılır; yoksa Hedef 24 yine açılır.
- Kurulum dashboard.py için yedek oluşturur; fund_analysis_center.py dosyasını değiştirmez.
