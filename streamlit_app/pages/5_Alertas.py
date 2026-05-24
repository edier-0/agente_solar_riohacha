"""Pagina de alertas con resumen compacto y detalle opcional."""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_client import api_get, api_patch, api_post, get_current_user, is_authenticated
from design import render_card, render_hero, render_section_header
from ui import render_user_sidebar


st.set_page_config(page_title="Alertas", layout="wide", initial_sidebar_state="expanded")
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

solo_no_leidas = st.checkbox("Mostrar solo pendientes", value=True)
alertas_humanizadas = api_get(
    f"/alertas/{empresa_id}/humanizadas",
    params={"solo_no_leidas": solo_no_leidas, "limit": 50},
) or []

rojas = sum(1 for a in alertas_humanizadas if a.get("nivel") == "rojo")
amarillas = sum(1 for a in alertas_humanizadas if a.get("nivel") == "amarillo")
verdes = sum(1 for a in alertas_humanizadas if a.get("nivel") == "verde")
hero_tone = "danger" if rojas else "warning" if amarillas else "success"

render_hero(
    "Centro de Alertas",
    "Visualiza notificaciones operativas críticas. Abre el detalle técnico solo cuando haga falta ajustar los umbrales.",
    icon="alert",
    eyebrow=empresa_sel["nombre"],
    tone=hero_tone,
)

stats = st.columns(3)
with stats[0]:
    render_card("Urgentes", value=str(rojas), body="Requieren accion pronta.", icon="alert", tone="danger")
with stats[1]:
    render_card("Atencion", value=str(amarillas), body="Conviene seguimiento cercano.", icon="spark", tone="warning")
with stats[2]:
    render_card("Informativas", value=str(verdes), body="Sin criticidad inmediata.", icon="check", tone="success")

st.markdown("""
<style>
/* Bóton Flotante (FAB) para evaluar alertas */
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

if st.button("Evaluar Alertas Ahora", type="primary", use_container_width=False, help="Forzar escaneo de umbrales en tiempo real"):
    with st.spinner("Evaluando umbrales y eventos..."):
        creadas = api_post(f"/alertas/evaluar/{empresa_id}")
        if creadas is not None:
            st.success(f"Evaluacion completada. Nuevas alertas: {len(creadas)}")
            st.rerun()

st.divider()
render_section_header("Notificaciones Prioritarias", "alert")
if not alertas_humanizadas:
    st.success("No hay alertas pendientes para esta empresa.")
else:
    tone_map = {"rojo": "danger", "amarillo": "warning", "verde": "success"}
    icon_map = {
        "consumo_alto": "bolt",
        "pico_demanda": "chart",
        "bateria_baja": "battery",
        "baja_radiacion": "cloud",
        "riesgo_apagon": "alert",
    }
    for alerta in alertas_humanizadas:
        cols = st.columns([5, 1])
        with cols[0]:
            render_card(
                alerta.get("titulo", "Alerta"),
                body=alerta.get("mensaje", ""),
                action=alerta.get("accion"),
                badge="Nueva" if not alerta.get("leida") else "Revisada",
                icon=icon_map.get(alerta.get("tipo"), "alert"),
                tone=tone_map.get(alerta.get("nivel"), "info"),
            )
        with cols[1]:
            if not alerta.get("leida"):
                st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
                if st.button("Aceptar", key=f"ok_{alerta['id']}", use_container_width=True):
                    api_patch(f"/alertas/{alerta['id']}/marcar-leida")
                    st.rerun()

st.divider()

show_details = st.toggle("Habilitar Umbrales y Modo Desarrollador", key="alertas_detalles", help="Baja nivel al log técnico y ajusta variables duras.")
if not show_details:
    st.caption("👈 Activa este interruptor para ajustar reglas de Alertas (Radiación mínima, tope de consumo) y ver tabla JSON de logs.")
    st.stop()

render_section_header("Configuración de Umbrales", "settings")
tab_alertas, tab_config = st.tabs(["Log Técnico", "Parámetros del Sistema"])

with tab_alertas:
    alertas = api_get(f"/alertas/{empresa_id}", params={"solo_no_leidas": solo_no_leidas, "limit": 100}) or []
    if alertas:
        st.dataframe(alertas, use_container_width=True, hide_index=True)
    else:
        st.info("Sin alertas tecnicas activas.")

with tab_config:
    st.caption("Referencia: el umbral de radiacion baja ayuda a detectar dias con recurso solar insuficiente; puede apoyarse con GHI historico.")
    config = api_get(f"/alertas/config/{empresa_id}")
    if config:
        with st.form("config_alertas"):
            col_a, col_b = st.columns(2)
            with col_a:
                umbral_consumo = st.number_input(
                    "Umbral consumo diario (kWh)",
                    min_value=0.0,
                    value=float(config.get("umbral_consumo_diario_kwh", 500)),
                    step=10.0,
                )
                umbral_bateria = st.slider(
                    "Umbral bateria baja (%)",
                    min_value=5.0,
                    max_value=50.0,
                    value=float(config.get("umbral_bateria_baja_pct", 20)),
                    step=1.0,
                )
            with col_b:
                umbral_radiacion = st.number_input(
                    "Umbral radiacion baja (kWh/m2/dia)",
                    min_value=0.5,
                    max_value=5.0,
                    value=float(config.get("umbral_radiacion_baja", 2.0)),
                    step=0.1,
                )
                notif_email = st.checkbox("Notificar por email", value=config.get("notificar_email", True))
                notif_dash = st.checkbox("Notificar en dashboard", value=config.get("notificar_dashboard", True))

            if st.form_submit_button("Guardar configuracion", type="primary"):
                payload = {
                    "umbral_consumo_diario_kwh": umbral_consumo,
                    "umbral_bateria_baja_pct": umbral_bateria,
                    "umbral_radiacion_baja": umbral_radiacion,
                    "notificar_email": notif_email,
                    "notificar_dashboard": notif_dash,
                }
                response = api_patch(f"/alertas/config/{empresa_id}", json=payload)
                if response:
                    st.success("Configuracion actualizada.")
                    st.rerun()
