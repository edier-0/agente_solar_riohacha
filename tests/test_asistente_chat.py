"""
Pruebas del Asistente Copiloto Ka'i.
Verifica:
- Seguridad y autenticación (401 o 403 sin token).
- Aislamiento de contexto por usuario (sin mezclar hogares/negocios).
- Consultas de navegación por la app.
- Consultas de términos solares (DoD, kW vs kWh, etc.).
- Tolerancia a fallos: respuesta heurística local ante caída o ausencia de Gemini.
"""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps.auth import get_current_user
from app.api.routes import auth, ia
from app.db.session import get_db
from app.models import models as m
from app.services.asistente_copiloto import (
    construir_contexto_usuario,
    generar_respuesta_heuristica,
    responder_chat_asistente,
)
from app.schemas.schemas import ChatAsistenteRequest


@pytest.fixture
def cliente_ia(Sesion):
    """Cliente de prueba que incluye los routers de auth e ia."""
    app = FastAPI()
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(ia.router, prefix="/api/v1")

    def _db():
        s = Sesion()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _db
    return TestClient(app)


def test_asistente_requiere_autenticacion(cliente_ia):
    """Llamar a /api/v1/ia/asistente/chat sin token debe devolver 401 o 403."""
    resp = cliente_ia.post("/api/v1/ia/asistente/chat", json={"mensaje": "Hola Ka'i"})
    assert resp.status_code in (401, 403)


