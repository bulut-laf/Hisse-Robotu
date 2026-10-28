import streamlit as st
import pandas as pd
from app.funds.fund_screener_service import FundScreenerService

def render_fund_screener_tab():
    st.header("📊 TEFAS Fon Tarama ve Sıralama Robotu (Faz 1)")
    st.markdown("Yerli Hisse Senedi Yoğun ve Para Piyasası Fonları Risk-Getiri (Sharpe) Analizi")

    screener = FundScreenerService()
    watchlist = screener.load_watchlist()
    categories = list(watchlist.get("categories", {}).keys())

    if not categories:
        st.warning("zleme listesinde (watchlist) kategori bulunamadı.")
        return

    col1, col2 = st.columns(2)
    with col1:
        selected_category = st.selectbox("Fon Kategorisi Seçin", categories)
    with col2:
        period_months = st.selectbox("Analiz Periyodu", [3, 6, 12], index=1, format_func=lambda x: f"Son {x} Ay")

    if st.button("Fonları Tara ve Sırala", type="primary"):
        with st.spinner("TEFAS verileri taranıyor, metrikler ve Sharpe oranları hesaplanıyor..."):
            ranked_results = screener.get_ranked_funds_for_category(selected_category, months=period_months)
            
            if not ranked_results:
                st.warning("Seçilen kategoride analiz edilebilir fon verisi bulunamadı.")
            else:
                st.success(f"'{selected_category}' kategorisi başarıyla taranarak Sharpe oranına göre sıralandı!")
                
                df_display = pd.DataFrame(ranked_results)
                column_mapping = {
                    "fund_code": "Fon Kodu",
                    "toplam_getiri_yuzde": "Toplam Getiri (%)",
                    "volatilite": "Volatilite (Yıllık %)",
                    "sharpe_orani": "Sharpe Oranı",
                    "veri_nokta_sayisi": "şlem Günü Sayısı"
                }
                df_display = df_display.rename(columns=column_mapping)
                st.dataframe(df_display)