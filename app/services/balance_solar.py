"""
Balance solar diario de una instalación registrada: cuánto producen los paneles, cuánto se consume,
qué parte cubre el sol, qué guarda la batería, qué sobra (excedente) y qué se toma de la red.

- Producción: radiación global diaria REAL de Open-Meteo (respaldo NASA POWER) y su pronóstico para
  hoy y los próximos días, por la potencia pico y el rendimiento del sistema (PR). Es una estimación
  con datos reales de clima, no una lectura del inversor.
- Consumo: los aparatos registrados (potencia x horas x cantidad); si no hay, el consumo diario del
  perfil de la instalación; si tampoco, el promedio de la factura de Air-e.
- Batería: balance día a día. El sol cubre primero el consumo del día; lo que sobra carga el banco y
  lo que no cabe es excedente. La batería cubre lo que falta y el consumo de la noche, sin bajar de la
  reserva mínima (30 %) que queda para los cortes de luz. Lo demás sale de la red.
"""
from __future__ import annotations

import time
from datetime import date, datetime, timedelta
from datetime import time as dtime
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import AparatoUsuario, ConsumoEnergetico, Empresa, RadiacionSolar
from app.services.instalacion_solar import obtener_instalacion

PR_DEFECTO = 0.80            # pérdidas por temperatura, polvo, cableado e inversor
RESERVA_MINIMA = 0.30        # la batería no baja de aquí: queda para los cortes de luz
DOD_DEFECTO = 0.80
EFICIENCIA_DEFECTO = 0.90    # ida y vuelta de la batería
FRACCION_DIURNA_DEFECTO = 0.5
DIAS_MINIMOS_FACTURA = 7
DIAS_RECIENTES = 10          # días ya pasados que se piden al pronóstico mientras el archivo los publica
PRIORIDAD_FUENTE = {"open_meteo": 0, "nasa_power": 1}
NOMBRE_FUENTE = {"open_meteo": "Open-Meteo", "nasa_power": "NASA POWER"}
SEGUNDOS_CACHE = 600
_cache: Dict = {}


def parametros_sistema(inst) -> Dict:
    bateria = float(inst.bateria_kwh or 0)
    dod = (inst.dod_pct / 100) if inst.dod_pct else DOD_DEFECTO
    fraccion_util = max(0.0, min(dod, 1 - RESERVA_MINIMA))
    diurna, nocturna = inst.demanda_diurna_kwh, inst.demanda_nocturna_kwh
    if diurna is not None and nocturna is not None and diurna + nocturna > 0:
        fraccion_diurna = diurna / (diurna + nocturna)
    else:
        fraccion_diurna = FRACCION_DIURNA_DEFECTO
    return {
        "kwp": float(inst.potencia_pico_kw or 0),
        "pr": (inst.rendimiento_pr_pct / 100) if inst.rendimiento_pr_pct else PR_DEFECTO,
        "bateria_kwh": round(bateria, 3),
        "bateria_util_kwh": round(bateria * fraccion_util, 3),
        "reserva_pct": round((1 - fraccion_util) * 100) if bateria else None,
        "numero_baterias": inst.numero_baterias,
        "eficiencia_bateria": (inst.eficiencia_ciclo_pct / 100) if inst.eficiencia_ciclo_pct else EFICIENCIA_DEFECTO,
        "fraccion_diurna": round(fraccion_diurna, 3),
        "soc_inicial_pct": inst.soc_pct,
    }


def demanda_factura(db: Session, empresa: Empresa) -> Optional[Dict]:
    """Promedio diario de la factura de Air-e (solo lo que se tomó de la red)."""
    hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    filas = (
        db.query(func.date(ConsumoEnergetico.fecha), func.sum(ConsumoEnergetico.consumo_kwh))
        .filter(
            ConsumoEnergetico.empresa_id == empresa.id,
            ConsumoEnergetico.escenario == "real",
            ConsumoEnergetico.fecha >= hoy - timedelta(days=30),
            ConsumoEnergetico.fecha < hoy + timedelta(days=1),
        )
        .group_by(func.date(ConsumoEnergetico.fecha))
        .all()
    )
    if len(filas) < DIAS_MINIMOS_FACTURA:
        return None
    return {
        "kwh_dia": round(sum(float(k or 0) for _, k in filas) / len(filas), 2),
        "fuente": "factura",
        "detalle": "el promedio diario de tu factura de Air-e",
    }


