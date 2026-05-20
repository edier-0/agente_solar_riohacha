import streamlit as st

st.set_page_config(page_title="Solar AI", page_icon="☀️", layout="wide")

if "perfil_empresa" not in st.session_state:
    st.session_state["perfil_empresa"] = {
        "nombre": "Hielera Caribe",
        "tipo": "Hielera",
        "consumo_mensual": 4500.0,
        "bateria": 15.0
    }

st.title("☀️ Solar AI Dashboard")
st.write("Bienvenido al sistema inteligente de autogestión solar para Riohacha.")