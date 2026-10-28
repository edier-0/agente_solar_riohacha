"""Banco de varias baterías, balance solar diario con radiación real y alertas del sistema solar."""
import asyncio
from datetime import date, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.models import models as m
from app.services.alertas_solares import calcular_alertas_solares
from app.services.balance_solar import calcular_balance, parametros_sistema, simular_serie
from tests.conftest import CLAVE

B = "/api/v1"

INSTALACION = {
    "potencia_panel_w": 500.0, "cantidad_paneles": 12, "orientacion": "sur", "inclinacion_grados": 12,
    "tiene_bateria": True, "quimica_bateria": "Litio LiFePO4", "voltaje_banco_v": 48.0, "capacidad_ah": 100.0,
    "soc_pct": 100, "dod_pct": 80.0, "eficiencia_ciclo_pct": 95.0, "potencia_inversor_w": 5000.0,
    "rendimiento_pr_pct": 80.0, "consumo_diario_kwh": 10.0, "demanda_diurna_kwh": 4.0, "demanda_nocturna_kwh": 6.0,
}
BATERIA = {"quimica": "Litio LiFePO4", "voltaje_v": 48.0, "capacidad_ah": 100.0}


@pytest.fixture
def api(Sesion, db):
    from app.api.routes import alertas, auth, consumo, instalacion

    app = FastAPI()
    for r in (auth, instalacion, consumo, alertas):
        app.include_router(r.router, prefix=B)

    def _db():
        s = Sesion()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _db
    return TestClient(app)


@pytest.fixture
def entrar(api):
    def _entrar(email):
        r = api.post(B + "/auth/login", json={"email": email, "password": CLAVE})
        assert r.status_code == 200, r.text
        return {"Authorization": "Bearer " + r.json()["access_token"]}
    return _entrar


@pytest.fixture
def gasolinera(crear_empresa, crear_usuario):
    empresa = crear_empresa("Gasolinera", tipo="industria", tipo_entidad="empresa")
    crear_usuario("gas@t.co", empresa=empresa)
    otra = crear_empresa("Otra")
    crear_usuario("otra@t.co", empresa=otra)
    return empresa


@pytest.fixture(autouse=True)
def sin_serie_reciente(monkeypatch):
    from app.services import openmeteo

    async def vacio(*args, **kwargs):
        return []

    monkeypatch.setattr(openmeteo.openmeteo_service, "get_serie_reciente", vacio)


def radiacion(db, dias, ghi=6.0, fuente="open_meteo"):
    hoy = date.today()
    for i in range(dias):
        d = hoy - timedelta(days=i)
        db.add(m.RadiacionSolar(fecha=datetime.combine(d, datetime.min.time()), ghi=ghi, fuente=fuente,
                                escenario="real", origen_dato="real_api", confiabilidad=90))
    db.commit()


def test_put_instalacion_con_cuatro_baterias_suma_el_banco(api, entrar, gasolinera, Sesion):
    h = entrar("gas@t.co")
    datos = {**INSTALACION, "baterias": [BATERIA, BATERIA, BATERIA, BATERIA]}
    r = api.put(f"{B}/empresas/{gasolinera.id}/instalacion", json=datos, headers=h)
    assert r.status_code == 200, r.text
    inst = r.json()
    assert inst["numero_baterias"] == 4 and inst["bateria_kwh"] == pytest.approx(19.2)
    assert inst["potencia_pico_kw"] == pytest.approx(6.0)
    assert [b["orden"] for b in inst["baterias"]] == [1, 2, 3, 4]
    s = Sesion()
    try:
        empresa = s.get(m.Empresa, gasolinera.id)
        assert empresa.capacidad_bateria_kwh == pytest.approx(19.2)
        assert empresa.capacidad_paneles_kw == pytest.approx(6.0)
    finally:
        s.close()

    # Una sola fila con cantidad 4 da lo mismo; quitar las baterías deja el banco en cero
    r = api.put(f"{B}/empresas/{gasolinera.id}/instalacion", json={**INSTALACION, "baterias": [{**BATERIA, "cantidad": 4}]}, headers=h)
    assert r.json()["bateria_kwh"] == pytest.approx(19.2) and len(r.json()["baterias"]) == 1
    r = api.put(f"{B}/empresas/{gasolinera.id}/instalacion", json={**INSTALACION, "tiene_bateria": False}, headers=h)
    assert r.json()["bateria_kwh"] == 0 and r.json()["baterias"] == []