def candidatas_demanda(db: Session, empresa: Empresa, inst) -> List[Dict]:
    """Estimaciones del consumo diario total, en orden de preferencia: aparatos y perfil de la instalación."""
    candidatas = []
    aparatos = db.query(AparatoUsuario).filter(AparatoUsuario.empresa_id == empresa.id).all()
    total_mes = sum(a.consumo_kwh_mes for a in aparatos)
    if total_mes > 0:
        candidatas.append({
            "kwh_dia": round(total_mes / 30, 2),
            "fuente": "aparatos",
            "detalle": f"tus {len(aparatos)} aparatos registrados (potencia x horas de uso)",
        })
    if inst is not None and inst.consumo_diario_kwh:
        candidatas.append({
            "kwh_dia": round(float(inst.consumo_diario_kwh), 2),
            "fuente": "perfil",
            "detalle": "el consumo diario que registraste para tu instalación",
        })
    return candidatas


def elegir_demanda(
    candidatas: List[Dict],
    fechas: List[date],
    producciones: List[Optional[float]],
    factura: Dict[date, float],
    p: Dict,
    tarifa: float,
    respaldo: Optional[Dict] = None,
) -> Dict:
    """Con paneles, la factura solo muestra lo que se tomó de la red. Si hay factura, se usa la
    estimación de consumo cuyo resultado de red se parece más a ella; si no, la primera disponible."""
    if not candidatas:
        return respaldo or {"kwh_dia": None, "fuente": None, "detalle": "registra tus aparatos o tu consumo diario"}
    indices = [i for i, d in enumerate(fechas) if d in factura and producciones[i] is not None]
    if len(candidatas) == 1 or len(indices) < DIAS_MINIMOS_FACTURA:
        return {**candidatas[0], "elegida_por": "prioridad"}
    real = sum(factura[fechas[i]] for i in indices)
    comparacion = []
    for c in candidatas:
        sim = simular_serie(producciones, c["kwh_dia"], p, tarifa)
        estimada = sum(sim[i]["red_kwh"] for i in indices)
        comparacion.append({**c, "red_estimada_kwh": round(estimada, 2), "_error": abs(estimada - real)})
    mejor = min(comparacion, key=lambda c: c["_error"])
    return {
        "kwh_dia": mejor["kwh_dia"],
        "fuente": mejor["fuente"],
        "detalle": mejor["detalle"],
        "elegida_por": "factura",
        "factura_red_kwh": round(real, 2),
        "comparacion": [{k: v for k, v in c.items() if k != "_error"} for c in comparacion],
    }


def _fecha(valor) -> Optional[date]:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str) and valor:
        try:
            return datetime.fromisoformat(valor.replace("Z", "")[:19]).date()
        except ValueError:
            return None
    return None


def radiacion_bd(db: Session, desde: date, hasta: date) -> Dict[date, Dict]:
    """Radiación diaria real guardada (Open-Meteo antes que NASA POWER), sin datos sintéticos."""
    filas = (
        db.query(RadiacionSolar)
        .filter(
            RadiacionSolar.fecha >= datetime.combine(desde, dtime.min),
            RadiacionSolar.fecha < datetime.combine(hasta + timedelta(days=1), dtime.min),
            RadiacionSolar.escenario == "real",
            RadiacionSolar.origen_dato == "real_api",
            RadiacionSolar.ghi.isnot(None),
        )
        .all()
    )
    mejor: Dict[date, Dict] = {}
    for f in filas:
        d = f.fecha.date()
        prioridad = PRIORIDAD_FUENTE.get(f.fuente, 9)
        if d not in mejor or prioridad < mejor[d]["_prioridad"]:
            mejor[d] = {"ghi": float(f.ghi), "fuente": f.fuente, "origen": "historico", "_prioridad": prioridad}
    return mejor


