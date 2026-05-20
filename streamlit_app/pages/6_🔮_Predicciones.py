"""Página: Predicciones a 24-72h."""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_client import api_get, api_post, is_authenticated, get_current_user

st.set_page_config(page_title="Predicciones", page_icon="🔮", layout="wide")

if not is_authenticated():
    st.warning("⚠️ Debe iniciar sesión primero.")
    st.stop()

user = get_current_user() or {}

st.title("🔮 Predicciones — 24 a 72 horas")
st.caption("Producción solar, consumo energético, costos y riesgo de apagones")

# Selector empresa
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

# Generar
col_a, col_b = st.columns([1, 2])
with col_a:
    horizonte = st.selectbox("Horizonte", [24, 48, 72, 96, 120, 168], index=2,
                             format_func=lambda x: f"{x} horas ({x // 24} días)")
    if st.button("🔮 Generar predicciones", type="primary"):
        with st.spinner("Consultando pronóstico meteorológico y generando predicciones..."):
            res = api_post(f"/predicciones/generar/{empresa_id}", params={"horas_horizonte": horizonte})
            if res:
                st.success(f"✅ {res.get('total_predicciones_guardadas', 0)} predicciones generadas")
                if res.get("riesgo_apagon_24h_pct"):
                    risk = res["riesgo_apagon_24h_pct"]
                    if risk > 30:
                        st.error(f"⚠️ Riesgo de apagón 24h: {risk}%")
                    elif risk > 15:
                        st.warning(f"⚠️ Riesgo de apagón 24h: {risk}%")
                    else:
                        st.info(f"✅ Riesgo de apagón 24h: {risk}%")
                st.rerun()

with col_b:
    st.info(
        "Las predicciones combinan:  \n"
        "• Pronóstico meteorológico (OpenWeather)  \n"
        "• Capacidad instalada de paneles  \n"
        "• Histórico de consumo (últimos 30 días)  \n"
        "• Heurísticas de riesgo de apagón"
    )

st.divider()

# Visualizar predicciones
tipos_disponibles = {
    "produccion_solar": "🌞 Producción solar",
    "consumo": "⚡ Consumo",
    "costo": "💰 Costo",
    "riesgo_apagon": "🚨 Riesgo apagón",
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
            confianza_prom = df["confianza_pct"].mean()

            c1, c2, c3 = st.columns(3)
            c1.metric("Predicciones", len(df))
            c2.metric("Confianza promedio", f"{confianza_prom:.0f}%")
            if tipo_key in ("produccion_solar", "consumo", "costo"):
                c3.metric(f"Total {unidad}", f"{df['valor'].sum():,.1f}")

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df["fecha_objetivo"], y=df["valor"],
                name=tipo_label,
                text=df["valor"].round(1),
                textposition="outside",
                marker_color={
                    "produccion_solar": "#F39C12",
                    "consumo": "#E74C3C",
                    "costo": "#1B4F72",
                    "riesgo_apagon": "#C0392B",
                }.get(tipo_key, "#7F8C8D"),
            ))
            fig.update_layout(
                xaxis_title="Fecha",
                yaxis_title=unidad,
                height=400,
            )
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("📋 Ver detalle"):
                st.dataframe(
                    df[["fecha_objetivo", "valor", "unidad", "confianza_pct"]],
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            st.info(f"Sin predicciones de tipo `{tipo_key}`. Genere predicciones con el botón arriba.")
