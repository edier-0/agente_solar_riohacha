"""Agente Solar Inteligente - landing and login."""

import streamlit as st

from api_client import api_get, get_current_user, is_authenticated, login, logout
from design import inject_css, inject_style_block, render_card, render_hero, render_section_header, render_sidebar_brand, render_spacer
from ui import _hide_pages_by_user, go_to_login


st.set_page_config(page_title="Agente Solar Inteligente", layout="wide", initial_sidebar_state="expanded")
inject_css()

if not is_authenticated():
    inject_style_block(
        """
        [data-testid="stSidebar"] { display: none; }
        [data-testid="collapsedControl"] { display: none; }
        """
    )
else:
    _hide_pages_by_user()

render_hero(
    "Agente Solar Inteligente",
    "Monitorea consumo, produccion solar, alertas y recomendaciones con una experiencia mas clara y menos cargada.",
    icon="sun",
    eyebrow="Riohacha · gestion energetica asistida",
    tone="brand",
)

with st.sidebar:
    render_sidebar_brand("Agente Solar", "Acceso y navegacion")
    if is_authenticated():
        user = get_current_user()
        if user:
            st.success(user.get("full_name", "Usuario"))
            st.caption(user.get("email", ""))
        if st.button("Cerrar sesion", use_container_width=True):
            logout()
            go_to_login()
    else:
        st.info("Inicia sesion para continuar.")

if not is_authenticated():
    col_login, col_info = st.columns([1, 1.15])

    with col_login:
        render_section_header("Iniciar sesion", "lock", "Acceso para administracion, analisis y operacion.")
        with st.form("login_form"):
            email = st.text_input("Correo electronico", placeholder="usuario@empresa.com")
            password = st.text_input("Contrasena", type="password")
            submit = st.form_submit_button("Ingresar", use_container_width=True)

            if submit:
                if email and password:
                    token = login(email, password)
                    if token:
                        st.success("Sesion iniciada correctamente.")
                        st.rerun()
                else:
                    st.warning("Completa ambos campos.")

        with st.expander("Credenciales de demostracion"):
            st.code(
                "Admin:\n"
                "  email: admin@agentesolar.co\n"
                "  password: admin123\n\n"
                "Empresa Demo:\n"
                "  email: hotel@agentesolar.co\n"
                "  password: hotel123"
            )

    with col_info:
        render_section_header("Resumen del sistema", "dashboard", "Vista general del producto.")
        cards = st.columns(2)
        with cards[0]:
            render_card(
                "Monitoreo operativo",
                body="KPIs, consumo, costos y estado energetico diario con una lectura rapida.",
                icon="chart",
                tone="info",
            )
        with cards[1]:
            render_card(
                "Inteligencia aplicada",
                body="Recomendaciones, predicciones y alertas construidas sobre datos solares y consumo.",
                icon="idea",
                tone="success",
            )
        cards = st.columns(2)
        with cards[0]:
            render_card(
                "Fuentes de datos",
                body="Open-Meteo, NASA POWER, OpenWeather y PVGIS para radiacion, clima y validacion.",
                icon="cloud",
                tone="warning",
            )
        with cards[1]:
            render_card(
                "Casos de uso",
                body="Hoteles, retail, cadena de frio y otras operaciones con sensibilidad a costo y continuidad.",
                icon="factory",
                tone="brand",
            )
else:
    user = get_current_user() or {}
    st.success(f"Bienvenido, {user.get('full_name', 'usuario')}.")

    cols = st.columns(3)
    with cols[0]:
        render_card("Dashboard", body="Consulta KPIs, tendencias y comparativas del negocio.", icon="chart", tone="info")
    with cols[1]:
        render_card("Recomendaciones", body="Prioriza acciones concretas de ahorro y operacion.", icon="idea", tone="success")
    with cols[2]:
        render_card("Reportes", body="Descarga informes listos para seguimiento interno.", icon="report", tone="brand")

    render_spacer()
    st.info("Usa el menu lateral para navegar. Cada modulo inicia en vista compacta y permite abrir detalles tecnicos cuando los necesites.")

    status_cols = st.columns(2)
    with status_cols[0]:
        render_section_header("Motor de recomendaciones", "idea")
        ia_status = api_get("/ia/status")
        if ia_status:
            if ia_status.get("ollama_disponible"):
                st.success(f"Modelo disponible: {ia_status.get('modelo')}")
            else:
                st.warning(f"Modo alterno activo: {ia_status.get('modo')}")
                st.caption("El sistema seguira operando con reglas heuristicas.")

    with status_cols[1]:
        render_section_header("Empresas accesibles", "factory")
        empresas = api_get("/empresas/")
        if empresas is not None:
            st.metric("Total", len(empresas))
            for empresa in empresas[:3]:
                st.caption(f"{empresa['nombre']} · {empresa.get('tipo', 'N/A')}")
