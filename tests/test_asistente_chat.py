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
