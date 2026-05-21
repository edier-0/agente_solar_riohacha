"""Página: Datos solares (NASA POWER + OpenWeather)."""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_client import api_get, api_post, is_authenticated
from ui import render_user_sidebar

st.set_page_config(page_title="Datos Solares", page_icon="☀️", layout="wide", initial_sidebar_state="expanded")
render_user_sidebar()

if not is_authenticated():
    st.warning("⚠️ Debe iniciar sesión primero.")
    st.stop()

st.title("☀️ Datos Solares — Riohacha")
st.caption("Radiación solar, temperatura y meteorología")

st.info(
    "📍 **Ubicación**: Riohacha, La Guajira (11.5444°N, 72.9072°W)  \n"
    "🌞 **Promedio histórico**: 5.5–7.0 kWh/m²/día (uno de los más altos de Colombia)"
)

# Sincronización
st.subheader("🔄 Sincronización con NASA POWER")
col_a, col_b = st.columns([1, 2])
with col_a:
    days_sync = st.number_input("Días a sincronizar", min_value=7, max_value=365, value=30)
    if st.button("🚀 Sincronizar ahora", type="primary"):
        with st.spinner("Consultando NASA POWER API..."):
            data = api_post(f"/solar/sync/nasa", params={"days": days_sync})
            if data is not None:
                st.success(f"✅ {len(data)} registros sincronizados")
                st.rerun()

with col_b:
    st.markdown(
        "**Fuentes integradas:**  \n"
        "✅ NASA POWER API (radiación histórica diaria)  \n"
        "✅ OpenWeather API (clima actual y pronóstico)  \n"
        "⏳ CAMS (próximamente)  \n"
        "⏳ IDEAM (próximamente)"
    )

st.divider()

# Visualización de radiación
st.subheader("📈 Histórico de Radiación Solar")
days_view = st.slider("Período de visualización (días)", 7, 365, 60)
radiacion = api_get("/solar/radiacion", params={"days": days_view})

if radiacion:
    df = pd.DataFrame(radiacion)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df.sort_values("fecha")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("📊 Promedio GHI", f"{df['ghi'].mean():.2f} kWh/m²/día")
    with c2:
        st.metric("⬆️ Máximo GHI", f"{df['ghi'].max():.2f} kWh/m²/día")
    with c3:
        st.metric("⬇️ Mínimo GHI", f"{df['ghi'].min():.2f} kWh/m²/día")
    with c4:
        st.metric("🌡️ Temp. promedio", f"{df['temperatura'].mean():.1f} °C")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["fecha"], y=df["ghi"],
        name="GHI (kWh/m²/día)", mode="lines+markers",
        line=dict(color="#F1C40F", width=2),
        fill="tozeroy", fillcolor="rgba(241, 196, 15, 0.3)",
    ))
    if "dni" in df.columns and df["dni"].notna().any():
        fig.add_trace(go.Scatter(
            x=df["fecha"], y=df["dni"],
            name="DNI", mode="lines",
            line=dict(color="#E67E22", width=1.5, dash="dash"),
        ))
    fig.update_layout(
        xaxis_title="Fecha", yaxis_title="kWh/m²/día",
        height=400, hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Temperatura y nubosidad
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("**🌡️ Temperatura**")
        fig_t = px.line(df, x="fecha", y="temperatura", color_discrete_sequence=["#E74C3C"])
        fig_t.update_layout(height=300, yaxis_title="°C")
        st.plotly_chart(fig_t, use_container_width=True)

    with col_g2:
        st.markdown("**☁️ Nubosidad**")
        if df["nubosidad"].notna().any():
            fig_n = px.area(df, x="fecha", y="nubosidad", color_discrete_sequence=["#85C1E2"])
            fig_n.update_layout(height=300, yaxis_title="%")
            st.plotly_chart(fig_n, use_container_width=True)
else:
    st.info("⚠️ Sin datos. Sincronice con NASA POWER usando el botón arriba.")

st.divider()

# Clima actual y pronóstico
st.subheader("🌤️ Clima Actual y Pronóstico")
col_now, col_forecast = st.columns([1, 2])

with col_now:
    st.markdown("**🌡️ Clima actual**")
    weather = api_get("/solar/weather/current")
    if weather:
        st.metric("Temperatura", f"{weather.get('temperatura', 0):.1f} °C")
        st.metric("Humedad", f"{weather.get('humedad', 0)} %")
        st.metric("Nubosidad", f"{weather.get('nubosidad', 0)} %")
        st.metric("Viento", f"{weather.get('viento_kmh', 0):.1f} km/h")
        st.caption(f"☁️ {weather.get('descripcion', '')}")
        st.caption(f"Fuente: `{weather.get('fuente', '?')}`")

with col_forecast:
    st.markdown("**📅 Pronóstico 5 días (3h)**")
    forecast = api_get("/solar/weather/forecast")
    if forecast:
        df_f = pd.DataFrame(forecast)
        df_f["fecha"] = pd.to_datetime(df_f["fecha"])

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_f["fecha"], y=df_f["temperatura"],
            name="Temperatura (°C)", line=dict(color="#E74C3C"),
        ))
        fig.add_trace(go.Scatter(
            x=df_f["fecha"], y=df_f["nubosidad"],
            name="Nubosidad (%)", line=dict(color="#85C1E2", dash="dash"),
            yaxis="y2",
        ))
        fig.update_layout(
            yaxis=dict(title="°C"),
            yaxis2=dict(title="%", overlaying="y", side="right"),
            height=350, hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True)
