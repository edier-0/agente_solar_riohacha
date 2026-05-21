"""Pagina de datos solares."""

import os
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_client import api_get, api_post, is_authenticated
from design import render_hero, render_section_header
from ui import render_user_sidebar


st.set_page_config(page_title="Datos Solares", layout="wide", initial_sidebar_state="expanded")
render_user_sidebar()

if not is_authenticated():
    st.warning("Debe iniciar sesion primero.")
    st.stop()

render_hero(
    "Datos solares de Riohacha",
    "Open-Meteo como fuente principal, OpenWeather como complemento y PVGIS como linea base.",
    icon="sun",
    eyebrow="Riohacha, La Guajira",
    tone="warning",
)

st.info("Ubicacion: 11.5444 N, 72.9072 W. Referencia historica de GHI: 5.5 a 7.0 kWh/m2/dia.")

render_section_header("Sincronizacion de datos", "upload")
tab_om, tab_nasa, tab_pvgis = st.tabs(["Open-Meteo", "NASA POWER", "PVGIS"])

with tab_om:
    col_a, col_b = st.columns([1, 2])
    with col_a:
        days_om = st.number_input("Dias a sincronizar", min_value=7, max_value=365, value=30, key="om_days")
        if st.button("Sincronizar Open-Meteo", type="primary", key="om_sync"):
            with st.spinner("Consultando Open-Meteo Archive..."):
                data = api_post("/solar/sync/openmeteo", params={"days": days_om})
                if data is not None:
                    st.success(f"Registros sincronizados: {len(data)}")
                    st.rerun()
    with col_b:
        st.markdown(
            "**Open-Meteo** entrega GHI, DNI y DHI sin API key.\n\n"
            "- Forecast horario hasta 16 dias.\n"
            "- Archivo historico hasta 80 anos.\n"
            "- Calidad del aire para seguimiento de polvo."
        )

with tab_nasa:
    col_a, col_b = st.columns([1, 2])
    with col_a:
        days_nasa = st.number_input("Dias a sincronizar", min_value=7, max_value=365, value=30, key="nasa_days")
        if st.button("Sincronizar NASA POWER", key="nasa_sync"):
            with st.spinner("Consultando NASA POWER..."):
                data = api_post("/solar/sync/nasa", params={"days": days_nasa})
                if data is not None:
                    st.success(f"Registros sincronizados: {len(data)}")
                    st.rerun()
    with col_b:
        st.markdown("NASA POWER se mantiene como respaldo historico y referencia de validacion cruzada.")

with tab_pvgis:
    if st.button("Obtener TMY de Riohacha", key="pvgis_tmy"):
        with st.spinner("Consultando PVGIS..."):
            tmy = api_get("/solar/pvgis/tmy")
            if tmy and tmy.get("disponible"):
                cols = st.columns(3)
                cols[0].metric("GHI promedio", f"{tmy.get('ghi_promedio_diario_kwh_m2', 0):.2f} kWh/m2/dia")
                cols[1].metric("Temperatura promedio", f"{tmy.get('temperatura_promedio_c', 0):.1f} C")
                cols[2].metric("GHI maximo horario", f"{tmy.get('ghi_max_horario_w_m2', 0):.0f} W/m2")
                st.caption("Linea base climatologica para comparar pronosticos y desvio operativo.")
            else:
                st.warning(tmy.get("motivo", "PVGIS no disponible") if tmy else "Sin respuesta")

st.divider()
render_section_header("Historico de radiacion", "chart")
days_view = st.slider("Periodo de visualizacion (dias)", 7, 365, 60)
fuente_filtro = st.selectbox("Fuente", options=["(todas)", "open_meteo", "nasa_power"], index=0)
params_get = {"days": days_view}
if fuente_filtro != "(todas)":
    params_get["fuente"] = fuente_filtro

