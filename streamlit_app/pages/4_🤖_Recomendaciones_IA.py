"""Página: Recomendaciones IA (Agente de Recomendaciones)."""
import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_client import api_get, api_post, api_patch, is_authenticated, get_current_user
from ui import render_user_sidebar

st.set_page_config(page_title="Recomendaciones IA", page_icon="🤖", layout="wide", initial_sidebar_state="expanded")
render_user_sidebar()

if not is_authenticated():
    st.warning("⚠️ Debe iniciar sesión primero.")
    st.stop()

user = get_current_user() or {}

st.title("🤖 Recomendaciones IA")
st.caption("Agente de Recomendaciones — Llama 3.2 vía Ollama (con fallback de reglas)")

# Estado IA
ia_status = api_get("/ia/status")
if ia_status:
    if ia_status.get("ollama_disponible"):
        st.success(f"✅ **LLM disponible**: {ia_status['modelo']}")
    else:
        st.warning(
            f"⚠️ **Ollama no disponible** — modo `{ia_status.get('modo')}`. "
            "Las recomendaciones usarán reglas heurísticas. "
            "Para activar IA local, instale [Ollama](https://ollama.com) y ejecute `ollama pull llama3.2:3b`."
        )

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

st.markdown(f"### 🏢 {empresa_sel['nombre']}")

# Análisis
col_a, col_b = st.columns(2)
with col_a:
    st.subheader("☀️ Agente de Análisis Solar")
    analisis_solar = api_get(f"/ia/analisis/solar/{empresa_id}")
    if analisis_solar:
        st.metric("Promedio GHI", f"{analisis_solar.get('promedio_ghi') or 0:.2f} kWh/m²/día")
        st.metric("Producción estimada/día", f"{analisis_solar.get('produccion_estimada_diaria_kwh') or 0:.1f} kWh")
        st.metric("Ahorro mensual estimado", f"${analisis_solar.get('ahorro_estimado_mensual_cop') or 0:,.0f}")
        st.caption(analisis_solar.get("mensaje", ""))

with col_b:
    st.subheader("⚡ Agente de Consumo")
    analisis_consumo = api_get(f"/ia/analisis/consumo/{empresa_id}")
    if analisis_consumo:
        st.metric("Consumo total (30d)", f"{analisis_consumo.get('total_kwh', 0):.1f} kWh")
        st.metric("Promedio diario", f"{analisis_consumo.get('promedio_diario_kwh', 0):.1f} kWh")
        st.metric("Anomalías detectadas", analisis_consumo.get("num_anomalias", 0))
        st.caption(analisis_consumo.get("mensaje", ""))

st.divider()

# Generar recomendaciones
st.subheader("💡 Recomendaciones")
col_btn, col_info = st.columns([1, 2])
with col_btn:
    if st.button("✨ Generar nuevas recomendaciones", type="primary"):
        with st.spinner("El Agente IA está analizando datos y generando recomendaciones..."):
            nuevas = api_post(f"/ia/recomendaciones/{empresa_id}")
            if nuevas:
                st.success(f"✅ {len(nuevas)} recomendaciones generadas")
                st.rerun()

with col_info:
    st.info(
        "Las recomendaciones se generan combinando análisis solar, consumo histórico y patrones detectados. "
        "Si Ollama está activo, se usa Llama 3.2 para producir lenguaje natural; si no, se usan reglas heurísticas."
    )

# Listar recomendaciones existentes
recomendaciones = api_get(f"/ia/recomendaciones/{empresa_id}", params={"limit": 30})

if recomendaciones:
    # Filtros
    tipos = sorted({r.get("tipo") or "ahorro" for r in recomendaciones})
    filtro_tipo = st.multiselect("Filtrar por tipo", tipos, default=tipos)
    mostrar_aplicadas = st.checkbox("Mostrar también las aplicadas", value=False)

    filtradas = [
        r for r in recomendaciones
        if (r.get("tipo") or "ahorro") in filtro_tipo
        and (mostrar_aplicadas or not r.get("aplicada"))
    ]

    st.caption(f"Mostrando {len(filtradas)} recomendaciones")

    iconos_tipo = {
        "ahorro": "💰",
        "redistribucion": "🔄",
        "contingencia": "🚨",
        "mantenimiento": "🔧",
    }

    for r in filtradas:
        tipo = r.get("tipo") or "ahorro"
        icono = iconos_tipo.get(tipo, "💡")
        impacto = r.get("impacto_estimado_cop") or 0
        confianza = r.get("confianza_pct") or 0
        aplicada = r.get("aplicada")

        with st.container(border=True):
            cols = st.columns([4, 1])
            with cols[0]:
                titulo = f"{icono} **[{tipo.upper()}]** "
                if aplicada:
                    titulo += "✅ "
                st.markdown(titulo + r["texto"])
                st.caption(
                    f"📅 {r['created_at'][:16]} | "
                    f"💵 Impacto: ${impacto:,.0f} COP | "
                    f"🎯 Confianza: {confianza:.0f}%"
                )
            with cols[1]:
                if not aplicada:
                    if st.button("✓ Marcar aplicada", key=f"apl_{r['id']}"):
                        api_patch(f"/ia/recomendaciones/{r['id']}/aplicar")
                        st.rerun()
                else:
                    st.success("Aplicada")
else:
    st.info("Aún no hay recomendaciones. Haga clic en el botón **Generar nuevas recomendaciones**.")
