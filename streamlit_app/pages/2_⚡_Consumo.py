"""Página: Carga y gestión de consumo energético."""
import streamlit as st
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_client import api_get, api_post, is_authenticated, get_current_user, API_BASE_URL, API_PREFIX
import requests

st.set_page_config(page_title="Consumo Energético", page_icon="⚡", layout="wide")

if not is_authenticated():
    st.warning("⚠️ Debe iniciar sesión primero.")
    st.stop()

user = get_current_user() or {}

st.title("⚡ Consumo Energético")
st.caption("Carga de datos CSV/Excel y visualización de consumo")

# Selector de empresa
empresas = api_get("/empresas/") or []
if not empresas:
    st.warning("No hay empresas disponibles.")
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

tab1, tab2, tab3 = st.tabs(["📁 Cargar archivo", "📋 Histórico", "✍️ Registro manual"])

with tab1:
    st.markdown("""
    #### Formato esperado del archivo

    **Columnas requeridas:**
    - `fecha` (formato YYYY-MM-DD o YYYY-MM-DD HH:MM:SS)
    - `consumo_kwh` (número)

    **Columnas opcionales:**
    - `costo_cop`, `demanda_pico_kw`, `produccion_solar_kwh`, `nivel_bateria_pct`, `periodo`

    Formatos soportados: **CSV** y **XLSX**.
    """)

    # Plantilla descargable
    plantilla = pd.DataFrame({
        "fecha": ["2026-01-01", "2026-01-02", "2026-01-03"],
        "consumo_kwh": [120.5, 135.2, 110.8],
        "costo_cop": [113550, 127430, 104484],
        "demanda_pico_kw": [15.2, 18.4, 14.1],
        "produccion_solar_kwh": [45.0, 50.2, 42.8],
        "nivel_bateria_pct": [85.0, 78.0, 90.0],
        "periodo": ["diario", "diario", "diario"],
    })
    csv_template = plantilla.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Descargar plantilla CSV",
        data=csv_template,
        file_name="plantilla_consumo.csv",
        mime="text/csv",
    )

    archivo = st.file_uploader("Seleccione archivo CSV o XLSX", type=["csv", "xlsx", "xls"])
    if archivo:
        st.success(f"✅ Archivo seleccionado: **{archivo.name}** ({archivo.size / 1024:.1f} KB)")

        # Preview
        try:
            if archivo.name.endswith(".csv"):
                df_preview = pd.read_csv(archivo)
            else:
                df_preview = pd.read_excel(archivo)
            st.markdown("**Vista previa (primeras 5 filas):**")
            st.dataframe(df_preview.head(), use_container_width=True)
            archivo.seek(0)
        except Exception as e:
            st.error(f"Error leyendo archivo: {e}")

        if st.button("📤 Subir y procesar", type="primary"):
            token = st.session_state.get("token")
            files = {"file": (archivo.name, archivo.getvalue(), archivo.type)}
            try:
                resp = requests.post(
                    f"{API_BASE_URL}{API_PREFIX}/consumo/upload/{empresa_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    files=files,
                    timeout=120,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    st.success(f"✅ {data.get('mensaje')}")
                    st.metric("Registros insertados", data.get("registros_insertados", 0))
                    if data.get("errores"):
                        with st.expander(f"⚠️ Errores ({len(data['errores'])})"):
                            for e in data["errores"][:50]:
                                st.text(e)
                else:
                    detalle = resp.json().get("detail", resp.text)
                    st.error(f"Error {resp.status_code}: {detalle}")
            except Exception as e:
                st.error(f"Error: {e}")

with tab2:
    days = st.slider("Días a mostrar", 7, 365, 30, key="dias_hist")
    consumos = api_get(f"/consumo/empresa/{empresa_id}", params={"days": days})

    if consumos:
        df = pd.DataFrame(consumos)
        df["fecha"] = pd.to_datetime(df["fecha"])
        df = df.sort_values("fecha", ascending=False)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Total registros", len(df))
        with col2:
            st.metric("⚡ Consumo total", f"{df['consumo_kwh'].sum():.1f} kWh")
        with col3:
            costo = df["costo_cop"].fillna(df["consumo_kwh"] * empresa_sel["tarifa_kwh"]).sum()
            st.metric("💰 Costo total", f"${costo:,.0f}")

        st.dataframe(
            df[["fecha", "consumo_kwh", "costo_cop", "demanda_pico_kw",
                "produccion_solar_kwh", "nivel_bateria_pct", "periodo"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Sin registros de consumo.")

with tab3:
    st.markdown("Registre un consumo manualmente:")
    with st.form("registro_manual"):
        col_a, col_b = st.columns(2)
        with col_a:
            fecha = st.date_input("Fecha")
            hora = st.time_input("Hora")
            consumo = st.number_input("Consumo (kWh)", min_value=0.0, step=0.1)
            costo = st.number_input("Costo (COP) — opcional", min_value=0.0, step=100.0)
        with col_b:
            demanda = st.number_input("Demanda pico (kW) — opcional", min_value=0.0, step=0.1)
            produccion = st.number_input("Producción solar (kWh) — opcional", min_value=0.0, step=0.1)
            bateria = st.number_input("Batería (%) — opcional", min_value=0.0, max_value=100.0, step=1.0)
            periodo = st.selectbox("Período", ["diario", "horario", "mensual"])

        if st.form_submit_button("💾 Guardar"):
            from datetime import datetime as dt
            payload = {
                "empresa_id": empresa_id,
                "fecha": dt.combine(fecha, hora).isoformat(),
                "consumo_kwh": consumo,
                "costo_cop": costo or None,
                "demanda_pico_kw": demanda or None,
                "produccion_solar_kwh": produccion,
                "nivel_bateria_pct": bateria or None,
                "periodo": periodo,
            }
            res = api_post("/consumo/", json=payload)
            if res:
                st.success("✅ Registro guardado")
                st.rerun()