async def radiacion_api(dias: int, pronostico: int) -> Dict[date, Dict]:
    """Últimos días (archivo + pronóstico reciente) y pronóstico de Open-Meteo. {} si no responde."""
    clave = (date.today().isoformat(), dias, pronostico)
    guardado = _cache.get(clave)
    if guardado and time.monotonic() - guardado[0] < SEGUNDOS_CACHE:
        return guardado[1]

    from app.services.openmeteo import openmeteo_service

    resultado: Dict[date, Dict] = {}
    hoy = date.today()
    try:
        for item in await openmeteo_service.get_serie_reciente(days=dias):
            d = _fecha(item.get("fecha"))
            if d and item.get("ghi") is not None and d < hoy:
                resultado[d] = {"ghi": float(item["ghi"]), "fuente": "open_meteo", "origen": "historico"}
    except Exception as e:  # sin internet no se inventan datos: esos días quedan sin producción
        print(f"[BALANCE SOLAR] Sin histórico reciente de Open-Meteo: {e}")
    try:
        # Con past_days llegan también los días recientes que el archivo aún no publica
        recientes = await openmeteo_service.get_forecast_diario(
            days=pronostico + 1, allow_synthetic=False, past_days=DIAS_RECIENTES
        )
        for item in recientes:
            d = _fecha(item.get("fecha"))
            if not d or item.get("ghi") is None:
                continue
            if d >= hoy:
                resultado[d] = {"ghi": float(item["ghi"]), "fuente": "open_meteo", "origen": "pronostico"}
            elif d not in resultado:
                resultado[d] = {"ghi": float(item["ghi"]), "fuente": "open_meteo", "origen": "reciente"}
    except Exception as e:
        print(f"[BALANCE SOLAR] Sin pronóstico de Open-Meteo: {e}")
    if resultado:
        _cache[clave] = (time.monotonic(), resultado)
    return resultado


def consumo_red_por_dia(db: Session, empresa: Empresa, desde: date, hasta: date) -> Dict[date, float]:
    """Energía tomada de la red según la factura o los datos cargados (escenario real)."""
    filas = (
        db.query(func.date(ConsumoEnergetico.fecha), func.sum(ConsumoEnergetico.consumo_kwh))
        .filter(
            ConsumoEnergetico.empresa_id == empresa.id,
            ConsumoEnergetico.escenario == "real",
            ConsumoEnergetico.fecha >= datetime.combine(desde, dtime.min),
            ConsumoEnergetico.fecha < datetime.combine(hasta + timedelta(days=1), dtime.min),
        )
        .group_by(func.date(ConsumoEnergetico.fecha))
        .all()
    )
    return {_fecha(d): round(float(k or 0), 3) for d, k in filas if _fecha(d)}


def simular_serie(producciones: List[Optional[float]], demanda: Optional[float], p: Dict, tarifa: float) -> List[Dict]:
    """Balance día a día; la carga de la batería pasa de un día al siguiente."""
    bateria = p["bateria_kwh"]
    reserva = bateria - p["bateria_util_kwh"]
    efic = p["eficiencia_bateria"] or EFICIENCIA_DEFECTO
    soc_ini = p.get("soc_inicial_pct")
    carga = bateria * (soc_ini / 100) if soc_ini is not None else bateria
    carga = min(max(carga, reserva), bateria)
    demanda = demanda or 0.0
    d_dia = demanda * p["fraccion_diurna"]
    d_noche = demanda - d_dia
    salida = []
    for produccion in producciones:
        if produccion is None:
            salida.append({
                "produccion_kwh": None, "consumo_kwh": round(demanda, 2), "autoconsumo_kwh": None,
                "carga_bateria_kwh": None, "descarga_bateria_kwh": None, "excedente_kwh": None,
                "red_kwh": None, "red_noche_kwh": None, "consumo_noche_kwh": round(d_noche, 2),
                "solar_aprovechada_kwh": None, "cobertura_pct": None,
                "bateria_anochecer_pct": None, "bateria_amanecer_pct": None,
                "ahorro_cop": None, "costo_red_cop": None,
            })
            continue
        directo = min(produccion, d_dia)
        sobrante = produccion - directo
        a_cargar = min(sobrante, bateria - carga)
        carga += a_cargar
        excedente = sobrante - a_cargar
        # La batería cubre lo que el sol no alcanzó de día y el consumo de la noche
        falta_dia = d_dia - directo
        desc_dia = min(falta_dia, max(carga - reserva, 0) * efic)
        carga -= desc_dia / efic if efic else 0
        anochecer = carga
        desc_noche = min(d_noche, max(carga - reserva, 0) * efic)
        carga -= desc_noche / efic if efic else 0
        descarga = desc_dia + desc_noche
        red = (falta_dia - desc_dia) + (d_noche - desc_noche)
        aprovechada = directo + descarga
        salida.append({
            "produccion_kwh": round(produccion, 2),
            "consumo_kwh": round(demanda, 2),
            "autoconsumo_kwh": round(directo, 2),
            "carga_bateria_kwh": round(a_cargar, 2),
            "descarga_bateria_kwh": round(descarga, 2),
            "excedente_kwh": round(excedente, 2),
            "red_kwh": round(red, 2),
            "red_noche_kwh": round(d_noche - desc_noche, 2),
            "consumo_noche_kwh": round(d_noche, 2),
            "solar_aprovechada_kwh": round(aprovechada, 2),
            "cobertura_pct": round(aprovechada / demanda * 100, 1) if demanda else None,
            "bateria_anochecer_pct": round(anochecer / bateria * 100) if bateria else None,
            "bateria_amanecer_pct": round(carga / bateria * 100) if bateria else None,
            "ahorro_cop": round(aprovechada * tarifa),
            "costo_red_cop": round(red * tarifa),
        })
    return salida


