HISSE ROBOTU — FUND ANALYSIS NON-BLOCKING ENTRY V1

Amaç:
- Fon Analiz Merkezi seçildiğinde otomatik TEFAS ağ çağrısını kaldırır.
- Fon ekranını ve KAP Portföy Raporu içe aktarma alanını anında render eder.
- TEFAS canlı analizi yalnız kullanıcı "TEFAS Verisini Güncelle" düğmesine bastığında çalışır.
- TEFAS yenilemesi başarısız olursa son iyi sonuçlar ve portföy ekranı korunur.

Uygulama:
1. Çalışan Streamlit sürecini Ctrl+C ile durdurun.
2. APPLY-HISSE-ROBOTU-FUND-ANALYSIS-NON-BLOCKING-ENTRY-V1.ps1 dosyasını çalıştırın.
3. Target tests ve full regression PASS sonrası Streamlit'i yeniden başlatın.

Güvenlik:
- AL/SAT değişikliği yok.
- Canonical ranking değişikliği yok.
- KAP ingestion ve snapshot store korunur.