radiacion = api_get("/solar/radiacion", params=params_get)
if radiacion:
    df = pd.DataFrame(radiacion)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df.sort_values("fecha")

    cols = st.columns(4)
    cols[0].metric("Promedio GHI", f"{df['ghi'].mean():.2f} kWh/m2/dia")
    cols[1].metric("Maximo GHI", f"{df['ghi'].max():.2f} kWh/m2/dia")
    cols[2].metric("Minimo GHI", f"{df['ghi'].min():.2f} kWh/m2/dia")
    if "temperatura" in df.columns and df["temperatura"].notna().any():
        cols[3].metric("Temp. promedio", f"{df['temperatura'].mean():.1f} C")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["fecha"],
            y=df["ghi"],
            name="GHI",
            mode="lines+markers",
            line=dict(color="#C88A2E", width=2),
            fill="tozeroy",
            fillcolor="rgba(200, 138, 46, 0.2)",
        )
    )
    if "dni" in df.columns and df["dni"].notna().any():
        fig.add_trace(go.Scatter(x=df["fecha"], y=df["dni"], name="DNI", mode="lines", line=dict(color="#1E6B5C", width=1.5, dash="dash")))
    fig.update_layout(xaxis_title="Fecha", yaxis_title="kWh/m2/dia", height=400, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Sin datos. Sincroniza una fuente para comenzar.")

st.divider()
render_section_header("Pronostico solar", "forecast", "Referencia tecnica para los proximos dias.")
forecast_om = api_get("/solar/forecast/horario", params={"days": 5})
if forecast_om:
    df_fo = pd.DataFrame(forecast_om)
    df_fo["fecha"] = pd.to_datetime(df_fo["fecha"])

    fig_om = go.Figure()
    fig_om.add_trace(go.Scatter(x=df_fo["fecha"], y=df_fo["ghi_w_m2"], name="GHI (W/m2)", line=dict(color="#C88A2E", width=2), fill="tozeroy", fillcolor="rgba(200, 138, 46, 0.2)"))
    if "dni_w_m2" in df_fo.columns:
        fig_om.add_trace(go.Scatter(x=df_fo["fecha"], y=df_fo["dni_w_m2"], name="DNI (W/m2)", line=dict(color="#1E6B5C", dash="dash")))
    fig_om.add_trace(go.Scatter(x=df_fo["fecha"], y=df_fo["nubosidad"], name="Nubosidad (%)", line=dict(color="#245C81"), yaxis="y2"))
    fig_om.update_layout(yaxis=dict(title="W/m2"), yaxis2=dict(title="%", overlaying="y", side="right"), height=380, hovermode="x unified")
    st.plotly_chart(fig_om, use_container_width=True)

st.divider()
render_section_header("Clima y validacion cruzada", "cloud")
col_now, col_cross = st.columns([1, 2])
with col_now:
    st.markdown("**Clima actual**")
    weather = api_get("/solar/weather/current")
    if weather:
        st.metric("Temperatura", f"{weather.get('temperatura', 0):.1f} C")
        st.metric("Humedad", f"{weather.get('humedad', 0)} %")
        st.metric("Nubosidad", f"{weather.get('nubosidad', 0)} %")
        st.metric("Viento", f"{weather.get('viento_kmh', 0):.1f} km/h")
        st.caption(weather.get("descripcion", ""))
        st.caption(f"Fuente: {weather.get('fuente', '?')}")

with col_cross:
    st.markdown("**Comparacion entre fuentes**")
    if st.button("Comparar fuentes ahora"):
        with st.spinner("Comparando..."):
            cross = api_get("/solar/weather/cross-check")
            if cross:
                delta = cross.get("delta_temperatura_c")
                if cross.get("consistente"):
                    st.success(f"Fuentes consistentes. Delta de temperatura: {delta} C")
                else:
                    st.warning(f"Discrepancia detectada. Delta de temperatura: {delta} C")
                st.json(cross)

    st.markdown("**Calidad del aire**")
    aqi = api_get("/solar/air-quality")
    if aqi and aqi.get("disponible") and aqi.get("datos"):
        primer = aqi["datos"][0]
        cols = st.columns(3)
        cols[0].metric("PM10", f"{primer.get('pm10', 0) or 0:.1f} ug/m3")
        cols[1].metric("PM2.5", f"{primer.get('pm2_5', 0) or 0:.1f} ug/m3")
        cols[2].metric("Polvo", f"{primer.get('polvo', 0) or 0:.1f} ug/m3")
        st.caption("Una carga alta de polvo puede reducir la eficiencia de los paneles.")
