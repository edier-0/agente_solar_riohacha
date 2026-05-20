"""Página: Reportes PDF y Excel."""
import streamlit as st
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_client import api_get, api_download, is_authenticated, get_current_user

st.set_page_config(page_title="Reportes", page_icon="📑", layout="wide")

if not is_authenticated():
    st.warning("⚠️ Debe iniciar sesión primero.")
    st.stop()

user = get_current_user() or {}

st.title("📑 Reportes Inteligentes")
st.caption("Exportación PDF (presentación) y Excel (análisis técnico)")

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

col_a, col_b = st.columns(2)
with col_a:
    days = st.slider("Período (días)", min_value=7, max_value=365, value=30)
with col_b:
    st.markdown("""
    **El reporte incluye:**
    - 📊 KPIs y resumen ejecutivo
    - 🤖 Recomendaciones IA con justificación
    - 🚨 Alertas del período
    - 📈 Detalle de consumo, producción, costos
    """)

st.divider()

col_pdf, col_excel = st.columns(2)

with col_pdf:
    st.subheader("📄 Reporte PDF")
    st.markdown(
        "Ideal para **presentación a directivos** y entidades. "
        "Incluye gráficas, tablas y narrativa."
    )
    if st.button("🔽 Generar y descargar PDF", type="primary", use_container_width=True):
        with st.spinner("Generando reporte PDF..."):
            pdf_bytes = api_download(f"/reportes/pdf/{empresa_id}", params={"days": days})
            if pdf_bytes:
                filename = f"reporte_{empresa_sel['nombre'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
                st.download_button(
                    "⬇️ Descargar PDF",
                    data=pdf_bytes,
                    file_name=filename,
                    mime="application/pdf",
                    use_container_width=True,
                )
                st.success("✅ Reporte generado correctamente")
            else:
                st.error("❌ No se pudo generar el PDF")

with col_excel:
    st.subheader("📊 Reporte Excel")
    st.markdown(
        "Ideal para **análisis técnico** posterior. "
        "4 hojas: Resumen, Consumo, Recomendaciones IA, Alertas."
    )
    if st.button("🔽 Generar y descargar Excel", type="primary", use_container_width=True):
        with st.spinner("Generando reporte Excel..."):
            xlsx_bytes = api_download(f"/reportes/excel/{empresa_id}", params={"days": days})
            if xlsx_bytes:
                filename = f"reporte_{empresa_sel['nombre'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx"
                st.download_button(
                    "⬇️ Descargar Excel",
                    data=xlsx_bytes,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
                st.success("✅ Reporte generado correctamente")
            else:
                st.error("❌ No se pudo generar el Excel")
