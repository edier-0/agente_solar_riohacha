"""Componentes compartidos de interfaz para Streamlit."""
import streamlit as st

from api_client import get_current_user, is_authenticated, logout


def hide_admin_page_for_non_admin() -> None:
    """Oculta el enlace de Administracion en el menu para usuarios no admin."""
    user = get_current_user() or {}
    if user.get("role") == "admin":
        return

    st.markdown(
        """
        <style>
        [data-testid="stSidebarNav"] li:has(a[href*="Administracion"]),
        [data-testid="stSidebarNav"] li:has(a[href*="Administraci%C3%B3n"]),
        [data-testid="stSidebarNav"] div:has(> a[href*="Administracion"]),
        [data-testid="stSidebarNav"] div:has(> a[href*="Administraci%C3%B3n"]),
        [data-testid="stSidebarNav"] a[href*="Administracion"],
        [data-testid="stSidebarNav"] a[href*="Administraci%C3%B3n"] {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def go_to_login() -> None:
    """Envia al usuario al Home/login."""
    st.switch_page("Home.py")


def render_user_sidebar() -> None:
    """Muestra datos del usuario y boton de cierre de sesion en el sidebar."""
    if not is_authenticated():
        go_to_login()

    hide_admin_page_for_non_admin()

    with st.sidebar:
        st.markdown("### 🌞 Agente Solar")
        user = get_current_user()
        if user:
            st.success(f"**{user.get('full_name', 'Usuario')}**")
            st.caption(f"📧 {user.get('email')}")
        if st.button("🚪 Cerrar sesión", use_container_width=True, key="sidebar_logout"):
            logout()
            go_to_login()