def test_instalacion_antigua_pasa_su_bateria_a_la_lista(api, entrar, gasolinera, db):
    db.add(m.InstalacionSolar(empresa_id=gasolinera.id, potencia_panel_w=500, cantidad_paneles=12, tiene_bateria=True,
                              quimica_bateria="Litio LiFePO4", voltaje_banco_v=48, capacidad_ah=100))
    db.commit()
    r = api.get(f"{B}/empresas/{gasolinera.id}/instalacion", headers=entrar("gas@t.co"))
    assert r.status_code == 200
    assert r.json()["numero_baterias"] == 1 and r.json()["baterias"][0]["energia_kwh"] == pytest.approx(4.8)


def test_solo_la_propia_empresa_ve_y_cambia_su_instalacion(api, entrar, gasolinera):
    h = entrar("otra@t.co")
    assert api.get(f"{B}/empresas/{gasolinera.id}/instalacion", headers=h).status_code == 403
    assert api.put(f"{B}/empresas/{gasolinera.id}/instalacion", json=INSTALACION, headers=h).status_code == 403
    assert api.get(f"{B}/empresas/{gasolinera.id}/balance-solar", headers=h).status_code == 403


def test_registro_con_baterias_iguales(api, crear_usuario, entrar, Sesion):
    crear_usuario("admin@t.co", rol=m.UserRole.ADMIN)
    datos = {"email": "nuevo@t.co", "password": CLAVE, "full_name": "Ana", "escenario_usuario": "real",
             "nombre_empresa": "Finca Ana", "tipo_entidad": "finca",
             "instalacion": {**INSTALACION, "baterias": [{**BATERIA, "cantidad": 4}]}}
    r = api.post(B + "/auth/register", json=datos, headers=entrar("admin@t.co"))
    assert r.status_code == 201, r.text
    s = Sesion()
    try:
        empresa = s.query(m.Empresa).filter_by(nombre="Finca Ana").one()
        assert empresa.capacidad_bateria_kwh == pytest.approx(19.2)
    finally:
        s.close()


def test_simulacion_separa_excedente_bateria_y_red():
    p = {"bateria_kwh": 10.0, "bateria_util_kwh": 7.0, "eficiencia_bateria": 1.0, "fraccion_diurna": 0.5,
         "soc_inicial_pct": 30}
    # Mucho sol: el día se cubre, la batería se llena (de 3 a 10 kWh) y sobra el resto
    dia = simular_serie([20.0], 10.0, p, tarifa=1000)[0]
    assert dia["autoconsumo_kwh"] == 5 and dia["carga_bateria_kwh"] == 7 and dia["excedente_kwh"] == 8
    assert dia["red_kwh"] == 0 and dia["bateria_anochecer_pct"] == 100 and dia["bateria_amanecer_pct"] == 50
    assert dia["ahorro_cop"] == 10000
    # Sin sol: la batería baja hasta la reserva (30 %) y lo demás sale de la red
    sin_sol = simular_serie([0.0], 10.0, {**p, "soc_inicial_pct": 100}, tarifa=1000)[0]
    assert sin_sol["descarga_bateria_kwh"] == 7 and sin_sol["red_kwh"] == 3 and sin_sol["bateria_amanecer_pct"] == 30
    # Día sin radiación: no se inventa la producción
    assert simular_serie([None], 10.0, p, tarifa=1000)[0]["produccion_kwh"] is None


def test_balance_usa_radiacion_real_y_paneles_registrados(db, gasolinera, agregar_aparatos):
    db.add(m.InstalacionSolar(empresa_id=gasolinera.id, **{k: v for k, v in INSTALACION.items()}))
    db.commit()
    radiacion(db, 10, ghi=6.0)
    bal = asyncio.run(calcular_balance(db, gasolinera, days=14, pronostico=0, usar_api=False))
    assert bal["disponible"]
    dias = {d["fecha"]: d for d in bal["dias"]}
    hoy = dias[date.today().isoformat()]
    assert hoy["produccion_kwh"] == pytest.approx(6.0 * 6.0 * 0.8)  # kWp × GHI × PR
    assert hoy["consumo_kwh"] == 10.0 and bal["demanda"]["fuente"] == "perfil"
    sin_dato = dias[(date.today() - timedelta(days=12)).isoformat()]
    assert sin_dato["produccion_kwh"] is None  # sin radiación guardada no hay producción
    assert bal["resumen"]["dias_con_datos"] == 10
    assert bal["fuentes_radiacion"] == ["Open-Meteo"]


