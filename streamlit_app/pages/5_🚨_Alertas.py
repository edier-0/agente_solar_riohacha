"""Página: Sistema de Alertas."""
import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_client import api_get, api_post, api_patch, is_authenticated, get_current_user
from ui import render_user_sidebar

st.set_page_config(page_title="Alertas", page_icon="🚨", layout="wide", initial_sidebar_state="expanded")
render_user_sidebar()

if not is_authenticated():
    st.warning("⚠️ Debe iniciar sesión primero.")
    st.stop()

user = get_current_user() or {}

st.title("🚨 Sistema de Alertas")
st.caption("Notificaciones automáticas: consumo alto, batería baja, picos de demanda, baja radiación")

# Selector de empresa
empresas = api_get("/empresas/") or []
if not empresas:
    st.warning("Sin empresas disponibles.")
    st.stop()

if user.get("role") == "empresa" and user.get("empresa_id"):
    empresa_id = user["empresa_id"]
    empresa_sel = next((e for e in empresas if e["id"] == empresa_id), empresas[0])
else:
    opciones = {f"{e['nombre']} (ID:{e['id']})": e for e in empresas}
    sel = st.selectbox("Empresa", list(opciones.keys()))
    empresa_sel = opciones[sel]
    empresa_id = empresa_sel["id"]

tab_alertas, tab_config = st.tabs(["📢 Alertas", "⚙️ Configuración"])

with tab_alertas:
    col_btns = st.columns([1, 1, 3])
    with col_btns[0]:
        if st.button("🔄 Evaluar ahora", type="primary"):
            with st.spinner("Evaluando umbrales..."):
                creadas = api_post(f"/alertas/evaluar/{empresa_id}")
                if creadas is not None:
                    if creadas:
                        st.success(f"✅ {len(creadas)} nuevas alertas creadas")
                    else:
                        st.info("Sin nuevas alertas. Todo dentro de umbrales.")
                    st.rerun()

    with col_btns[1]:
        solo_no_leidas = st.checkbox("Solo no leídas", value=True)

    alertas = api_get(
        f"/alertas/{empresa_id}",
        params={"solo_no_leidas": solo_no_leidas, "limit": 100},
    ) or []

    if alertas:
        # Resumen por severidad
        criticas = sum(1 for a in alertas if a["severidad"] == "critica")
        altas = sum(1 for a in alertas if a["severidad"] == "alta")
        medias = sum(1 for a in alertas if a["severidad"] == "media")
        bajas = sum(1 for a in alertas if a["severidad"] == "baja")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🔴 Críticas", criticas)
        c2.metric("🟠 Altas", altas)
        c3.metric("🟡 Medias", medias)
        c4.metric("🟢 Bajas", bajas)

        st.divider()

        iconos_tipo = {
            "consumo_alto": "⚡",
            "pico_demanda": "📈",
            "bateria_baja": "🔋",
            "baja_radiacion": "☁️",
            "riesgo_apagon": "🔌",
        }
        colores_severidad = {
            "critica": "🔴",
            "alta": "🟠",
            "media": "🟡",
            "baja": "🟢",
        }

        for a in alertas:
            icono = iconos_tipo.get(a["tipo"], "🚨")
            color = colores_severidad.get(a["severidad"], "⚪")

            with st.container(border=True):
                cols = st.columns([4, 1])
                with cols[0]:
                    estado = "" if a["leida"] else " 🆕"
                    st.markdown(f"### {color} {icono} **[{a['tipo'].replace('_', ' ').upper()}]**{estado}")
                    st.write(a["mensaje"])
                    st.caption(f"📅 {a['created_at'][:16]} | Severidad: `{a['severidad']}`")
                with cols[1]:
                    if not a["leida"]:
                        if st.button("✓ Marcar leída", key=f"leida_{a['id']}"):
                            api_patch(f"/alertas/{a['id']}/marcar-leida")
                            st.rerun()
                    else:
                        st.success("Leída")
    else:
        st.info("✨ Sin alertas activas. Todo dentro de los umbrales configurados.")

with tab_config:
    st.subheader("⚙️ Configuración de Umbrales")
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
                    "Umbral batería baja (%)",
                    min_value=5.0, max_value=50.0,
                    value=float(config.get("umbral_bateria_baja_pct", 20)),
                    step=1.0,
                )
            with col_b:
                umbral_radiacion = st.number_input(
                    "Umbral radiación baja (kWh/m²/día)",
                    min_value=0.5, max_value=5.0,
                    value=float(config.get("umbral_radiacion_baja", 2.0)),
                    step=0.1,
                )
                notif_email = st.checkbox(
                    "Notificar por email",
                    value=config.get("notificar_email", True),
                )
                notif_dash = st.checkbox(
                    "Notificar en dashboard",
                    value=config.get("notificar_dashboard", True),
                )

            if st.form_submit_button("💾 Guardar configuración", type="primary"):
                payload = {
                    "umbral_consumo_diario_kwh": umbral_consumo,
                    "umbral_bateria_baja_pct": umbral_bateria,
                    "umbral_radiacion_baja": umbral_radiacion,
                    "notificar_email": notif_email,
                    "notificar_dashboard": notif_dash,
                }
                res = api_patch(f"/alertas/config/{empresa_id}", json=payload)
                if res:
                    st.success("✅ Configuración actualizada")
                    st.rerun()
