"""
Cliente HTTP para consumir la API FastAPI desde Streamlit.
"""

import os
from typing import Any, Dict, Optional

import requests
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_PREFIX = "/api/v1"


def _get_headers() -> Dict[str, str]:
    token = st.session_state.get("token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def _clear_session() -> None:
    for key in ("token", "user"):
        if key in st.session_state:
            del st.session_state[key]


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
            me = api_get("/auth/me")
            if me:
                st.session_state["user"] = me
            return data["access_token"]

        try:
            detail = resp.json().get("detail", "Error desconocido")
        except Exception:
            detail = resp.text
        st.error(f"Login fallido: {detail}")
        return None
    except requests.RequestException as exc:
        st.error(f"Error de conexion con API: {exc}")
        return None


def logout(call_api: bool = True) -> bool:
    """
    Cierra sesion en el cliente y, si hay token, notifica a la API.

    La API actual valida el token en /auth/logout pero no revoca JWT emitidos
    previamente porque el esquema es stateless.
    """
    success = True
    token = st.session_state.get("token")

    if call_api and token:
        try:
            resp = requests.post(_url("/auth/logout"), headers=_get_headers(), timeout=10)
            success = resp.status_code in (200, 401)
        except requests.RequestException:
            success = False

    _clear_session()
    return success


def is_authenticated() -> bool:
    return "token" in st.session_state and st.session_state.get("token")


def get_current_user() -> Optional[Dict]:
    return st.session_state.get("user")


def api_get(path: str, params: Optional[Dict] = None) -> Optional[Any]:
    try:
        resp = requests.get(_url(path), headers=_get_headers(), params=params, timeout=30)
        if resp.status_code == 401:
            _clear_session()
            st.warning("Sesion expirada. Inicie sesion nuevamente.")
            return None
        if resp.status_code >= 400:
            return None
        return resp.json()
    except requests.RequestException as exc:
        st.error(f"Error API: {exc}")
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
            _clear_session()
            st.warning("Sesion expirada.")
            return None
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            st.error(f"Error {resp.status_code}: {detail}")
            return None
        return resp.json()
    except requests.RequestException as exc:
        st.error(f"Error API: {exc}")
        return None


def api_patch(path: str, json: Optional[Dict] = None) -> Optional[Any]:
    try:
        resp = requests.patch(_url(path), headers=_get_headers(), json=json, timeout=30)
        if resp.status_code == 401:
            _clear_session()
            st.warning("Sesion expirada.")
            return None
        if resp.status_code >= 400:
            return None
        return resp.json()
    except requests.RequestException as exc:
        st.error(f"Error API: {exc}")
        return None


def api_download(path: str, params: Optional[Dict] = None) -> Optional[bytes]:
    """Descarga binaria (PDF/Excel)."""
    try:
        resp = requests.get(_url(path), headers=_get_headers(), params=params, timeout=60)
        if resp.status_code == 401:
            _clear_session()
            st.warning("Sesion expirada.")
            return None
        if resp.status_code >= 400:
            return None
        return resp.content
    except requests.RequestException as exc:
        st.error(f"Error descarga: {exc}")
        return None