def _suma(dias: List[Dict], campo: str) -> float:
    return round(sum(d[campo] for d in dias if d.get(campo) is not None), 2)


async def calcular_balance(
    db: Session, empresa: Empresa, days: int = 30, pronostico: int = 3, usar_api: bool = True
) -> Dict:
    inst = obtener_instalacion(db, empresa.id)
    if inst is None or (inst.potencia_pico_kw or 0) <= 0:
        return {"disponible": False, "motivo": "Esta cuenta no tiene paneles solares registrados."}

    p = parametros_sistema(inst)
    tarifa = float(empresa.tarifa_kwh or 0)
    hoy = date.today()
    desde = hoy - timedelta(days=max(days, 1) - 1)
    fechas = [desde + timedelta(days=i) for i in range((hoy - desde).days + 1 + max(pronostico, 0))]

    radiacion = radiacion_bd(db, desde, hoy)
    if usar_api:
        for d, v in (await radiacion_api(days, pronostico)).items():
            if d >= hoy or d not in radiacion:
                radiacion[d] = v
    factura = consumo_red_por_dia(db, empresa, desde, hoy)

    producciones = []
    for d in fechas:
        r = radiacion.get(d)
        producciones.append(round(p["kwp"] * r["ghi"] * p["pr"], 3) if r else None)
    demanda = elegir_demanda(
        candidatas_demanda(db, empresa, inst), fechas, producciones, factura, p, tarifa,
        respaldo=demanda_factura(db, empresa),
    )
    simulados = simular_serie(producciones, demanda["kwh_dia"], p, tarifa)

    dias = []
    for d, sim in zip(fechas, simulados):
        r = radiacion.get(d) or {}
        dias.append({
            "fecha": d.isoformat(),
            "tipo": "pronostico" if d > hoy else ("hoy" if d == hoy else "historico"),
            "ghi_kwh_m2": r.get("ghi"),
            "fuente_radiacion": r.get("fuente"),
            "red_factura_kwh": factura.get(d),
            **sim,
        })

    pasados = [d for d in dias if d["tipo"] != "pronostico" and d["produccion_kwh"] is not None]
    previos = [d for d in pasados if d["tipo"] == "historico"][-14:]
    hoy_item = next((d for d in dias if d["tipo"] == "hoy"), None)
    manana_item = next((d for d in dias if d["tipo"] == "pronostico"), None)
    con_factura = [d for d in pasados if d.get("red_factura_kwh") is not None]

    resumen = {
        "dias_con_datos": len(pasados),
        "produccion_kwh": _suma(pasados, "produccion_kwh"),
        "consumo_kwh": _suma(pasados, "consumo_kwh"),
        "solar_aprovechada_kwh": _suma(pasados, "solar_aprovechada_kwh"),
        "excedente_kwh": _suma(pasados, "excedente_kwh"),
        "red_kwh": _suma(pasados, "red_kwh"),
        "ahorro_cop": round(sum(d["ahorro_cop"] for d in pasados)),
        "produccion_promedio_kwh_dia": round(_suma(previos, "produccion_kwh") / len(previos), 2) if previos else None,
        "hoy": hoy_item,
        "manana": manana_item,
        "factura_red_kwh": _suma(con_factura, "red_factura_kwh") if len(con_factura) >= DIAS_MINIMOS_FACTURA else None,
        "red_estimada_mismos_dias_kwh": _suma(con_factura, "red_kwh") if len(con_factura) >= DIAS_MINIMOS_FACTURA else None,
    }
    consumo_total = resumen["consumo_kwh"]
    resumen["cobertura_pct"] = round(resumen["solar_aprovechada_kwh"] / consumo_total * 100, 1) if consumo_total else None

    fuentes = sorted({NOMBRE_FUENTE.get(d["fuente_radiacion"], d["fuente_radiacion"]) for d in dias if d["fuente_radiacion"]})
    notas = []
    sin_dato = [d["fecha"] for d in dias if d["tipo"] != "pronostico" and d["produccion_kwh"] is None]
    if sin_dato:
        notas.append(f"{len(sin_dato)} día(s) sin radiación disponible: no se estima su producción.")
    if demanda["kwh_dia"] is None:
        notas.append("Sin consumo registrado: agrega tus aparatos para calcular cuánto cubre el sol.")
    if demanda.get("elegida_por") == "factura":
        descartadas = [c for c in demanda["comparacion"] if c["fuente"] != demanda["fuente"]]
        for c in descartadas:
            notas.append(
                f"Con {c['detalle']} el consumo sería de {c['kwh_dia']:,.1f} kWh al día y la red te habría dado "
                f"{c['red_estimada_kwh']:,.0f} kWh, pero tu factura marca {demanda['factura_red_kwh']:,.0f} kWh: "
                f"por eso se usa {demanda['detalle']} ({demanda['kwh_dia']:,.1f} kWh al día)."
            )
        if any(c["fuente"] == "aparatos" for c in descartadas):
            notas.append("Revisa las horas de uso de tus aparatos en Mis Aparatos para que coincidan con tu consumo real.")
    elif demanda["fuente"] == "factura":
        notas.append("Solo hay datos de tu factura (lo que tomas de la red): agrega tus aparatos para ver tu consumo total.")
    if resumen["factura_red_kwh"] is not None and resumen["red_estimada_mismos_dias_kwh"]:
        real, estimado = resumen["factura_red_kwh"], resumen["red_estimada_mismos_dias_kwh"]
        if estimado > 0 and (real < estimado * 0.5 or real > estimado * 1.5):
            notas.append(
                f"La red que estimamos ({estimado:,.0f} kWh) no coincide con tu factura ({real:,.0f} kWh) en los "
                "mismos días: revisa tu consumo diario y tus aparatos."
            )

    return {
        "disponible": True,
        "empresa_id": empresa.id,
        "tarifa_kwh": tarifa,
        "sistema": p,
        "demanda": demanda,
        "dias": dias,
        "resumen": resumen,
        "fuentes_radiacion": fuentes,
        "metodo": (
            f"Producción = radiación diaria x {p['kwp']:g} kWp x rendimiento {p['pr'] * 100:.0f} %. "
            f"Consumo según {demanda['detalle']}. Reserva de batería {p['reserva_pct'] or 0} %."
        ),
        "notas": notas,
    }


