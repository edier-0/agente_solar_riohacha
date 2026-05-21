"""
Capa de traducción: convierte métricas crudas en mensajes accionables.

Pensado para usuarios no técnicos (vista 'simple'). Cada función devuelve un dict
con: emoji, nivel (verde/amarillo/rojo), titulo y mensaje en lenguaje natural.
"""
from typing import Dict, Optional


# ---------------------------------------------------------------------------
# Niveles estándar (semáforo)
# ---------------------------------------------------------------------------
NIVEL_VERDE = "verde"
NIVEL_AMARILLO = "amarillo"
NIVEL_ROJO = "rojo"


def _pkg(emoji: str, nivel: str, titulo: str, mensaje: str, accion: Optional[str] = None) -> Dict:
    return {
        "emoji": emoji,
        "nivel": nivel,
        "titulo": titulo,
        "mensaje": mensaje,
        "accion": accion,
    }


# ---------------------------------------------------------------------------
# Radiación / día solar
# ---------------------------------------------------------------------------
def traducir_radiacion(ghi: Optional[float]) -> Dict:
    """Traduce GHI (kWh/m²/día) a mensaje accionable."""
    if ghi is None:
        return _pkg("❓", NIVEL_AMARILLO, "Sin datos solares", "Aún no hay datos de radiación. Sincroniza Open-Meteo.", "Ir a Datos Solares")
    if ghi >= 6.0:
        return _pkg(
            "☀️", NIVEL_VERDE,
            "Día solar excelente",
            f"Hoy el sol está fuerte (≈{ghi:.1f} kWh/m²). Es ideal operar a máxima carga entre 10 AM y 2 PM.",
            "Programa equipos pesados a media mañana",
        )
    if ghi >= 4.5:
        return _pkg(
            "⛅", NIVEL_VERDE,
            "Buen día solar",
            f"La radiación de hoy (≈{ghi:.1f} kWh/m²) cubrirá una parte importante de tu consumo.",
            "Aprovecha la franja 11 AM - 1 PM",
        )
    if ghi >= 3.0:
        return _pkg(
            "🌥️", NIVEL_AMARILLO,
            "Día solar regular",
            f"Hoy hay menos sol (≈{ghi:.1f} kWh/m²). Limita el uso de aire acondicionado y equipos no esenciales.",
            "Reduce cargas no críticas",
        )
    return _pkg(
        "🌧️", NIVEL_ROJO,
        "Día solar bajo",
        f"Muy poca radiación hoy (≈{ghi:.1f} kWh/m²). Prioriza consumir desde batería o red.",
        "Carga baterías cuando haya luz",
    )


# ---------------------------------------------------------------------------
# Consumo vs comparativa
# ---------------------------------------------------------------------------
def traducir_consumo(
    consumo_hoy_kwh: Optional[float],
    consumo_ayer_kwh: Optional[float],
    tarifa_kwh: float = 943.0,
) -> Dict:
    if consumo_hoy_kwh is None:
        return _pkg("❓", NIVEL_AMARILLO, "Sin datos de consumo", "Carga tu archivo de consumo para ver el análisis.", "Subir CSV/Excel")

    costo_hoy = consumo_hoy_kwh * tarifa_kwh
    if consumo_ayer_kwh and consumo_ayer_kwh > 0:
        delta_pct = ((consumo_hoy_kwh - consumo_ayer_kwh) / consumo_ayer_kwh) * 100
    else:
        delta_pct = 0

    if delta_pct > 20:
        return _pkg(
            "🔺", NIVEL_ROJO,
            "Consumo elevado",
            f"Llevas {consumo_hoy_kwh:.0f} kWh hoy (≈ ${costo_hoy:,.0f}). Es {delta_pct:+.0f}% más que ayer.",
            "Revisa equipos encendidos sin uso",
        )
    if delta_pct > 5:
        return _pkg(
            "📈", NIVEL_AMARILLO,
            "Consumo en aumento",
            f"Llevas {consumo_hoy_kwh:.0f} kWh hoy (≈ ${costo_hoy:,.0f}), {delta_pct:+.0f}% vs ayer.",
            "Vigila los próximos picos",
        )
    if delta_pct < -10:
        return _pkg(
            "📉", NIVEL_VERDE,
            "Buen ahorro",
            f"Solo {consumo_hoy_kwh:.0f} kWh hoy (≈ ${costo_hoy:,.0f}). Es {abs(delta_pct):.0f}% menos que ayer. ¡Bien!",
            "Mantén el ritmo",
        )
    return _pkg(
        "✅", NIVEL_VERDE,
        "Consumo estable",
        f"Llevas {consumo_hoy_kwh:.0f} kWh hoy (≈ ${costo_hoy:,.0f}). Similar a ayer.",
        None,
    )


