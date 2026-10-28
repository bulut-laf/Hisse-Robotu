import streamlit as st

def render_portfolio_alerts(st, alerts: list[dict]):
    """Arka plandan gelen risk uyarılarını Streamlit arayüzüne banner olarak basar."""
    if not alerts:
        st.success("✅ Portföy Risk Analizi: Tüm metrikler (Drawdown ve Likidite) güvenli sınırlar içinde.")
        return
        
    st.subheader("🚨 Risk ve Erken Uyarı Radarı")
    
    for alert in alerts:
        if alert["level"] == "CRITICAL":
            st.error(f"**{alert['title']}**\n\n{alert['message']}")
        elif alert["level"] == "WARNING":
            st.warning(f"**{alert['title']}**\n\n{alert['message']}")
        else:
            st.info(f"**{alert['title']}**\n\n{alert['message']}")