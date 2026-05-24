"""Agente Solar Inteligente - landing, login and registration."""

import streamlit as st

from api_client import (
    api_get,
    get_active_scenario,
    get_current_user,
    is_authenticated,
    login,
    logout,
    register,
)
from design import (
    inject_css,
    inject_style_block,
    render_card,
    render_hero,
    render_section_header,
    render_sidebar_brand,
    render_spacer,
)
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
        escenario_actual = get_active_scenario()
        escenario_label = "Demo" if escenario_actual == "demo" else "Real"
        st.caption(f"Escenario activo: **{escenario_label}**")
        
        if st.button("Cerrar sesion", use_container_width=True):
            logout()
            go_to_login()
    else:
        st.info("Inicia sesion para continuar.")

if not is_authenticated():
    col_login, col_info = st.columns([1, 1.15])

    with col_login:
        tab_login, tab_register = st.tabs(["🔑 Iniciar Sesión", "📝 Registrarse"])

        with tab_login:
            render_section_header("Iniciar sesion", "lock", "Acceso para administracion, analisis y operacion.")
            with st.form("login_form"):
                email = st.text_input("Correo electronico", placeholder="usuario@empresa.com", key="login_email")
                password = st.text_input("Contrasena", type="password", key="login_pass")
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

        with tab_register:
            render_section_header("Crear una cuenta", "user", "Regístrate gratis para empezar a gestionar tus datos solares.")
            
            perfil = st.radio(
                "Tipo de perfil",
                options=["Hogar / Persona Natural (Comunidad)", "Empresa / PYME"],
                index=0,
                horizontal=True,
                key="reg_perfil"
            )
            
            with st.form("register_form"):
                reg_name = st.text_input("Nombre completo", placeholder="Juan Perez", key="reg_name")
                reg_email = st.text_input("Correo electrónico", placeholder="juan.perez@correo.com", key="reg_email")
                reg_password = st.text_input("Contraseña", type="password", help="Mínimo 6 caracteres", key="reg_pass")
                
                st.write("---")
                
                if perfil == "Hogar / Persona Natural (Comunidad)":
                    nombre_empresa = st.text_input("Nombre de tu Hogar / Familia", placeholder="Familia Pérez Losada", help="Escribe un identificador para tu casa.", key="reg_nombre_empresa")
                    tarifa = st.number_input("Tarifa de energía (COP/kWh)", min_value=100.0, max_value=5000.0, value=943.0, step=10.0, key="reg_tarifa", help="Busca en tu recibo de luz el costo por kWh (en Riohacha ronda los $943 COP).")
                    tipo_empresa = "hogar"
                else:
                    nombre_empresa = st.text_input("Nombre de la empresa", placeholder="Hielera Riohacha o Minimarket", help="Escribe el nombre comercial de tu negocio.", key="reg_nombre_empresa")
                    tarifa = st.number_input("Tarifa comercial (COP/kWh)", min_value=100.0, max_value=5000.0, value=943.0, step=10.0, key="reg_tarifa")
                    tipo_empresa = st.selectbox(
                        "Giro / Tipo Comercial",
                        options=["hotel", "hielera", "retail", "pyme", "comunidad"],
                        index=3,
                        key="reg_tipo_empresa"
                    )

                submit_reg = st.form_submit_button("Registrarse y Comenzar", use_container_width=True)
                
                if submit_reg:
                    if not reg_name or not reg_email or not reg_password or not nombre_empresa:
                        st.warning("Completa todos los campos obligatorios.")
                    elif len(reg_password) < 6:
                        st.warning("La contraseña debe tener al menos 6 caracteres.")
                    else:
                        success = register(
                            email=reg_email,
                            password=reg_password,
                            full_name=reg_name,
                            role="empresa",
                            escenario_usuario="real",
                            nombre_empresa=nombre_empresa,
                            tipo_empresa=tipo_empresa,
                            tarifa_kwh=tarifa
                        )
                        if success:
                            st.success("¡Registro exitoso! Iniciando sesión...")
                            # Iniciar sesión de forma automática
                            token = login(reg_email, reg_password)
                            if token:
                                st.rerun()

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
            if ia_status.get("gemini_disponible"):
                modelo = ia_status.get('modelo', 'Gemini')
                st.success(f"Modelo disponible: {modelo}")
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