# ---------------------------------------------------------------------------
# Producción solar
# ---------------------------------------------------------------------------
def traducir_produccion_solar(
    produccion_kwh: Optional[float],
    consumo_kwh: Optional[float],
    tarifa_kwh: float = 943.0,
) -> Dict:
    if not produccion_kwh:
        return _pkg(
            "🪫", NIVEL_AMARILLO,
            "Sin paneles activos",
            "No hay producción solar registrada. Si tienes paneles, verifica el inversor.",
            "Configura capacidad de paneles",
        )
    ahorro = produccion_kwh * tarifa_kwh
    cobertura = (produccion_kwh / consumo_kwh * 100) if consumo_kwh else 0

    if cobertura >= 60:
        return _pkg(
            "🌞", NIVEL_VERDE,
            "Tus paneles están rindiendo",
            f"Generaste {produccion_kwh:.0f} kWh hoy. Cubrió el {cobertura:.0f}% de tu consumo (ahorro ≈ ${ahorro:,.0f}).",
            None,
        )
    if cobertura >= 30:
        return _pkg(
            "🌤️", NIVEL_VERDE,
            "Producción solar correcta",
            f"Tus paneles generaron {produccion_kwh:.0f} kWh (ahorro ≈ ${ahorro:,.0f}).",
            None,
        )
    return _pkg(
        "⚠️", NIVEL_AMARILLO,
        "Producción solar baja",
        f"Solo {produccion_kwh:.0f} kWh generados hoy. Puede ser por nubes o suciedad en paneles.",
        "Considera limpiar los paneles",
    )


# ---------------------------------------------------------------------------
# Riesgo de apagón
# ---------------------------------------------------------------------------
def traducir_riesgo_apagon(riesgo_pct: Optional[float]) -> Dict:
    if riesgo_pct is None:
        return _pkg("❓", NIVEL_AMARILLO, "Sin predicción de apagón", "Genera predicciones para evaluar el riesgo.", "Generar predicción")
    if riesgo_pct >= 40:
        return _pkg(
            "🔴", NIVEL_ROJO,
            "Riesgo alto de apagón",
            f"Probabilidad estimada {riesgo_pct:.0f}%. Carga baterías y prepara plan de contingencia.",
            "Reduce cargas no críticas en la noche",
        )
    if riesgo_pct >= 20:
        return _pkg(
            "🟡", NIVEL_AMARILLO,
            "Riesgo medio de apagón",
            f"Probabilidad estimada {riesgo_pct:.0f}%. Mantén equipos críticos respaldados.",
            "Verifica nivel de batería",
        )
    return _pkg(
        "🟢", NIVEL_VERDE,
        "Riesgo bajo de apagón",
        f"Probabilidad estimada {riesgo_pct:.0f}%. Operación normal.",
        None,
    )


