"""Pagina de dashboard principal."""

from datetime import datetime, timedelta
import os
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_client import api_get, get_current_user, is_authenticated
from design import render_hero, render_section_header
from ui import render_user_sidebar


st.set_page_config(page_title="Dashboard", layout="wide", initial_sidebar_state="expanded")
render_user_sidebar()

if not is_authenticated():
    st.warning("Debe iniciar sesion primero. Vaya a Home.")
    st.stop()

user = get_current_user() or {}

empresas = api_get("/empresas/") or []
if not empresas:
    st.warning("No hay empresas registradas.")
    st.stop()

if user.get("role") == "empresa" and user.get("empresa_id"):
    empresa_id = user["empresa_id"]
    empresa_sel = next((e for e in empresas if e["id"] == empresa_id), empresas[0])
else:
    opciones = {f"{e['nombre']} (ID:{e['id']})": e for e in empresas}
    seleccion = st.selectbox("Selecciona una empresa", list(opciones.keys()))
    empresa_sel = opciones[seleccion]
    empresa_id = empresa_sel["id"]

render_hero(
    "Dashboard energetico",
    f"Tipo: {empresa_sel.get('tipo', 'N/A')} · Tarifa: ${empresa_sel.get('tarifa_kwh', 0):,.0f} COP/kWh · Paneles: {empresa_sel.get('capacidad_paneles_kw', 0)} kW",
    icon="chart",
    eyebrow=empresa_sel["nombre"],
    tone="info",
)

kpis = api_get(f"/consumo/kpis/{empresa_id}")
if kpis:
    cols = st.columns(4)
    with cols[0]:
        st.metric("Radiacion actual", f"{kpis.get('radiacion_actual_kwh') or 0:.2f} kWh/m2")
    with cols[1]:
        st.metric("Consumo hoy", f"{kpis.get('consumo_hoy_kwh') or 0:.1f} kWh")
    with cols[2]:
        st.metric("Costo hoy", f"${kpis.get('costo_hoy_cop') or 0:,.0f}")
    with cols[3]:
        ahorro = kpis.get("ahorro_estimado_cop") or 0
        st.metric("Ahorro solar hoy", f"${ahorro:,.0f}", delta=f"{(ahorro / max(kpis.get('costo_hoy_cop') or 1, 1) * 100):.0f}%")

    cols = st.columns(4)
    with cols[0]:
        st.metric("Produccion solar hoy", f"{kpis.get('produccion_solar_hoy_kwh') or 0:.1f} kWh")
    with cols[1]:
        st.metric("Consumo mes", f"{kpis.get('consumo_mes_kwh') or 0:.1f} kWh")
    with cols[2]:
        st.metric("Costo mes", f"${kpis.get('costo_mes_cop') or 0:,.0f}")
    with cols[3]:
        bat = kpis.get("nivel_bateria_pct")
        st.metric("Bateria", f"{bat:.0f}%" if bat is not None else "N/A")

st.divider()
days = st.slider("Periodo de analisis (dias)", min_value=7, max_value=180, value=30)
consumos = api_get(f"/consumo/empresa/{empresa_id}", params={"days": days}) or []
radiacion = api_get("/solar/radiacion", params={"days": days}) or []

col_g1, col_g2 = st.columns(2)
with col_g1:
    render_section_header("Consumo vs produccion", "bolt")
    if consumos:
        df_c = pd.DataFrame(consumos)
        df_c["fecha"] = pd.to_datetime(df_c["fecha"])
        df_c = df_c.sort_values("fecha")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_c["fecha"], y=df_c["consumo_kwh"], name="Consumo", mode="lines+markers", line=dict(color="#245C81", width=2)))
        if "produccion_solar_kwh" in df_c.columns:
            fig.add_trace(
                go.Scatter(
                    x=df_c["fecha"],
                    y=df_c["produccion_solar_kwh"],
                    name="Produccion solar",
                    mode="lines+markers",
                    line=dict(color="#C88A2E", width=2),
                    fill="tozeroy",
                    fillcolor="rgba(200, 138, 46, 0.2)",
                )
            )
        fig.update_layout(xaxis_title="Fecha", yaxis_title="kWh", hovermode="x unified", height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sin datos de consumo.")

with col_g2:
    render_section_header("Radiacion solar historica", "sun")
    if radiacion:
        df_r = pd.DataFrame(radiacion)
        df_r["fecha"] = pd.to_datetime(df_r["fecha"])
        df_r = df_r.sort_values("fecha")

        fig = px.line(df_r, x="fecha", y="ghi", labels={"ghi": "GHI (kWh/m2/dia)", "fecha": "Fecha"}, color_discrete_sequence=["#C88A2E"])
        fig.update_traces(mode="lines+markers", line=dict(width=2))
        fig.update_layout(height=400, hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sin datos de radiacion.")

render_section_header("Costos energeticos por dia", "money")
if consumos:
    df_c = pd.DataFrame(consumos)
    df_c["fecha"] = pd.to_datetime(df_c["fecha"])
    df_c["dia"] = df_c["fecha"].dt.date
    df_c["costo_cop"] = df_c["costo_cop"].fillna(df_c["consumo_kwh"] * empresa_sel["tarifa_kwh"])
    df_costos = df_c.groupby("dia").agg({"costo_cop": "sum", "consumo_kwh": "sum"}).reset_index()
    fig = px.bar(df_costos, x="dia", y="costo_cop", labels={"costo_cop": "Costo (COP)", "dia": "Dia"}, color_discrete_sequence=["#1E6B5C"])
    fig.update_layout(height=350)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Sin datos para visualizar costos.")