def test_con_factura_se_elige_el_consumo_que_mejor_la_explica(db, gasolinera, agregar_aparatos):
    db.add(m.InstalacionSolar(empresa_id=gasolinera.id, **INSTALACION))
    agregar_aparatos(gasolinera, ("aire_12000", 4))  # mucho más consumo del que muestra la factura
    radiacion(db, 20, ghi=6.0)
    hoy = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
    for i in range(20):
        db.add(m.ConsumoEnergetico(empresa_id=gasolinera.id, fecha=hoy - timedelta(days=i), consumo_kwh=0.5,
                                   escenario="real", origen_dato="real_monthly_bill", periodo="diario"))
    db.commit()
    bal = asyncio.run(calcular_balance(db, gasolinera, days=20, pronostico=0, usar_api=False))
    assert bal["demanda"]["fuente"] == "perfil" and bal["demanda"]["elegida_por"] == "factura"
    assert any("Revisa las horas de uso" in n for n in bal["notas"])


def test_sin_paneles_no_hay_balance(db, gasolinera):
    bal = asyncio.run(calcular_balance(db, gasolinera, usar_api=False))
    assert bal == {"disponible": False, "motivo": "Esta cuenta no tiene paneles solares registrados."}


def test_alertas_de_excedente_bateria_y_produccion_baja():
    sistema = {"bateria_kwh": 4.8, "reserva_pct": 30}
    hoy = {"produccion_kwh": 26.0, "excedente_kwh": 12.0, "red_noche_kwh": 2.5, "consumo_noche_kwh": 5.7,
           "descarga_bateria_kwh": 3.2}
    manana = {"produccion_kwh": 10.0, "excedente_kwh": 0.0}
    balance = {"disponible": True, "sistema": sistema,
               "resumen": {"hoy": hoy, "manana": manana, "produccion_promedio_kwh_dia": 26.0}}
    tipos = {a["tipo"]: a for a in calcular_alertas_solares(balance)}
    assert set(tipos) == {"excedente_solar", "bateria_insuficiente", "produccion_baja"}
    assert "12.0 kWh" in tipos["excedente_solar"]["mensaje"]
    assert "2.5 kWh saldrán de la red" in tipos["bateria_insuficiente"]["mensaje"]
    assert "62 % menos" in tipos["produccion_baja"]["mensaje"]
    assert calcular_alertas_solares({"disponible": False}) == []


def test_alertas_solares_se_guardan_para_la_empresa(api, entrar, gasolinera, db):
    db.add(m.InstalacionSolar(empresa_id=gasolinera.id, **{**INSTALACION, "consumo_diario_kwh": 4.0}))
    gasolinera.capacidad_paneles_kw = 6.0
    db.commit()
    radiacion(db, 14, ghi=6.0)
    r = api.get(f"{B}/alertas/{gasolinera.id}", headers=entrar("gas@t.co"))
    assert r.status_code == 200, r.text
    assert "excedente_solar" in {a["tipo"] for a in r.json()}


def test_kpis_estiman_la_produccion_de_hoy_con_los_paneles(api, entrar, gasolinera, db):
    db.add(m.InstalacionSolar(empresa_id=gasolinera.id, **INSTALACION))
    gasolinera.capacidad_paneles_kw = 6.0
    db.commit()
    radiacion(db, 3, ghi=5.0)
    k = api.get(f"{B}/consumo/kpis/{gasolinera.id}", headers=entrar("gas@t.co")).json()
    assert k["produccion_solar_hoy_kwh"] == pytest.approx(6.0 * 5.0 * 0.8)
    assert k["ahorro_estimado_cop"] > 0


def test_parametros_dejan_la_reserva_para_cortes_de_luz():
    class Inst:
        bateria_kwh = 19.2
        potencia_pico_kw = 6.0
        numero_baterias = 4
        dod_pct = 90
        rendimiento_pr_pct = None
        eficiencia_ciclo_pct = None
        demanda_diurna_kwh = None
        demanda_nocturna_kwh = None
        soc_pct = None

    p = parametros_sistema(Inst())
    assert p["bateria_util_kwh"] == pytest.approx(19.2 * 0.7) and p["reserva_pct"] == 30 and p["pr"] == 0.8
