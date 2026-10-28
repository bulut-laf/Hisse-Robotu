import pandas as pd

def render_backtest_results(st, simulation_result: dict):
    "`"`"Backtest motorundan gelen sonuçları Streamlit arayüzüne şık bir şekilde çizer."`"`"
    if not simulation_result:
        st.warning("Simülasyon verisi bulunamadı veya hesaplanamadı.")
        return
        
    st.subheader("📊 Strateji Simülasyonu ve Büyüme Grafiği")
    st.markdown("Seçilen fonlara **Eşit Ağırlıklı** yatırım yapılsaydı portföyün geçmiş performansı ne olurdu?")
    
    # 4'lü Metrik Kartları
    col1, col2, col3, col4 = st.columns(4)
    
    initial = simulation_result["initial_capital"]
    final = simulation_result["final_capital"]
    ret_pct = simulation_result["total_return_pct"]
    mdd_pct = simulation_result["max_drawdown_pct"]
    
    col1.metric("Başlangıç Sermayesi", f"{initial:,.2f} ")
    col2.metric("Güncel Değer", f"{final:,.2f} ", f"{ret_pct}%")
    col3.metric("Net Getiri (%)", f"%{ret_pct}")
    col4.metric("Max Düşüş (Drawdown)", f"%{mdd_pct}", delta_color="inverse")
    
    # Büyüme Eğrisi (Equity Curve) Grafiği
    equity_dict = simulation_result.get("equity_curve", {})
    if equity_dict:
        # Veriyi Streamlit'in seveceği bir DataFrame'e çeviriyoruz
        df_curve = pd.DataFrame(list(equity_dict.items()), columns=["Tarih", "Portföy Büyüklüğü ()"])
        df_curve.set_index("Tarih", inplace=True)
        
        st.line_chart(df_curve, y="Portföy Büyüklüğü ()", use_container_width=True)