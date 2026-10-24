# Sprint-182 Rev4 — Runtime Wiring Hotfix

Kök neden: `backend/dashboard.py` içinde Sprint-182 alias yönlendirmesinden sonra Sprint-157 legacy yönlendirmesi tekrar çalışıyor ve `render_market_context_dashboard` adını yeniden Sprint-157 wrapper'a bağlıyordu. Bu nedenle Sprint-182 dosyaları kurulu ve testler başarılı olsa bile canlı Streamlit oturumunda aktif modül `backend.app.ui.market_context_dashboard_s157` kalıyordu.

Rev4:
- Sprint-137E2 legacy import satırını korur.
- Sprint-157 alias import ve legacy rebind satırını korur.
- Sprint-182 alias importunu korur.
- Eski Sprint-182 rebind satırını normalize eder ve **son runtime binding** olarak Sprint-182'yi yerleştirir.
- Installer, tam regresyondan önce `backend.dashboard.render_market_context_dashboard.__module__` değerinin `backend.app.ui.market_context_dashboard_s182` olduğunu canlı Python importuyla doğrular.
- Sprint-182 işlevsel çekirdeği değişmez; yalnız runtime wiring ve onun kalıcı regresyon sözleşmesi düzeltilir.