def solar_aprovechada_mes_bd(db: Session, empresa: Empresa) -> Optional[float]:
    """kWh al mes que el sol cubre (directo o por la batería), con la radiación real guardada en la BD.

    Sirve para que el consumo total de una empresa con paneles sea la factura (red) más lo que puso el sol.
    None si no hay instalación, consumo o al menos una semana de radiación.
    """
    inst = obtener_instalacion(db, empresa.id)
    if inst is None or (inst.potencia_pico_kw or 0) <= 0:
        return None
    hoy = date.today()
    radiacion = radiacion_bd(db, hoy - timedelta(days=29), hoy)
    if len(radiacion) < DIAS_MINIMOS_FACTURA:
        return None
    p = parametros_sistema(inst)
    tarifa = float(empresa.tarifa_kwh or 0)
    # Día típico del mes: la producción promedio con la radiación guardada
    produccion_media = sum(p["kwp"] * r["ghi"] * p["pr"] for r in radiacion.values()) / len(radiacion)
    factura = consumo_red_por_dia(db, empresa, hoy - timedelta(days=29), hoy)
    if len(factura) >= DIAS_MINIMOS_FACTURA:
        fechas = sorted(factura)
    else:
        fechas = [hoy - timedelta(days=i) for i in range(29, -1, -1)]
    producciones = [produccion_media] * len(fechas)
    demanda = elegir_demanda(candidatas_demanda(db, empresa, inst), fechas, producciones, factura, p, tarifa)["kwh_dia"]
    if not demanda:
        return None
    simulados = simular_serie(producciones, demanda, p, tarifa)
    promedio = sum(s["solar_aprovechada_kwh"] for s in simulados) / len(simulados)
    return round(promedio * 30, 2)
