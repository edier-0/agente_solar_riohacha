"""Pagina de predicciones con vista compacta y detalle opcional."""

from datetime import datetime
import os
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_client import api_get, api_post, get_current_user, is_authenticated
from design import render_card, render_hero, render_section_header
from ui import render_user_sidebar


st.set_page_config(page_title="Predicciones", layout="wide", initial_sidebar_state="expanded")
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


def _future_rows(items):
    out = []
    for item in items:
        try:
            fecha = datetime.fromisoformat(item["fecha_objetivo"].replace("Z", ""))
        except Exception:
            continue
        if fecha >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
            out.append((fecha, item))
    return sorted(out, key=lambda row: row[0])


preds_prod = api_get(f"/predicciones/{empresa_id}", params={"tipo": "produccion_solar"}) or []
preds_cons = api_get(f"/predicciones/{empresa_id}", params={"tipo": "consumo"}) or []
preds_cost = api_get(f"/predicciones/{empresa_id}", params={"tipo": "costo"}) or []
preds_risk = api_get(f"/predicciones/{empresa_id}", params={"tipo": "riesgo_apagon"}) or []

prod_fut = _future_rows(preds_prod)
cons_fut = _future_rows(preds_cons)
cost_fut = _future_rows(preds_cost)
risk_fut = _future_rows(preds_risk)

prod_next = prod_fut[0][1]["valor"] if prod_fut else 0
cons_next = cons_fut[0][1]["valor"] if cons_fut else 0
cost_next = cost_fut[0][1]["valor"] if cost_fut else 0
risk_next = risk_fut[0][1]["valor"] if risk_fut else 0
coverage = (prod_next / cons_next * 100) if cons_next else 0
saving = prod_next * empresa_sel.get("tarifa_kwh", 943.0)

if risk_next >= 40:
    risk_title = "Riesgo alto de continuidad"
    risk_body = f"Se estima una probabilidad de {risk_next:.0f}% de interrupcion en 24 horas."
    risk_tone = "danger"
elif risk_next >= 20:
    risk_title = "Riesgo medio de continuidad"
    risk_body = f"Probabilidad estimada de {risk_next:.0f}% en 24 horas."
    risk_tone = "warning"
else:
    risk_title = "Riesgo bajo de continuidad"
    risk_body = f"Probabilidad estimada de {risk_next:.0f}% en 24 horas."
    risk_tone = "success"

render_hero(
    risk_title,
    risk_body if (preds_prod or preds_cons or preds_cost or preds_risk) else "Genera predicciones para ver el panorama de las proximas horas.",
    icon="forecast",
    eyebrow=empresa_sel["nombre"],
    tone=risk_tone if (preds_prod or preds_cons or preds_cost or preds_risk) else "info",
)

top = st.columns(4)
with top[0]:
    render_card("Produccion prevista", value=f"{prod_next:,.0f} kWh", body="Siguiente bloque disponible.", icon="sun", tone="success")
with top[1]:
    render_card("Consumo previsto", value=f"{cons_next:,.0f} kWh", body="Estimacion operativa base.", icon="bolt", tone="info")
with top[2]:
    render_card("Costo previsto", value=f"${cost_next:,.0f}", body="Antes de ajustes operativos.", icon="money", tone="warning")
with top[3]:
    render_card("Cobertura solar", value=f"{coverage:,.0f}%", body=f"Ahorro estimado ${saving:,.0f}.", icon="chart", tone=risk_tone)

