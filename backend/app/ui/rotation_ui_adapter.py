import pandas as pd
import streamlit as st

def render_rotation_action_plan(st, df_action_plan: pd.DataFrame):
    "`"`"Rotasyon motorundan gelen AL/SAT aksiyon planını Streamlit arayüzüne renkli ve şık bir tablo olarak basar."`"`"
    if df_action_plan is None or df_action_plan.empty:
        st.info("Portföyünüzde şu an bir rotasyon veya değişiklik gerekmiyor.")
        return
        
    st.subheader("🔄 Dönemsel Fon Rotasyonu Aksiyon Planı")
    st.markdown("Sistemin güncel taramalarına göre portföyünüzü **yeniden dengelemek** için aşağıdaki işlemleri yapmalısınız:")
    
    # Aksiyonları renklendirmek için bir fonksiyon
    def highlight_action(val):
        color = 'white'
        if val == 'SAT':
            color = '#ff4b4b' # Kırmızı
        elif val == 'AL':
            color = '#00c04b' # Yeşil
        elif val == 'TUT':
            color = '#fcca46' # Sarı
        return f'color: {color}; font-weight: bold'
        
    # Tabloyu stillendirip ekrana basıyoruz
    styled_df = df_action_plan.style.applymap(highlight_action, subset=['Aksiyon'])
    styled_df = styled_df.format({"Mevcut Bakiye ()": "{:,.2f}", "Hedef Bakiye ()": "{:,.2f}", "Fark ()": "{:,.2f}"})
    
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    st.caption("Not: 'Fark' kolonundaki negatif (-) değerler satılması gereken, pozitif (+) değerler ise alınması gereken tutarları (TL) gösterir.")