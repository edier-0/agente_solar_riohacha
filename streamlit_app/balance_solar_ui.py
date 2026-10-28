"""Panel de un usuario con paneles registrados: producción, consumo, excedentes, batería y red.

Los datos salen de GET /empresas/{id}/balance-solar, que estima la producción con la radiación real de
Open-Meteo (respaldo NASA POWER) y los paneles y baterías de "Mi sistema solar".
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api_client import api_get
from design import render_section_header

COLORES = {
    "produccion": "#C88A2E",
    "consumo": "#245C81",
    "excedente": "#2FA38A",
    "red": "#8A9BA8",
    "bateria": "#4C98D3",
}
FUENTE_CONSUMO = {
    "aparatos": "tus aparatos registrados",
    "perfil": "el consumo diario de tu sistema solar",
    "factura": "tu factura de Air-e",
}


def _kwh(valor) -> str:
    return f"{valor:,.1f} kWh" if valor is not None else "Sin dato"


def _cop(valor) -> str:
    return f"${valor:,.0f}" if valor is not None else "Sin dato"


def _tabla(balance: dict) -> pd.DataFrame:
    df = pd.DataFrame(balance.get("dias") or [])
    if df.empty:
        return df
    df["fecha"] = pd.to_datetime(df["fecha"])
    return df.sort_values("fecha")


def _sombrear_pronostico(fig: go.Figure, df: pd.DataFrame) -> None:
    futuros = df[df["tipo"] == "pronostico"]
    if futuros.empty:
        return
    inicio = futuros["fecha"].min() - pd.Timedelta(hours=12)
    fin = futuros["fecha"].max() + pd.Timedelta(hours=12)
    fig.add_vrect(x0=inicio, x1=fin, fillcolor="rgba(140,155,170,0.12)", line_width=0,
                  annotation_text="Pronóstico", annotation_position="top left")


def render_resumen(balance: dict) -> None:
    resumen = balance.get("resumen") or {}
    hoy = resumen.get("hoy") or {}
    sistema = balance.get("sistema") or {}
    demanda = balance.get("demanda") or {}

    st.markdown("### Resumen Rápido")
    cols = st.columns(4)
    cols[0].metric(
        "Producción solar hoy", _kwh(hoy.get("produccion_kwh")),
        help=f"Radiación de hoy {hoy.get('ghi_kwh_m2') or 0:.2f} kWh/m² × {sistema.get('kwp', 0):g} kWp × "
             f"rendimiento {sistema.get('pr', 0.8) * 100:.0f} %.",
    )
    cols[1].metric(
        "Consumo hoy", _kwh(hoy.get("consumo_kwh")),
        help=f"Estimado con {FUENTE_CONSUMO.get(demanda.get('fuente'), 'tus datos')}.",
    )
    cols[2].metric(
        "Excedente hoy", _kwh(hoy.get("excedente_kwh")),
        help="Energía solar que sobra después de cubrir el consumo y llenar las baterías.",
    )
    bat = hoy.get("bateria_anochecer_pct")
    cols[3].metric(
        "Batería al anochecer", f"{bat:.0f} %" if bat is not None else "Sin baterías",
        help=f"Banco de {sistema.get('numero_baterias', 0)} batería(s), {sistema.get('bateria_kwh', 0):g} kWh. "
             f"Reserva para cortes de luz: {sistema.get('reserva_pct') or 30} %.",
    )
    with st.expander("Ver más KPIs detallados"):
        det = st.columns(4)
        det[0].metric("Tomado de la red hoy", _kwh(hoy.get("red_kwh")),
                      help="Lo que el sol y las baterías no alcanzan a cubrir.")
        det[1].metric("Ahorro solar hoy", _cop(hoy.get("ahorro_cop")),
                      help=f"Energía solar aprovechada × tarifa (${balance.get('tarifa_kwh', 0):,.0f}/kWh).")
        det[2].metric("Cobertura solar", f"{resumen.get('cobertura_pct') or 0:.0f} %",
                      help="Parte del consumo de los últimos días que cubrió el sol (directo o por las baterías).")
        det[3].metric(f"Producción ({resumen.get('dias_con_datos', 0)} días)", _kwh(resumen.get("produccion_kwh")))

    fuentes = ", ".join(balance.get("fuentes_radiacion") or []) or "sin fuente disponible"
    st.caption(f"Radiación real de {fuentes}. {balance.get('metodo', '')}")
    for nota in balance.get("notas") or []:
        st.info(nota)


def _grafica_energia(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["fecha"], y=df["produccion_kwh"], name="Producción solar",
                         marker_color=COLORES["produccion"]))
    fig.add_trace(go.Bar(x=df["fecha"], y=df["excedente_kwh"], name="Excedente",
                         marker_color=COLORES["excedente"]))
    fig.add_trace(go.Bar(x=df["fecha"], y=df["red_kwh"], name="Tomado de la red",
                         marker_color=COLORES["red"]))
    fig.add_trace(go.Scatter(x=df["fecha"], y=df["consumo_kwh"], name="Consumo", mode="lines+markers",
                             line=dict(color=COLORES["consumo"], width=3)))
    if "red_factura_kwh" in df and df["red_factura_kwh"].notna().any():
        fig.add_trace(go.Scatter(x=df["fecha"], y=df["red_factura_kwh"], name="Red según factura",
                                 mode="lines", line=dict(color="#5B6770", width=2, dash="dot")))
    _sombrear_pronostico(fig, df)
    fig.update_layout(barmode="group", xaxis_title="Fecha", yaxis_title="Energía (kWh)", hovermode="x unified",
                      height=460, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig


def _grafica_bateria(df: pd.DataFrame, reserva) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["fecha"], y=df["bateria_anochecer_pct"], name="Al anochecer",
                             mode="lines+markers", line=dict(color=COLORES["bateria"], width=3)))
    fig.add_trace(go.Scatter(x=df["fecha"], y=df["bateria_amanecer_pct"], name="Al amanecer",
                             mode="lines+markers", line=dict(color=COLORES["red"], width=2, dash="dash")))
    if reserva:
        fig.add_hline(y=reserva, line_dash="dot", line_color="#C0392B",
                      annotation_text=f"Reserva {reserva} %", annotation_position="bottom right")
    _sombrear_pronostico(fig, df)
    fig.update_layout(yaxis=dict(title="Carga (%)", range=[0, 105]), xaxis_title="Fecha", hovermode="x unified",
                      height=340, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig


def _grafica_dinero(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["fecha"], y=df["ahorro_cop"], name="Ahorro por energía solar",
                         marker_color=COLORES["excedente"]))
    fig.add_trace(go.Bar(x=df["fecha"], y=df["costo_red_cop"], name="Costo de la energía de la red",
                         marker_color=COLORES["red"]))
    _sombrear_pronostico(fig, df)
    fig.update_layout(barmode="group", xaxis_title="Fecha", yaxis_title="Pesos (COP)", hovermode="x unified",
                      height=420, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig


def render_graficas(empresa_id: int, balance_30: dict) -> None:
    days = st.slider("Periodo de analisis (dias)", min_value=7, max_value=180, value=30,
                     help="Desliza para cambiar el rango de datos en las gráficas.")
    balance = balance_30
    if days != 30:
        otro = api_get(f"/empresas/{empresa_id}/balance-solar", params={"days": days, "pronostico": 3})
        if otro and otro.get("disponible"):
            balance = otro
    df = _tabla(balance)
    resumen = balance.get("resumen") or {}
    sistema = balance.get("sistema") or {}

    tab_operacion, tab_bateria, tab_financiero, tab_solar = st.tabs(["Operación", "Batería", "Financiero", "Entorno Solar"])
    with tab_operacion:
        render_section_header("Producción, consumo y excedentes", "bolt",
                              "Cada día: lo que produjeron los paneles, lo que se consumió, lo que sobró y lo que vino de la red.")
        if df.empty:
            st.info("No hay datos para mostrar.")
        else:
            st.plotly_chart(_grafica_energia(df), use_container_width=True)
            c = st.columns(4)
            c[0].metric("Producción", _kwh(resumen.get("produccion_kwh")))
            c[1].metric("Consumo", _kwh(resumen.get("consumo_kwh")))
            c[2].metric("Excedente", _kwh(resumen.get("excedente_kwh")))
            c[3].metric("Tomado de la red", _kwh(resumen.get("red_kwh")))
            if resumen.get("factura_red_kwh") is not None:
                st.caption(
                    f"En los días con factura, Air-e registró {resumen['factura_red_kwh']:,.1f} kWh tomados de la red; "
                    f"el cálculo de la app da {resumen.get('red_estimada_mismos_dias_kwh') or 0:,.1f} kWh."
                )
    with tab_bateria:
        render_section_header("Carga de las baterías", "battery",
                              f"{sistema.get('numero_baterias', 0)} batería(s) · {sistema.get('bateria_kwh', 0):g} kWh · "
                              f"útiles por ciclo {sistema.get('bateria_util_kwh', 0):g} kWh.")
        if not sistema.get("bateria_kwh"):
            st.info("No hay baterías registradas. Agrégalas en Mi sistema solar.")
        elif not df.empty:
            st.plotly_chart(_grafica_bateria(df, sistema.get("reserva_pct")), use_container_width=True)
            st.caption("De día se cargan con lo que sobra del sol; de noche cubren el consumo hasta la reserva.")
    with tab_financiero:
        render_section_header("Ahorro y costo de la red", "money")
        if not df.empty:
            st.plotly_chart(_grafica_dinero(df), use_container_width=True)
            costo_red = df.loc[df["tipo"] != "pronostico", "costo_red_cop"].dropna().sum()
            c = st.columns(2)
            c[0].metric("Ahorro solar del periodo", _cop(resumen.get("ahorro_cop")))
            c[1].metric("Costo estimado de la red", _cop(costo_red))
    with tab_solar:
        render_section_header("Radiación solar diaria (GHI)", "sun")
        if not df.empty and df["ghi_kwh_m2"].notna().any():
            fig = go.Figure(go.Scatter(x=df["fecha"], y=df["ghi_kwh_m2"], mode="lines+markers", name="GHI",
                                       line=dict(color=COLORES["produccion"], width=2), fill="tozeroy",
                                       fillcolor="rgba(200, 138, 46, 0.1)"))
            _sombrear_pronostico(fig, df)
            fig.update_layout(height=420, hovermode="x unified", yaxis_title="Radiación (kWh/m²/día)", xaxis_title="Fecha")
            st.plotly_chart(fig, use_container_width=True)
            st.caption(f"Fuentes: {', '.join(balance.get('fuentes_radiacion') or [])}.")
        else:
            st.info("Sin datos de radiación.")
