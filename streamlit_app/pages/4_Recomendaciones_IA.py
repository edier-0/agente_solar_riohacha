"""Pagina de recomendaciones con vista compacta y detalle opcional."""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_client import api_get, api_patch, api_post, get_current_user, is_authenticated
from design import render_card, render_hero, render_section_header
from ui import render_user_sidebar


st.set_page_config(page_title="Recomendaciones IA", layout="wide", initial_sidebar_state="expanded")
render_user_sidebar()

if not is_authenticated():
    st.warning("Debe iniciar sesion primero.")
    st.stop()

user = get_current_user() or {}

empresas = api_get("/empresas/") or []
if not empresas:
    st.warning("Sin empresas disponibles.")
    st.stop()

if user.get("role") == "empresa" and user.get("empresa_id"):
    empresa_id = user["empresa_id"]
    empresa_sel = next((e for e in empresas if e["id"] == empresa_id), empresas[0])
else:
    opciones = {f"{e['nombre']} (ID:{e['id']})": e for e in empresas}
    seleccion = st.selectbox("Empresa", list(opciones.keys()))
    empresa_sel = opciones[seleccion]
    empresa_id = empresa_sel["id"]

recomendaciones = api_get(f"/ia/recomendaciones/{empresa_id}", params={"limit": 30}) or []
pendientes = [r for r in recomendaciones if not r.get("aplicada")]
total_impacto = sum((r.get("impacto_estimado_cop") or 0) for r in pendientes)

render_hero(
    "Recomendaciones priorizadas",
    "Acciones concretas para ahorro, continuidad y mantenimiento sin saturar la vista principal.",
    icon="idea",
    eyebrow=empresa_sel["nombre"],
    tone="success" if pendientes else "info",
)

action_col, stats_col = st.columns([1, 3])
with action_col:
    if st.button("Generar nuevas recomendaciones", type="primary", use_container_width=True):
        with st.spinner("Analizando datos y preparando recomendaciones..."):
            nuevas = api_post(f"/ia/recomendaciones/{empresa_id}")
            if nuevas:
                st.success(f"Se generaron {len(nuevas)} recomendaciones.")
                st.rerun()
with stats_col:
    stats = st.columns(3)
    with stats[0]:
        render_card("Pendientes", value=str(len(pendientes)), body="Acciones aun no aplicadas.", icon="idea", tone="info")
    with stats[1]:
        render_card("Impacto estimado", value=f"${total_impacto:,.0f}", body="Ahorro agregado potencial.", icon="money", tone="success")
    with stats[2]:
        render_card("Aplicadas", value=str(len(recomendaciones) - len(pendientes)), body="Historial reciente.", icon="check", tone="brand")

render_section_header("Acciones sugeridas", "spark", "Lista compacta de mayor valor operativo.")
if not pendientes:
    st.info("No hay recomendaciones pendientes en este momento.")
else:
    icon_map = {
        "ahorro": ("money", "success"),
        "redistribucion": ("chart", "info"),
        "contingencia": ("alert", "danger"),
        "mantenimiento": ("settings", "warning"),
    }
    for rec in pendientes[:8]:
        icon_name, tone = icon_map.get(rec.get("tipo", "ahorro"), ("idea", "info"))
        cols = st.columns([5, 1])
        with cols[0]:
            render_card(
                rec.get("tipo", "recomendacion").replace("_", " ").title(),
                value=f"${(rec.get('impacto_estimado_cop') or 0):,.0f}",
                body=rec.get("texto", ""),
                badge=f"Confianza {rec.get('confianza_pct') or 0:.0f}%",
                icon=icon_name,
                tone=tone,
            )
        with cols[1]:
            if st.button("Aplicar", key=f"apl_{rec['id']}", use_container_width=True):
                api_patch(f"/ia/recomendaciones/{rec['id']}/aplicar")
                st.rerun()

show_details = st.toggle("Ver detalles tecnicos", key="reco_detalles")
if not show_details:
    st.caption("Activa los detalles para revisar el analisis solar y de consumo que soporta estas recomendaciones.")
    st.stop()

render_section_header("Detalle tecnico", "chart", "Contexto de IA, analisis y filtros.")
ia_status = api_get("/ia/status")
if ia_status:
    if ia_status.get("ollama_disponible"):
        st.success(f"Modelo disponible: {ia_status.get('modelo')}")
    else:
        st.warning(f"Modo alterno activo: {ia_status.get('modo')}")
        st.caption("Si activas Ollama, el sistema puede redactar recomendaciones con mayor riqueza contextual.")

analysis_cols = st.columns(2)
with analysis_cols[0]:
    st.markdown("**Analisis solar**")
    analisis_solar = api_get(f"/ia/analisis/solar/{empresa_id}")
    if analisis_solar:
        st.metric("Promedio GHI", f"{analisis_solar.get('promedio_ghi') or 0:.2f} kWh/m2/dia")
        st.metric("Produccion estimada", f"{analisis_solar.get('produccion_estimada_diaria_kwh') or 0:.1f} kWh/dia")
        st.metric("Ahorro mensual", f"${analisis_solar.get('ahorro_estimado_mensual_cop') or 0:,.0f}")
        st.caption(analisis_solar.get("mensaje", ""))
        st.caption("GHI mide la radiacion total horizontal y sirve como referencia general del recurso solar.")

with analysis_cols[1]:
    st.markdown("**Analisis de consumo**")
    analisis_consumo = api_get(f"/ia/analisis/consumo/{empresa_id}")
    if analisis_consumo:
        st.metric("Consumo 30 dias", f"{analisis_consumo.get('total_kwh', 0):.1f} kWh")
        st.metric("Promedio diario", f"{analisis_consumo.get('promedio_diario_kwh', 0):.1f} kWh")
        st.metric("Anomalias", analisis_consumo.get("num_anomalias", 0))
        st.caption(analisis_consumo.get("mensaje", ""))

if recomendaciones:
    tipos = sorted({r.get("tipo") or "ahorro" for r in recomendaciones})
    filtro_tipo = st.multiselect("Filtrar por tipo", tipos, default=tipos)
    mostrar_aplicadas = st.checkbox("Mostrar aplicadas", value=False)
    filtradas = [
        r
        for r in recomendaciones
        if (r.get("tipo") or "ahorro") in filtro_tipo and (mostrar_aplicadas or not r.get("aplicada"))
    ]
    st.dataframe(filtradas, use_container_width=True, hide_index=True)