def test_asistente_responde_usuario_autenticado_heuristico(db, crear_empresa, crear_usuario, token, cliente_ia):
    """Usuario autenticado recibe respuesta sin necesidad de clave de Gemini (motor heurístico)."""
    empresa = crear_empresa(nombre="Casa Familia Díaz", tipo="hogar", tipo_entidad="hogar")
    crear_usuario("diaz@ejemplo.com", m.UserRole.EMPRESA, empresa)
    auth_header = token("diaz@ejemplo.com")

    resp = cliente_ia.post(
        "/api/v1/ia/asistente/chat",
        headers=auth_header,
        json={"mensaje": "¿Dónde registro mis paneles solares y baterías?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "respuesta" in data
    assert "Administración" in data["respuesta"] or "paneles" in data["respuesta"].lower()
    assert len(data.get("sugerencias", [])) > 0
    assert data["origen"] in ("heuristico", "gemini")


def test_aislamiento_multitenant_contexto(db, crear_empresa, crear_usuario, agregar_aparatos):
    """El contexto construido para un usuario debe contener SOLO sus datos y nunca los de otro."""
    # Usuario A: Hogar con 2 aparatos y sin paneles
    empresa_a = crear_empresa(nombre="Hogar Los Laureles", tipo="hogar", tipo_entidad="hogar")
    agregar_aparatos(empresa_a, ("nevera", 1), ("bombillo_led", 4))
    crear_usuario("a@test.com", m.UserRole.EMPRESA, empresa_a)
    user_a = db.query(m.User).filter(m.User.email == "a@test.com").first()

    # Usuario B: Negocio con 15 kWp de paneles y 24 kWh de baterías
    empresa_b = crear_empresa(
        nombre="Ferretería Central",
        tipo="comercio",
        tipo_entidad="comercial",
        capacidad_paneles_kw=15.0,
        capacidad_bateria_kwh=24.0,
    )
    crear_usuario("b@test.com", m.UserRole.EMPRESA, empresa_b)
    user_b = db.query(m.User).filter(m.User.email == "b@test.com").first()

    ctx_a = construir_contexto_usuario(db, user_a)
    ctx_b = construir_contexto_usuario(db, user_b)

    # A tiene aparatos pero no paneles
    assert ctx_a["entidad"]["nombre"] == "Hogar Los Laureles"
    assert ctx_a["solar"]["tiene_paneles"] is False
    assert ctx_a["aparatos"]["total_registrados"] == 2

    # B tiene paneles y baterías pero no los aparatos de A
    assert ctx_b["entidad"]["nombre"] == "Ferretería Central"
    assert ctx_b["solar"]["tiene_paneles"] is True
    assert ctx_b["solar"]["capacidad_paneles_kw"] == 15.0
    assert ctx_b["solar"]["capacidad_bateria_kwh"] == 24.0
    assert ctx_b["aparatos"]["total_registrados"] == 0


def test_respuesta_heuristica_terminos_solares():
    """El motor heurístico responde preguntas comunes sobre términos energéticos."""
    ctx = {
        "usuario": {"nombre": "Ana"},
        "entidad": {"nombre": "Casa", "tipo": "hogar"},
        "solar": {"tiene_paneles": False, "capacidad_paneles_kw": 0.0},
        "aparatos": {"total_registrados": 0},
    }

    # Pregunta por DoD
    resp_dod, sug_dod = generar_respuesta_heuristica("¿Qué es DoD y cómo se usa?", ctx)
    assert "Depth of Discharge" in resp_dod or "profundidad de descarga" in resp_dod.lower()
    assert "30" in resp_dod or "40" in resp_dod

    # Pregunta por diferencia kW vs kWh
    resp_kw, _ = generar_respuesta_heuristica("¿Cuál es la diferencia entre kW y kWh?", ctx)
    assert "kW" in resp_kw and "kWh" in resp_kw
    assert "potencia" in resp_kw.lower() or "instantáneo" in resp_kw.lower()

    # Pregunta por Air-E
    resp_aire, _ = generar_respuesta_heuristica("¿Por qué la tarifa de Air-E es tan alta?", ctx)
    assert "Air-E" in resp_aire or "943" in resp_aire


def test_respuesta_con_gemini_mockeado(db, crear_empresa, crear_usuario):
    """Cuando Gemini está disponible y responde, el copiloto retorna origen='gemini'."""
    empresa = crear_empresa(nombre="Hotel Guajira", tipo="comercial")
    crear_usuario("hotel@guajira.com", m.UserRole.EMPRESA, empresa)
    user = db.query(m.User).filter(m.User.email == "hotel@guajira.com").first()

    req = ChatAsistenteRequest(
        mensaje="¿Dónde puedo descargar un reporte en PDF de mi consumo?",
        historial=[],
    )

    respuesta_simulada = (
        "Puedes descargar informes ejecutivos en formato PDF y Excel dirigiéndote a la sección "
        "**'Reportes'** en el menú lateral."
    )

    import asyncio

    with patch("app.services.asistente_copiloto.obtener_respuesta_gemini", new=AsyncMock(return_value=respuesta_simulada)):
        resultado = asyncio.run(responder_chat_asistente(db, user, req))
        assert resultado.origen == "gemini"
        assert "Reportes" in resultado.respuesta
        assert len(resultado.sugerencias) > 0


def test_respuesta_fallback_cuando_gemini_falla(db, crear_empresa, crear_usuario):
    """Si Gemini falla por timeout o error de red, el copiloto cae al motor heurístico sin explotar."""
    empresa = crear_empresa(nombre="Casa Fonseca", tipo="hogar")
    crear_usuario("fonseca@ejemplo.com", m.UserRole.EMPRESA, empresa)
    user = db.query(m.User).filter(m.User.email == "fonseca@ejemplo.com").first()

    req = ChatAsistenteRequest(
        mensaje="¿Dónde veo cuánto consumen mis aparatos?",
        historial=[],
    )

    import asyncio

    with patch("app.services.asistente_copiloto.obtener_respuesta_gemini", new=AsyncMock(side_effect=Exception("Timeout Gemini"))):
        resultado = asyncio.run(responder_chat_asistente(db, user, req))
        assert resultado.origen == "heuristico"
        assert "Mis Aparatos" in resultado.respuesta


def test_limpieza_rutas_archivos_en_navegacion():
    """El copiloto jamás debe devolver rutas de archivos como 'pages/8_Administracion.py'."""
    from app.services.asistente_copiloto import limpiar_rutas_archivos

    casos = [
        "Debes ir a pages/8_Administracion.py para registrar paneles",
        "Ve a pages/8_Administración.py en la seccion",
        "Abre pages\\8_administracion.py ahora",
        "En 8_Administracion.py encontraras paneles",
        "Consulta pages/0_Mis_Aparatos.py",
        "En Home.py veras el resumen",
        "En el archivo `pages/8_Administracion.py` puedes verlo",
    ]
    for texto in casos:
        limpio = limpiar_rutas_archivos(texto)
        assert ".py" not in limpio
        assert "pages/" not in limpio
        assert "pages\\" not in limpio
        if "administra" in texto.lower():
            assert "Administración" in limpio


def test_widget_flotante_renderiza():
    """Verifica que el widget flotante renderice correctamente el botón con AppTest."""
    import sys
    from pathlib import Path
    from streamlit.testing.v1 import AppTest

    ruta_streamlit = str(Path(__file__).parent.parent / "streamlit_app")
    if ruta_streamlit not in sys.path:
        sys.path.insert(0, ruta_streamlit)

    code = f"""
import sys
sys.path.insert(0, r'{ruta_streamlit}')
import streamlit as st
from asistente_widget import render_asistente_flotante

user = {{'id': 1, 'full_name': 'Edier Solar', 'empresa_nombre': 'Mi Casa', 'role': 'empresa'}}
render_asistente_flotante(user)
"""
    at = AppTest.from_string(code)
    at.run()
    assert not at.exception
    # Verifica que el botón de Ka'i está presente
    assert len(at.button) >= 1


def test_contexto_usuario_filtra_apartados_por_rol_empresa(db, crear_empresa, crear_usuario):
    """Un usuario con rol 'empresa' no debe tener 'Datos solares' ni 'Administración' en sus apartados permitidos."""
    empresa = crear_empresa(nombre="Hogar Los Pinos", tipo="hogar")
    crear_usuario("hogar@pinos.com", m.UserRole.EMPRESA, empresa)
    user = db.query(m.User).filter(m.User.email == "hogar@pinos.com").first()

    ctx = construir_contexto_usuario(db, user)

    assert "Datos solares" in ctx["nombres_restringidos"]
    assert "Administración" in ctx["nombres_restringidos"]
    assert "Datos solares" not in ctx["nombres_permitidos"]
    assert "Administración" not in ctx["nombres_permitidos"]

    # Debe tener Mi día y Mis Aparatos
    assert "Mi día" in ctx["nombres_permitidos"]
    assert "Mis Aparatos" in ctx["nombres_permitidos"]
    assert "Consumo" in ctx["nombres_permitidos"]


def test_contexto_usuario_filtra_apartados_por_rol_analista(db, crear_empresa, crear_usuario):
    """Un usuario con rol 'analista' debe ver 'Datos solares', pero no 'Mi día' ni 'Administración'."""
    empresa = crear_empresa(nombre="Gobernación Guajira", tipo="institucion")
    crear_usuario("analista@guajira.gov.co", m.UserRole.ANALISTA, empresa)
    user = db.query(m.User).filter(m.User.email == "analista@guajira.gov.co").first()

    ctx = construir_contexto_usuario(db, user)

    assert "Datos solares" in ctx["nombres_permitidos"]
    assert "Reportes" in ctx["nombres_permitidos"]
    assert "Mi día" in ctx["nombres_restringidos"]
    assert "Administración" in ctx["nombres_restringidos"]


def test_contexto_usuario_filtra_apartados_por_rol_admin(db, crear_empresa, crear_usuario):
    """Un usuario 'admin' tiene acceso a todos los apartados (ninguno restringido)."""
    empresa = crear_empresa(nombre="Central Solar Guajira", tipo="empresa")
    crear_usuario("superadmin@guajira.com", m.UserRole.ADMIN, empresa)
    user = db.query(m.User).filter(m.User.email == "superadmin@guajira.com").first()

    ctx = construir_contexto_usuario(db, user)

    assert "Datos solares" in ctx["nombres_permitidos"]
    assert "Administración" in ctx["nombres_permitidos"]
    assert "Mi día" in ctx["nombres_permitidos"]
    assert len(ctx["nombres_restringidos"]) == 0


def test_respuesta_heuristica_control_acceso_datos_solares():
    """El motor heurístico adapta la respuesta de datos solares según el rol."""
    ctx_empresa = {
        "usuario": {"nombre": "Carlos", "rol": "empresa"},
        "entidad": {"nombre": "Hogar Carlos", "tipo": "hogar", "ciudad": "Fonseca"},
        "solar": {"tiene_paneles": False, "capacidad_paneles_kw": 0.0},
        "aparatos": {"total_registrados": 0},
        "navegacion": [{"nombre": "Mi día", "proposito": "Resumen"}],
    }

    resp_emp, _ = generar_respuesta_heuristica("¿Dónde puedo ver los datos solares y la radiación?", ctx_empresa)
    assert "Analista" in resp_emp or "Administrador" in resp_emp
    assert "Mi día" in resp_emp or "Alertas" in resp_emp

    ctx_analista = {
        "usuario": {"nombre": "Ing. Laura", "rol": "analista"},
        "entidad": {"nombre": "Gobernación", "tipo": "institucion", "ciudad": "Riohacha"},
        "solar": {"tiene_paneles": True, "capacidad_paneles_kw": 10.0},
        "aparatos": {"total_registrados": 0},
        "navegacion": [{"nombre": "Datos solares", "proposito": "Radiación"}],
    }

    resp_ana, _ = generar_respuesta_heuristica("¿Dónde veo los datos solares de radiación?", ctx_analista)
    assert "Datos solares" in resp_ana
    assert "NASA POWER" in resp_ana or "Open-Meteo" in resp_ana


def test_respuesta_heuristica_control_acceso_paneles():
    """El motor heurístico indica a los usuarios 'empresa' que Administración es exclusiva del Admin."""
    ctx_empresa = {
        "usuario": {"nombre": "María", "rol": "empresa"},
        "entidad": {"nombre": "Casa María", "tipo": "hogar"},
        "solar": {"tiene_paneles": False, "capacidad_paneles_kw": 0.0},
        "aparatos": {"total_registrados": 0},
    }

    resp, _ = generar_respuesta_heuristica("¿Dónde registro mis paneles solares?", ctx_empresa)
    assert "Administrador" in resp
    assert "solicita" in resp.lower() or "administrador de la plataforma" in resp.lower()