# ---------------------------------------------------------------------------
# Calidad del aire / polvo en paneles
# ---------------------------------------------------------------------------
def traducir_polvo(pm10: Optional[float], polvo: Optional[float] = None) -> Dict:
    valor = polvo if polvo is not None else pm10
    if valor is None:
        return _pkg("❓", NIVEL_AMARILLO, "Sin datos de aire", "Calidad del aire no disponible.", None)
    if valor >= 80:
        return _pkg(
            "🟤", NIVEL_ROJO,
            "Polvo alto en el aire",
            f"PM10/polvo en {valor:.0f} µg/m³. Tus paneles pueden perder hasta 15% de eficiencia.",
            "Limpia los paneles esta semana",
        )
    if valor >= 40:
        return _pkg(
            "💨", NIVEL_AMARILLO,
            "Polvo moderado",
            f"Aire con polvo ({valor:.0f} µg/m³). Considera limpieza pronto.",
            "Programa limpieza próxima",
        )
    return _pkg(
        "🌬️", NIVEL_VERDE,
        "Aire limpio",
        f"Buena calidad del aire ({valor:.0f} µg/m³). Paneles operando con eficiencia plena.",
        None,
    )


# ---------------------------------------------------------------------------
# Batería
# ---------------------------------------------------------------------------
def traducir_bateria(nivel_pct: Optional[float]) -> Dict:
    if nivel_pct is None:
        return _pkg("🔋", NIVEL_AMARILLO, "Sin lectura de batería", "No hay datos del banco de baterías.", None)
    if nivel_pct >= 70:
        return _pkg("🔋", NIVEL_VERDE, "Batería cargada", f"Nivel {nivel_pct:.0f}%. Listo para apagones.", None)
    if nivel_pct >= 30:
        return _pkg("🔋", NIVEL_AMARILLO, "Batería media", f"Nivel {nivel_pct:.0f}%. Recarga si esperas apagón.", "Reduce consumo nocturno")
    return _pkg(
        "🪫", NIVEL_ROJO,
        "Batería baja",
        f"Solo {nivel_pct:.0f}% de carga. Apaga equipos no esenciales.",
        "Conecta cargas a red mientras se carga",
    )


# ---------------------------------------------------------------------------
# Resumen completo del día (todas las capas)
# ---------------------------------------------------------------------------
def construir_resumen_dia(
    ghi: Optional[float] = None,
    consumo_hoy_kwh: Optional[float] = None,
    consumo_ayer_kwh: Optional[float] = None,
    produccion_kwh: Optional[float] = None,
    riesgo_apagon_pct: Optional[float] = None,
    polvo_pm10: Optional[float] = None,
    nivel_bateria_pct: Optional[float] = None,
    tarifa_kwh: float = 943.0,
) -> Dict:
    """Devuelve el paquete completo de tarjetas para la vista 'simple'."""
    tarjetas = [
        ("dia_solar", traducir_radiacion(ghi)),
        ("consumo", traducir_consumo(consumo_hoy_kwh, consumo_ayer_kwh, tarifa_kwh)),
        ("produccion", traducir_produccion_solar(produccion_kwh, consumo_hoy_kwh, tarifa_kwh)),
        ("riesgo_apagon", traducir_riesgo_apagon(riesgo_apagon_pct)),
        ("aire", traducir_polvo(polvo_pm10)),
        ("bateria", traducir_bateria(nivel_bateria_pct)),
    ]
    score_global = _score_global([t for _, t in tarjetas])
    return {
        "score_global": score_global,
        "tarjetas": {k: v for k, v in tarjetas},
    }


def _score_global(tarjetas: list) -> Dict:
    """Calcula un nivel global agregando los semáforos."""
    rojos = sum(1 for t in tarjetas if t.get("nivel") == NIVEL_ROJO)
    amarillos = sum(1 for t in tarjetas if t.get("nivel") == NIVEL_AMARILLO)
    if rojos >= 2:
        return {"emoji": "🔴", "nivel": NIVEL_ROJO, "titulo": "Día crítico — atención requerida"}
    if rojos == 1 or amarillos >= 3:
        return {"emoji": "🟡", "nivel": NIVEL_AMARILLO, "titulo": "Día con avisos importantes"}
    return {"emoji": "🟢", "nivel": NIVEL_VERDE, "titulo": "Día energético tranquilo"}
