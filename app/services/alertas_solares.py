"""
Alertas del sistema solar de cada usuario con paneles registrados.

Salen del balance solar (app/services/balance_solar.py), que usa la radiación real y el pronóstico de
Open-Meteo: excedente de energía para aprovechar, baterías que no alcanzan para la noche y días con
menos producción de lo normal.
"""
from typing import Dict, List, Optional

TIPOS_SOLARES = ("excedente_solar", "bateria_insuficiente", "produccion_baja")

EXCEDENTE_MINIMO_KWH = 1.0       # menos que esto no vale la pena avisar
RED_NOCHE_MINIMA_KWH = 0.5
PRODUCCION_BAJA_FRACCION = 0.7   # mañana por debajo del 70 % del promedio de los últimos días

CRITERIOS_SOLARES = [
    {"alerta": "Excedente solar", "cuando": f"Sobran {EXCEDENTE_MINIMO_KWH:.0f} kWh o más después de cubrir el consumo y llenar las baterías."},
    {"alerta": "Baterías insuficientes", "cuando": f"Esta noche se tomarán {RED_NOCHE_MINIMA_KWH} kWh o más de la red porque las baterías llegaron a su reserva."},
    {"alerta": "Producción solar baja", "cuando": f"Mañana los paneles producirán menos del {PRODUCCION_BAJA_FRACCION * 100:.0f} % de su promedio de los últimos 14 días."},
]


def _alerta_excedente(hoy: Optional[Dict], manana: Optional[Dict]) -> Optional[Dict]:
    for cuando, dia in (("Mañana", manana), ("Hoy", hoy)):
        if dia and (dia.get("excedente_kwh") or 0) >= EXCEDENTE_MINIMO_KWH:
            return {
                "tipo": "excedente_solar",
                "severidad": "baja",
                "mensaje": (
                    f"{cuando} tus paneles producirán ≈{dia['produccion_kwh']:.1f} kWh y, con las baterías llenas, "
                    f"sobrarán ≈{dia['excedente_kwh']:.1f} kWh. Usa en las horas de sol (10 a. m. a 2 p. m.) "
                    "los equipos de más consumo para aprovechar esa energía."
                ),
            }
    return None


def _alerta_bateria(hoy: Optional[Dict], sistema: Dict) -> Optional[Dict]:
    if not hoy or not sistema.get("bateria_kwh"):
        return None
    red_noche = hoy.get("red_noche_kwh") or 0
    if red_noche < RED_NOCHE_MINIMA_KWH:
        return None
    return {
        "tipo": "bateria_insuficiente",
        "severidad": "media",
        "mensaje": (
            f"Esta noche consumirás ≈{hoy['consumo_noche_kwh']:.1f} kWh y tus baterías "
            f"({sistema['bateria_kwh']:.1f} kWh) cubrirán ≈{hoy['descarga_bateria_kwh']:.1f} kWh sin bajar de la "
            f"reserva del {sistema.get('reserva_pct') or 30} %. Unos {red_noche:.1f} kWh saldrán de la red de Air-e."
        ),
    }


def _alerta_produccion_baja(manana: Optional[Dict], promedio: Optional[float]) -> Optional[Dict]:
    if not manana or manana.get("produccion_kwh") is None or not promedio:
        return None
    produccion = manana["produccion_kwh"]
    if produccion >= promedio * PRODUCCION_BAJA_FRACCION:
        return None
    menos = (1 - produccion / promedio) * 100
    return {
        "tipo": "produccion_baja",
        "severidad": "media",
        "mensaje": (
            f"Mañana la producción solar bajará a ≈{produccion:.1f} kWh, un {menos:.0f} % menos que tu promedio de "
            f"{promedio:.1f} kWh, por las nubes o la lluvia del pronóstico. Deja las baterías cargadas hoy y "
            "aplaza los consumos grandes."
        ),
    }


def calcular_alertas_solares(balance: Dict) -> List[Dict]:
    if not balance or not balance.get("disponible"):
        return []
    resumen = balance.get("resumen") or {}
    sistema = balance.get("sistema") or {}
    hoy, manana = resumen.get("hoy"), resumen.get("manana")
    alertas = [
        _alerta_excedente(hoy, manana),
        _alerta_bateria(hoy, sistema),
        _alerta_produccion_baja(manana, resumen.get("produccion_promedio_kwh_dia")),
    ]
    return [a for a in alertas if a]
