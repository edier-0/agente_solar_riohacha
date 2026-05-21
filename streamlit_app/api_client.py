"""
Cliente HTTP para consumir la API FastAPI desde Streamlit.
"""
import os
import requests
import streamlit as st
from typing import Optional, Any, Dict


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_PREFIX = "/api/v1"


def _get_headers() -> Dict[str, str]:
    token = st.session_state.get("token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def _url(path: str) -> str:
    if path.startswith("http"):
        return path
    return f"{API_BASE_URL}{API_PREFIX}{path}"


def login(email: str, password: str) -> Optional[str]:
    """Realiza login y retorna token. Guarda en session_state."""
    try:
        resp = requests.post(
            f"{API_BASE_URL}{API_PREFIX}/auth/login",
            json={"email": email, "password": password},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            st.session_state["token"] = data["access_token"]
            # Obtener info usuario
            me = api_get("/auth/me")
            if me:
                st.session_state["user"] = me
            return data["access_token"]
        else:
            try:
                detail = resp.json().get("detail", "Error desconocido")
            except Exception:
                detail = resp.text
            st.error(f"Login fallido: {detail}")
            return None
    except requests.RequestException as e:
        st.error(f"Error de conexión con API: {e}")
        return None


def logout():
    """Borra credenciales del session_state."""
    for k in ("token", "user"):
        if k in st.session_state:
            del st.session_state[k]


def is_authenticated() -> bool:
    return "token" in st.session_state and st.session_state.get("token")


def get_current_user() -> Optional[Dict]:
    return st.session_state.get("user")


def api_get(path: str, params: Optional[Dict] = None) -> Optional[Any]:
    try:
        resp = requests.get(_url(path), headers=_get_headers(), params=params, timeout=30)
        if resp.status_code == 401:
            logout()
            st.warning("Sesión expirada. Inicie sesión nuevamente.")
            return None
        if resp.status_code >= 400:
            return None
        return resp.json()
    except requests.RequestException as e:
        st.error(f"Error API: {e}")
        return None


def api_post(path: str, json: Optional[Dict] = None, files: Any = None, params: Optional[Dict] = None) -> Optional[Any]:
    try:
        resp = requests.post(
            _url(path),
            headers=_get_headers(),
            json=json if files is None else None,
            files=files,
            params=params,
            timeout=120,
        )
        if resp.status_code == 401:
            logout()
            st.warning("Sesión expirada.")
            return None
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            st.error(f"Error {resp.status_code}: {detail}")
            return None
        return resp.json()
    except requests.RequestException as e:
        st.error(f"Error API: {e}")
        return None


def api_patch(path: str, json: Optional[Dict] = None) -> Optional[Any]:
    try:
        resp = requests.patch(_url(path), headers=_get_headers(), json=json, timeout=30)
        if resp.status_code >= 400:
            return None
        return resp.json()
    except requests.RequestException as e:
        st.error(f"Error API: {e}")
        return None


def api_download(path: str, params: Optional[Dict] = None) -> Optional[bytes]:
    """Descarga binaria (PDF/Excel)."""
    try:
        resp = requests.get(_url(path), headers=_get_headers(), params=params, timeout=60)
        if resp.status_code >= 400:
            return None
        return resp.content
    except requests.RequestException as e:
        st.error(f"Error descarga: {e}")
        return None