st.markdown("""
<style>
/* Bóton Flotante (FAB) para proyecciones */
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

if st.button("Proyectar Escenarios", type="primary", use_container_width=False, help="Calcular proyección de los próximos días"):
    with st.spinner("Consultando pronósticos y calculando escenarios..."):
        resultado = api_post(f"/predicciones/generar/{empresa_id}", params={"horas_horizonte": 72})
        if resultado:
            st.success(f"Predicciones guardadas: {resultado.get('total_predicciones_guardadas', 0)}")
            st.rerun()

st.write("")
render_section_header("Orquestación Autónoma de Respaldo", "spark", "Orquestador inteligente de baterías y excedentes solares ante apagones.")

st.markdown(
    "El Agente Solar de Riohacha implementa un **algoritmo de orquestación proactiva** "
    "que vincula las predicciones de apagones con el control físico del banco de baterías "
    "y los excedentes fotovoltaicos. Ajusta el simulador de abajo para ver cómo responde la IA:"
)

# Slider interactivo
sim_riesgo = st.slider(
    "Simular Probabilidad de Apagón para las próximas 24h (%)",
    min_value=0, max_value=100,
    value=int(risk_next) if risk_next > 0 else 45,
    step=5,
    key="sim_riesgo_slider"
)

# Algoritmo de orquestación
capacidad_bateria = empresa_sel.get("capacidad_bateria_kwh", 0.0)
es_hogar = (empresa_sel.get("tipo") == "hogar")

if capacidad_bateria == 0.0:
    st.info(
        "💡 **Simulador Solar Activo:** Actualmente este perfil no posee un banco de baterías físicas "
        "registrado (capacidad = 0 kWh). A continuación se muestra cómo funcionaría el "
        "Orquestador Autónomo si equiparas tu sistema con el banco de baterías recomendado "
        "para tu tipo de perfil (Hogar recomendado: 5 kWh | PYME recomendado: 30 kWh)."
    )
    bateria_sim = 5.0 if es_hogar else 30.0
else:
    bateria_sim = capacidad_bateria

# Lógica del orquestador basado en el slider
if sim_riesgo >= 40:
    estado_orq = "🔴 MÁXIMA PREVENTIVA"
    desc_orq = (
        "**Acción del Agente IA:** El riesgo de apagón es CRÍTICO. El orquestador ha bloqueado "
        "el uso de la batería para ahorro de OpEx diurno. El 100% de la generación solar sobrante "
        "y energía de la red se destina a cargar las baterías "
        "al 100% de inmediato para asegurar el máximo de horas de respaldo nocturno."
    )
    reserva_target = "100% (Respaldo Total)"
    rutado_solar = "100% a Baterías"
    color_banner = "#B8473F"
elif sim_riesgo >= 20:
    estado_orq = "🟡 RESPALDO PROACTIVO"
    desc_orq = (
        "**Acción del Agente IA:** Riesgo de apagón moderado detectado. El orquestador incrementa el "
        "umbral mínimo de batería (de 20% a 60%). Los excedentes solares de mediodía se desvían de forma "
        "prioritaria al banco de baterías para alcanzar este colchón de seguridad antes del atardecer."
    )
    reserva_target = "60% (Preventivo)"
    rutado_solar = "Batería > Consumo"
    color_banner = "#C88A2E"
else:
    estado_orq = "🟢 OPTIMIZACIÓN OPEX"
    desc_orq = (
        "**Acción del Agente IA:** Riesgo de apagón muy bajo. El orquestador opera en modo de máxima "
        "eficiencia económica: los excedentes solares se inyectan directamente a las cargas internas "
        "para reducir la compra a la red de Air-E, y la batería se descarga de forma "
        "controlada para aplanar la demanda en horas pico."
    )
    reserva_target = "20% (Umbral de Ciclo)"
    rutado_solar = "Consumo Directo (Ahorro)"
    color_banner = "#1E6B5C"

# Mostrar métricas del orquestador
cols_orq = st.columns(4)
with cols_orq[0]:
    st.metric("Modo Orquestador", estado_orq)
with cols_orq[1]:
    st.metric("Objetivo de Carga", reserva_target)
with cols_orq[2]:
    st.metric("Flujo Fotovoltaico", rutado_solar)
with cols_orq[3]:
    consumo_prom = cons_next if cons_next > 0 else (400.0 if not es_hogar else 15.0)
    consumo_hora = (consumo_prom / 24.0)
    pct_carga = 1.0 if sim_riesgo >= 40 else (0.6 if sim_riesgo >= 20 else 0.2)
    autonomia_horas = (bateria_sim * pct_carga) / (consumo_hora if consumo_hora > 0 else 1.0)
    st.metric("Autonomía Apagón", f"{autonomia_horas:.1f} horas")

st.markdown(
    f"""
    <div style="background-color: rgba(30, 30, 30, 0.4); border-left: 4px solid {color_banner}; padding: 15px; border-radius: 4px; margin-bottom: 25px;">
        <p style="margin: 0; font-size: 1rem; color: #f0f2f6;">
            {desc_orq}
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

st.divider()


if prod_fut:
    render_section_header("Proximos dias", "calendar", "Vista compacta del potencial esperado.")
    preview_cols = st.columns(min(len(prod_fut[:5]), 5))
    for index, (fecha, pred) in enumerate(prod_fut[:5]):
        valor = pred["valor"]
        tone = "success" if valor >= cons_next * 0.6 else "warning" if valor >= cons_next * 0.3 else "danger"
        with preview_cols[index]:
            render_card(
                fecha.strftime("%a %d/%m"),
                value=f"{valor:,.0f} kWh",
                body="Produccion proyectada.",
                icon="calendar",
                tone=tone,
            )
elif not (preds_prod or preds_cons or preds_cost or preds_risk):
    st.info("Aun no hay predicciones generadas para esta empresa.")

st.divider()

show_details = st.toggle("Habilitar Gráficos y Modelos Paramétricos", key="pred_detalles", help="Profundiza en las estimaciones por rango de horas e índices de confianza.")
if not show_details:
    st.caption("👈 Activa este interruptor para examinar los gráficos de tendencia, recálculos de horizonte y raw data.")
    st.stop()

render_section_header("Análisis de Tendencias", "chart", "Confianza de la IA, horizontes y desglose tabular.")
st.caption("ℹ️ DNI representa radiación directa normal; en escenarios solares ayuda a estimar el aporte en orientaciones específicas.")

h_col, hr_btn_col = st.columns([1, 3])
with h_col:
    horizonte = st.selectbox("Horizonte a evaluar", [24, 48, 72, 96, 120, 168], index=2, format_func=lambda x: f"Próximas {x}h")
with hr_btn_col:
    st.markdown("<br>", unsafe_allow_html=True)
    # Botón en modo secundario (por defecto) para no invocar las reglas de CSS del botón Primario flotante (FAB)
    if st.button("↻ Recalcular con este horizonte", key="btn_recalc_horizont"):
        with st.spinner("⏳ Actualizando motores de predicción..."):
            resultado = api_post(f"/predicciones/generar/{empresa_id}", params={"horas_horizonte": horizonte})
            if resultado:
                st.success(f"Predicciones actualizadas: {resultado.get('total_predicciones_guardadas', 0)}")
                st.rerun()

tipos_disponibles = {
    "produccion_solar": "Producción solar",
    "consumo": "Consumo",
    "costo": "Costo",
    "riesgo_apagon": "Riesgo de continuidad",
}
tabs = st.tabs(list(tipos_disponibles.values()))
for tab, (tipo_key, tipo_label) in zip(tabs, tipos_disponibles.items()):
    with tab:
        preds = api_get(f"/predicciones/{empresa_id}", params={"tipo": tipo_key})
        if preds:
            df = pd.DataFrame(preds)
            df["fecha_objetivo"] = pd.to_datetime(df["fecha_objetivo"])
            df = df.sort_values("fecha_objetivo")
            unidad = df["unidad"].iloc[0] if "unidad" in df.columns else ""
            confianza = df["confianza_pct"].mean() if "confianza_pct" in df.columns else 0
            metrics = st.columns(3)
            with metrics[0]:
                st.metric("Predicciones", len(df))
            with metrics[1]:
                st.metric("Confianza promedio", f"{confianza:.0f}%")
            with metrics[2]:
                if tipo_key in ("produccion_solar", "consumo", "costo"):
                    st.metric("Total", f"{df['valor'].sum():,.1f} {unidad}".strip())

            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    x=df["fecha_objetivo"],
                    y=df["valor"],
                    name=tipo_label,
                    text=df["valor"].round(1),
                    textposition="outside",
                    marker_color={
                        "produccion_solar": "#C88A2E",
                        "consumo": "#245C81",
                        "costo": "#1E6B5C",
                        "riesgo_apagon": "#B8473F",
                    }.get(tipo_key, "#5C6F69"),
                )
            )
            fig.update_layout(xaxis_title="Fecha", yaxis_title=unidad, height=380)
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df[["fecha_objetivo", "valor", "unidad", "confianza_pct"]], use_container_width=True, hide_index=True)
        else:
            st.info(f"No hay predicciones registradas para {tipo_label.lower()}.")
