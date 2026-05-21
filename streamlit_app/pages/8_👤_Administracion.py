"""Página: Administración (solo admin)."""
import streamlit as st
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_client import api_get, api_post, api_patch, is_authenticated, get_current_user
from ui import render_user_sidebar

st.set_page_config(page_title="Administración", page_icon="👤", layout="wide", initial_sidebar_state="expanded")
render_user_sidebar()

if not is_authenticated():
    st.warning("⚠️ Debe iniciar sesión primero.")
    st.stop()

user = get_current_user() or {}

if user.get("role") != "admin":
    st.error("🔒 Acceso restringido. Solo usuarios con rol `admin` pueden acceder.")
    st.stop()

st.title("👤 Administración del Sistema")
st.caption("Gestión de usuarios y empresas")

tab_users, tab_empresas, tab_nuevo = st.tabs(["👥 Usuarios", "🏢 Empresas", "➕ Crear"])

with tab_users:
    st.subheader("Usuarios registrados")
    usuarios = api_get("/users/")
    if usuarios:
        df = pd.DataFrame(usuarios)
        st.dataframe(
            df[["id", "email", "full_name", "role", "is_active", "empresa_id", "created_at"]],
            use_container_width=True,
            hide_index=True,
        )

        st.divider()
        st.markdown("**Activar / Desactivar usuario**")
        col_a, col_b, col_c = st.columns([2, 1, 1])
        with col_a:
            user_id = st.selectbox(
                "Usuario",
                options=[u["id"] for u in usuarios],
                format_func=lambda i: next(
                    f"{u['email']} ({'✅' if u['is_active'] else '❌'})"
                    for u in usuarios if u["id"] == i
                ),
            )
        with col_b:
            if st.button("✅ Activar"):
                if api_patch(f"/users/{user_id}/activate"):
                    st.success("Usuario activado")
                    st.rerun()
        with col_c:
            if st.button("❌ Desactivar"):
                if api_patch(f"/users/{user_id}/deactivate"):
                    st.success("Usuario desactivado")
                    st.rerun()

with tab_empresas:
    st.subheader("Empresas registradas")
    empresas = api_get("/empresas/")
    if empresas:
        df = pd.DataFrame(empresas)
        st.dataframe(df, use_container_width=True, hide_index=True)

with tab_nuevo:
    st.subheader("➕ Crear nueva entidad")
    sub_t1, sub_t2 = st.tabs(["🏢 Nueva empresa", "👤 Nuevo usuario"])

    with sub_t1:
        with st.form("form_empresa"):
            col_a, col_b = st.columns(2)
            with col_a:
                nombre = st.text_input("Nombre*")
                tipo = st.selectbox("Tipo", ["hotel", "hielera", "retail", "pyme", "comunidad", "otro"])
                direccion = st.text_input("Dirección")
                tarifa = st.number_input("Tarifa (COP/kWh)", min_value=0.0, value=943.0, step=10.0)
            with col_b:
                ciudad = st.text_input("Ciudad", value="Riohacha")
                departamento = st.text_input("Departamento", value="La Guajira")
                paneles = st.number_input("Capacidad paneles (kW)", min_value=0.0, value=0.0, step=0.5)
                bateria = st.number_input("Capacidad batería (kWh)", min_value=0.0, value=0.0, step=0.5)

            if st.form_submit_button("💾 Crear empresa", type="primary"):
                if nombre:
                    payload = {
                        "nombre": nombre,
                        "tipo": tipo,
                        "direccion": direccion,
                        "ciudad": ciudad,
                        "departamento": departamento,
                        "tarifa_kwh": tarifa,
                        "capacidad_paneles_kw": paneles,
                        "capacidad_bateria_kwh": bateria,
                    }
                    res = api_post("/empresas/", json=payload)
                    if res:
                        st.success(f"✅ Empresa creada: ID {res['id']}")
                        st.rerun()
                else:
                    st.warning("El nombre es requerido")

    with sub_t2:
        empresas_disp = api_get("/empresas/") or []
        with st.form("form_user"):
            col_a, col_b = st.columns(2)
            with col_a:
                email = st.text_input("Email*")
                password = st.text_input("Contraseña*", type="password")
                full_name = st.text_input("Nombre completo*")
            with col_b:
                role = st.selectbox("Rol", ["admin", "empresa", "analista"])
                empresa_id = None
                if role == "empresa" and empresas_disp:
                    opciones = {f"{e['nombre']} (ID:{e['id']})": e["id"] for e in empresas_disp}
                    sel = st.selectbox("Empresa asociada", list(opciones.keys()))
                    empresa_id = opciones[sel]

            if st.form_submit_button("💾 Crear usuario", type="primary"):
                if email and password and full_name:
                    payload = {
                        "email": email,
                        "password": password,
                        "full_name": full_name,
                        "role": role,
                        "empresa_id": empresa_id,
                    }
                    res = api_post("/auth/register", json=payload)
                    if res:
                        st.success(f"✅ Usuario creado: ID {res['id']}")
                        st.rerun()
                else:
                    st.warning("Complete todos los campos requeridos")
