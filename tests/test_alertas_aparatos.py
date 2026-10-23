"""Pruebas para las alertas del municipio (clima y riesgo de red) y humanización."""
import asyncio
from datetime import datetime, timedelta

import pytest

from app.models import models as m
from app.services import alertas_fonseca, openmeteo
from app.services.agents.agente_alertas import agente_alertas
from app.services.alertas_fonseca import calcular_alertas_generales, obtener_alertas_generales
from app.services.alertas_translator import humanizar_alerta, humanizar_lote


def alertas(db, empresa):
    return {a.tipo: a for a in db.query(m.Alerta).filter(m.Alerta.empresa_id == empresa.id).all()}


def contar(db, empresa, tipo):
    return db.query(m.Alerta).filter(m.Alerta.empresa_id == empresa.id, m.Alerta.tipo == tipo).count()


@pytest.fixture(autouse=True)
def reset_cache_alertas():
    """Limpia la caché de alertas del municipio antes de cada prueba."""
    alertas_fonseca._cache = {"alertas": None, "revisado": 0.0}
    yield
    alertas_fonseca._cache = {"alertas": None, "revisado": 0.0}


def test_clima_normal_sin_alertas():
    dias = [{
        "fecha": "2026-10-23",
        "temp_max": 32.0,
        "sensacion_max": 34.0,
        "lluvia_mm": 0.0,
        "prob_lluvia": 5,
        "viento_max": 15.0,
        "rafagas_max": 25.0,
        "ghi": 5.5,
    }]
    aire = {"disponible": True, "datos": [{"pm10": 20.0}]}
    res = calcular_alertas_generales(dias, aire, ciudad="Fonseca")
    assert res == []


def test_alerta_viento_genera_riesgo_apagon(db, crear_empresa, monkeypatch):
    empresa = crear_empresa("Casa Viento")
    dias = [{
        "fecha": "2026-10-23",
        "temp_max": 30.0,
        "viento_max": 52.0,
        "rafagas_max": 65.0,
        "ghi": 5.0,
    }]

    async def mock_pronostico(days=5):
        return dias

    monkeypatch.setattr(openmeteo.openmeteo_service, "get_pronostico_alertas", mock_pronostico)
    monkeypatch.setattr(openmeteo.openmeteo_service, "get_calidad_aire", lambda: None)

    asyncio.run(agente_alertas.evaluar(db, empresa, refrescar=True))
    t = alertas(db, empresa)
    assert "riesgo_apagon" in t
    assert "viento" in t["riesgo_apagon"].mensaje.lower()
    assert t["riesgo_apagon"].severidad == "alta"


def test_alerta_calor_extremo():
    dias = [{
        "fecha": "2026-10-23",
        "temp_max": 39.0,
        "sensacion_max": 42.0,
        "lluvia_mm": 0.0,
        "viento_max": 10.0,
        "rafagas_max": 15.0,
        "ghi": 5.8,
    }]
    res = calcular_alertas_generales(dias, None, ciudad="Fonseca")
    tipos = {a["tipo"]: a for a in res}
    assert "calor_extremo" in tipos
    assert tipos["calor_extremo"]["severidad"] == "alta"
    assert "39 °C" in tipos["calor_extremo"]["mensaje"]


def test_alerta_lluvia_fuerte():
    dias = [{
        "fecha": "2026-10-23",
        "temp_max": 28.0,
        "lluvia_mm": 35.0,
        "prob_lluvia": 85,
        "viento_max": 12.0,
        "rafagas_max": 20.0,
        "ghi": 4.0,
    }]
    res = calcular_alertas_generales(dias, None, ciudad="Fonseca")
    tipos = {a["tipo"]: a for a in res}
    assert "lluvia_fuerte" in tipos
    assert tipos["lluvia_fuerte"]["severidad"] == "media"


def test_alerta_polvo_aire():
    dias = [{"fecha": "2026-10-23", "temp_max": 31.0, "viento_max": 15.0, "ghi": 5.0}]
    aire = {"disponible": True, "datos": [{"pm10": 120.0}]}
    res = calcular_alertas_generales(dias, aire, ciudad="Fonseca")
    tipos = {a["tipo"]: a for a in res}
    assert "polvo_aire" in tipos
    assert tipos["polvo_aire"]["severidad"] == "media"


def test_alerta_sin_pronostico():
    res = calcular_alertas_generales([], None, ciudad="Fonseca")
    assert len(res) == 1
    assert res[0]["tipo"] == "sin_pronostico"


def test_humanizar_alertas_lote():
    alertas_crudas = [
        {"id": 1, "tipo": "calor_extremo", "mensaje": "Mucho calor", "severidad": "alta"},
        {"id": 2, "tipo": "riesgo_apagon", "mensaje": "Viento fuerte", "severidad": "alta"},
        {"id": 3, "tipo": "lluvia_fuerte", "mensaje": "Tormenta", "severidad": "media"},
        {"id": 4, "tipo": "polvo_aire", "mensaje": "PM10 alto", "severidad": "media"},
        {"id": 5, "tipo": "baja_radiacion", "mensaje": "Poco sol", "severidad": "baja"},
    ]
    h = {x["tipo_original"]: x for x in humanizar_lote(alertas_crudas)}
    assert h["calor_extremo"]["titulo"] == "Calor extremo"
    assert h["calor_extremo"]["nivel"] == "rojo"
    assert h["riesgo_apagon"]["titulo"] == "Riesgo de cortes de luz"
    assert h["lluvia_fuerte"]["titulo"] == "Lluvias fuertes"
    assert h["polvo_aire"]["titulo"] == "Mucho polvo en el aire"
    assert h["baja_radiacion"]["titulo"] == "Día con poco sol"
    assert h["baja_radiacion"]["nivel"] == "verde"


def test_alertas_no_se_duplican_el_mismo_dia(db, crear_empresa, monkeypatch):
    empresa = crear_empresa("Empresa Test Duplicados")
    dias = [{"fecha": "2026-10-23", "temp_max": 30.0, "viento_max": 50.0, "ghi": 5.0}]

    async def mock_pronostico(days=5):
        return dias

    monkeypatch.setattr(openmeteo.openmeteo_service, "get_pronostico_alertas", mock_pronostico)
    monkeypatch.setattr(openmeteo.openmeteo_service, "get_calidad_aire", lambda: None)

    asyncio.run(agente_alertas.evaluar(db, empresa, refrescar=True))
    assert contar(db, empresa, "riesgo_apagon") == 1

    # Segunda evaluación el mismo día no debe duplicar
    asyncio.run(agente_alertas.evaluar(db, empresa, refrescar=True))
    assert contar(db, empresa, "riesgo_apagon") == 1
