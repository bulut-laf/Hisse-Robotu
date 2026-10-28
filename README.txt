Hisse Robotu — Top 10 Next Session Performance Sprint

Kurulum:
1. ZIP içeriğini D:\Projects\Hisse-Robotu proje köküne çıkarın; klasör birleştirmesine izin verin.
2. PowerShell'de:
   Set-Location D:\Projects\Hisse-Robotu
   Set-ExecutionPolicy -Scope Process Bypass
   .\INSTALL_TOP10_NEXT_SESSION.ps1

Yeni arşiv:
backend/data/scan_top10_next_session_performance.json

Bu bağımsız ölçüm katmanı candidate_symbols listesinin ilk 10 sembolünü izler; buy_candidate_symbols ve AL-SAT kararlarını kullanarak aday seçmez. Kapanış verisi bulunamazsa PENDING_DATA üretir. Yeni hedef testler kurulum sırasında çalıştırılır.

Not: Çalışma zamanı fiyat sağlayıcısı geçmiş veriyi güncellediği ölçüde sonuçlar tamamlanır. Testler yalnızca yeni modülün ölçüm davranışını kapsar; tüm proje regresyonu ayrıca çalıştırılmalıdır.
