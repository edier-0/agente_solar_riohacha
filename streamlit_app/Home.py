"""
Agente Solar Inteligente - Frontend Streamlit
Página principal: Login + Landing.
"""
import streamlit as st
from api_client import login, logout, is_authenticated, get_current_user, api_get

st.set_page_config(
    page_title="Agente Solar Inteligente",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="collapsed",
    
    
)

if not is_authenticated():
    st.markdown("""
    <style>

    [data-testid="stSidebar"] {
        display: none;
    }

    [data-testid="collapsedControl"] {
        display: none;
    }

    </style>
    """, unsafe_allow_html=True)
    
# CSS personalizado
st.markdown("""
<style>

   .main-header {
        background: linear-gradient(135deg, #1B4F72 0%, #117A65 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 2rem;
        text-align: center;
    }
    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
    }
    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.95;
    }
    .kpi-card {
        background: white;
        border-left: 4px solid #117A65;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stButton button {
        background-color: #1B4F72;
        color: white;
        border: none;
        padding: 0.5rem 2rem;
        border-radius: 6px;
    }
    .stButton button:hover {
        background-color: #117A65;
        color: white;
    }
</style>
""", unsafe_allow_html=True)


# Header principal
st.markdown("""
<div class="main-header">
    <h1>☀️ Agente Solar Inteligente</h1>
    <p>Dashboard Solar con IA para Ahorro Energético en Riohacha, La Guajira</p>
</div>
""", unsafe_allow_html=True)


# Sidebar: usuario y logout
with st.sidebar:
    st.markdown("### 🌞 Agente Solar",)
    if is_authenticated():
        user = get_current_user()
        if user:
            st.success(f"**{user.get('full_name', 'Usuario')}**")
            st.caption(f"📧 {user.get('email')}")
        if st.button("🚪 Cerrar sesión", use_container_width=True):
            logout()
            st.rerun()
    else:
        st.info("Inicie sesión para continuar")


# Contenido principal según estado
if not is_authenticated():
    col_login, col_info = st.columns([1, 1])

    with col_login:
        st.subheader("🔐 Iniciar sesión")
        with st.form("login_form"):
            email = st.text_input("Correo electrónico", placeholder="usuario@empresa.com")
            password = st.text_input("Contraseña", type="password")
            submit = st.form_submit_button("Ingresar", use_container_width=True)

            if submit:
                if email and password:
                    token = login(email, password)
                    if token:
                        st.success("✅ Sesión iniciada")
                        st.rerun()
                else:
                    st.warning("Complete todos los campos")

        st.divider()
        with st.expander("💡 Credenciales de demostración"):
            st.code("""
Admin:
  email: admin@agentesolar.co
  password: admin123

Empresa Demo (Hotel):
  email: hotel@agentesolar.co
  password: hotel123
            """)

    with col_info:
        st.subheader("🌞 Sobre el Sistema")
        st.markdown("""
        **Agente Solar Inteligente** es una plataforma que combina **datos científicos solares** con
        **agentes IA** para generar recomendaciones automáticas de ahorro energético.

        #### Funcionalidades clave:
        - 📊 Dashboard con KPIs en tiempo real
        - ☀️ Datos solares de NASA POWER y OpenWeather
        - 📁 Carga de consumo desde CSV/Excel
        - 🤖 Recomendaciones IA con Llama 3.2 (Ollama)
        - 🔮 Predicciones a 24-72h
        - 🚨 Sistema de alertas configurables
        - 📑 Reportes PDF y Excel exportables

        #### Stack:
        - **FastAPI** + **MySQL** (Backend / API REST)
        - **Streamlit** (Frontend / Visualización)
        - **Ollama + Llama 3.2** (IA local privada)
        - **NASA POWER**, **OpenWeather**, **CAMS** (Datos solares)

        > Caso ancla: empresas reales de Riohacha (hoteles, hieleras, retail).
        """)
else:
    # Usuario autenticado - mostrar bienvenida
    user = get_current_user() or {}
    st.success(f"### ¡Bienvenido, {user.get('full_name', 'usuario')}!")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(
            "**📊 Dashboard**\n\n"
            "Vea KPIs, gráficas y estado en tiempo real de su empresa."
        )
    with col2:
        st.info(
            "**🤖 Recomendaciones IA**\n\n"
            "Genere sugerencias personalizadas de ahorro con IA."
        )
    with col3:
        st.info(
            "**📑 Reportes**\n\n"
            "Exporte reportes PDF y Excel para directivos."
        )

    st.divider()
    st.markdown("### 👉 Use el menú lateral para navegar por las secciones del sistema.")

    # Estado del sistema
    st.divider()
    col_estado1, col_estado2 = st.columns(2)
    with col_estado1:
        st.markdown("#### 🤖 Estado del Motor IA")
        ia_status = api_get("/ia/status")
        if ia_status:
            if ia_status.get("ollama_disponible"):
                st.success(f"✅ Ollama disponible — Modelo: `{ia_status.get('modelo')}`")
            else:
                st.warning(f"⚠️ Ollama no disponible — Modo: `{ia_status.get('modo')}`")
                st.caption("Las recomendaciones usarán reglas heurísticas (fallback).")

    with col_estado2:
        st.markdown("#### 🏢 Empresas Disponibles")
        empresas = api_get("/empresas/")
        if empresas is not None:
            st.metric("Total accesibles", len(empresas))
            if empresas:
                for e in empresas[:3]:
                    st.caption(f"• **{e['nombre']}** ({e.get('tipo', 'N/A')})")
