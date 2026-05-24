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

stats = st.columns(3)
with stats[0]:
    render_card("Pendientes", value=str(len(pendientes)), body="Acciones aun no aplicadas.", icon="idea", tone="info")
with stats[1]:
    render_card("Impacto estimado", value=f"${total_impacto:,.0f}", body="Ahorro agregado potencial.", icon="money", tone="success")
with stats[2]:
    render_card("Aplicadas", value=str(len(recomendaciones) - len(pendientes)), body="Historial reciente.", icon="check", tone="brand")

st.markdown("""
<style>
/* Bóton Flotante (FAB) para generar sugerencias */
div[data-testid="stButton"]:has(button[kind="primary"]) {
    position: fixed !important;
    bottom: 40px !important;
    right: 40px !important;
    width: auto !important;
    z-index: 9999 !important;
}
div[data-testid="stButton"] button[kind="primary"] {
    border-radius: 50px !important;
    padding: 16px 24px !important;
    box-shadow: 0 10px 25px rgba(0,0,0,0.5) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    font-size: 1.05rem !important;
}
</style>
""", unsafe_allow_html=True)

if st.button("✨ Sugerencias IA", type="primary", use_container_width=False, help="Inicia sesión de consultoría con Gemini"):
    with st.spinner("🧠 Analizando datos con Gemini..."):
        nuevas = api_post(f"/ia/recomendaciones/{empresa_id}")
        if nuevas:
            st.success(f"Se generaron {len(nuevas)} recomendaciones.")
            st.rerun()

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

    # Grid dinámico de 3xN columnas
    grid_cols = st.columns(3)
    
    for idx, rec in enumerate(pendientes):
        # Asignar secuencialmente a cada columna
        with grid_cols[idx % 3]:
            icon_name, tone = icon_map.get(rec.get("tipo", "ahorro"), ("idea", "info"))
            
            # Limitar a ~110 caracteres (unas 3 líneas de texto) para uniformidad visual
            texto = rec.get("texto", "")
            texto_truncado = (texto[:107] + "...") if len(texto) > 110 else texto
            
            # Usar la función render_card original para mantener la jerarquía de tipografía e iconos SVG
            render_card(
                rec.get("tipo", "recomendacion").replace("_", " ").title(),
                value=f"${(rec.get('impacto_estimado_cop') or 0):,.0f}",
                body=texto_truncado,
                badge=f"Confianza {rec.get('confianza_pct') or 0:.0f}%",
                icon=icon_name,
                tone=tone,
                tooltip=texto if len(texto) > 110 else None,
            )
            
            # Botón nativo acoplado justo en la base de la tarjeta (sin hacks de containers globales)
            st.markdown("<div style='margin-top: -0.5rem;'></div>", unsafe_allow_html=True)
            if st.button("Aplicar", key=f"apl_{rec['id']}", use_container_width=True):
                api_patch(f"/ia/recomendaciones/{rec['id']}/aplicar")
                st.rerun()
            st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True)

st.divider()

show_details = st.toggle("Habilitar Análisis Técnico y Filtros", key="reco_detalles", help="Revisa el contexto solar y de consumo detallado.")
if not show_details:
    st.caption("👈 Activa este interruptor para revisar el análisis detallado de Gemini y acceder a todas las recomendaciones.")
    st.stop()

render_section_header("Contexto Analítico IA", "chart", "Métricas base evaluadas por Gemini para emitir los consejos.")
ia_status = api_get("/ia/status")
if ia_status:
    if ia_status.get("gemini_disponible"):
        modelo = ia_status.get('modelo', 'Gemini')
        st.success(f"🧠 IA en línea: {modelo} analizando los datos.")
    else:
        st.warning(f"⚠️ Modo degradado activo: {ia_status.get('modo')}")
        st.caption("Sin conexión al LLM, el sistema generará recomendaciones estáticas predecibles.")

analysis_cols = st.columns(2)
with analysis_cols[0]:
    st.markdown("**☀️ Análisis Solar**")
    analisis_solar = api_get(f"/ia/analisis/solar/{empresa_id}")
    if analisis_solar:
        s1, s2, s3 = st.columns(3)
        s1.metric("GHI Promedio", f"{analisis_solar.get('promedio_ghi') or 0:.1f}")
        s2.metric("Producción (kWh)", f"{analisis_solar.get('produccion_estimada_diaria_kwh') or 0:.0f}")
        s3.metric("Ahorro", f"${(analisis_solar.get('ahorro_estimado_mensual_cop') or 0)/1000:,.0f}k")
        st.caption(f"_{analisis_solar.get('mensaje', '')}_")

with analysis_cols[1]:
    st.markdown("**⚡ Análisis de Consumo**")
    analisis_consumo = api_get(f"/ia/analisis/consumo/{empresa_id}")
    if analisis_consumo:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total 30d (kWh)", f"{analisis_consumo.get('total_kwh', 0):,.0f}")
        c2.metric("Promedio diario", f"{analisis_consumo.get('promedio_diario_kwh', 0):,.0f}")
        c3.metric("Anomalías", analisis_consumo.get("num_anomalias", 0))
        st.caption(f"_{analisis_consumo.get('mensaje', '')}_")

st.markdown(" ")
st.markdown("**📚 Histórico de Sugerencias**")
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
