"""Página: Dashboard principal con KPIs y gráficas."""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_client import api_get, is_authenticated, get_current_user

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

if not is_authenticated():
    st.warning("⚠️ Debe iniciar sesión primero. Vaya a la página Home.")
    st.stop()

user = get_current_user() or {}

st.title("📊 Dashboard Energético")
st.caption("KPIs en tiempo real, consumo vs producción solar")

# Selector de empresa
empresas = api_get("/empresas/") or []
if not empresas:
    st.warning("No hay empresas registradas. Solicite al admin que cree una.")
    st.stop()

if user.get("role") == "empresa" and user.get("empresa_id"):
    empresa_id = user["empresa_id"]
    empresa_sel = next((e for e in empresas if e["id"] == empresa_id), empresas[0])
else:
    opciones = {f"{e['nombre']} (ID:{e['id']})": e for e in empresas}
    sel = st.selectbox("Seleccione una empresa", list(opciones.keys()))
    empresa_sel = opciones[sel]
    empresa_id = empresa_sel["id"]

st.markdown(f"### 🏢 {empresa_sel['nombre']}")
st.caption(f"Tipo: {empresa_sel.get('tipo', 'N/A')} | Tarifa: ${empresa_sel.get('tarifa_kwh', 0):,.0f} COP/kWh | Paneles: {empresa_sel.get('capacidad_paneles_kw', 0)} kW")

# KPIs
kpis = api_get(f"/consumo/kpis/{empresa_id}")
if kpis:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            "☀️ Radiación actual",
            f"{kpis.get('radiacion_actual_kwh') or 0:.2f} kWh/m²",
            help="Última lectura de NASA POWER",
        )
    with c2:
        st.metric(
            "⚡ Consumo hoy",
            f"{kpis.get('consumo_hoy_kwh') or 0:.1f} kWh",
            help="Consumo acumulado del día",
        )
    with c3:
        st.metric(
            "💰 Costo hoy",
            f"${kpis.get('costo_hoy_cop') or 0:,.0f}",
            help="Costo energético del día",
        )
    with c4:
        ahorro = kpis.get("ahorro_estimado_cop") or 0
        st.metric(
            "💚 Ahorro solar hoy",
            f"${ahorro:,.0f}",
            delta=f"{(ahorro / max(kpis.get('costo_hoy_cop') or 1, 1) * 100):.0f}%",
        )

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        st.metric("🌞 Producción solar hoy", f"{kpis.get('produccion_solar_hoy_kwh') or 0:.1f} kWh")
    with c6:
        st.metric("⚡ Consumo mes", f"{kpis.get('consumo_mes_kwh') or 0:.1f} kWh")
    with c7:
        st.metric("💸 Costo mes", f"${kpis.get('costo_mes_cop') or 0:,.0f}")
    with c8:
        bat = kpis.get("nivel_bateria_pct")
        st.metric("🔋 Batería", f"{bat:.0f}%" if bat is not None else "N/A")

st.divider()

# Gráficas
col_g1, col_g2 = st.columns(2)
days = st.slider("Período de análisis (días)", min_value=7, max_value=180, value=30)

consumos = api_get(f"/consumo/empresa/{empresa_id}", params={"days": days}) or []
radiacion = api_get("/solar/radiacion", params={"days": days}) or []

with col_g1:
    st.subheader("⚡ Consumo vs Producción Solar")
    if consumos:
        df_c = pd.DataFrame(consumos)
        df_c["fecha"] = pd.to_datetime(df_c["fecha"])
        df_c = df_c.sort_values("fecha")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_c["fecha"], y=df_c["consumo_kwh"],
            name="Consumo (kWh)", mode="lines+markers",
            line=dict(color="#E74C3C", width=2),
        ))
        if "produccion_solar_kwh" in df_c.columns:
            fig.add_trace(go.Scatter(
                x=df_c["fecha"], y=df_c["produccion_solar_kwh"],
                name="Producción solar (kWh)", mode="lines+markers",
                line=dict(color="#F39C12", width=2),
                fill="tozeroy", fillcolor="rgba(243, 156, 18, 0.2)",
            ))
        fig.update_layout(
            xaxis_title="Fecha", yaxis_title="kWh",
            hovermode="x unified", height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sin datos de consumo. Cargue un archivo en la sección Consumo.")

with col_g2:
    st.subheader("☀️ Radiación Solar Histórica")
    if radiacion:
        df_r = pd.DataFrame(radiacion)
        df_r["fecha"] = pd.to_datetime(df_r["fecha"])
        df_r = df_r.sort_values("fecha")

        fig = px.line(
            df_r, x="fecha", y="ghi",
            labels={"ghi": "GHI (kWh/m²/día)", "fecha": "Fecha"},
            color_discrete_sequence=["#F1C40F"],
        )
        fig.update_traces(mode="lines+markers", line=dict(width=2))
        fig.update_layout(height=400, hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sin datos de radiación. Vaya a 'Datos Solares' y sincronice con NASA POWER.")

# Costos por día
st.subheader("💰 Costos energéticos por día")
if consumos:
    df_c = pd.DataFrame(consumos)
    df_c["fecha"] = pd.to_datetime(df_c["fecha"])
    df_c["dia"] = df_c["fecha"].dt.date
    df_c["costo_cop"] = df_c["costo_cop"].fillna(df_c["consumo_kwh"] * empresa_sel["tarifa_kwh"])
    df_costos = df_c.groupby("dia").agg({"costo_cop": "sum", "consumo_kwh": "sum"}).reset_index()

    fig = px.bar(
        df_costos, x="dia", y="costo_cop",
        labels={"costo_cop": "Costo (COP)", "dia": "Día"},
        color_discrete_sequence=["#1B4F72"],
    )
    fig.update_layout(height=350)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Sin datos para visualizar costos.")
