"""
Agente de Predicción.
Predice consumo futuro, producción solar y riesgo de apagones (24-72h).
Usa promedios móviles y patrones simples (sin ML pesado para MVP).
"""
from typing import List, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc
import statistics

from app.models.models import (
    ConsumoEnergetico,
    RadiacionSolar,
    Prediccion,
    Empresa,
)
from app.services.openweather import openweather_service
from app.services.agents.agente_solar import agente_solar


class AgentePrediccion:
    """Genera predicciones a 24-72h."""

    async def predecir(
        self,
        db: Session,
        empresa: Empresa,
        horas_horizonte: int = 72,
    ) -> Dict:
        """Genera predicciones y guarda en BD."""
        ahora = datetime.now()

        # 1. Promedio histórico de consumo
        since = ahora - timedelta(days=30)
        consumos = (
            db.query(ConsumoEnergetico)
            .filter(
                ConsumoEnergetico.empresa_id == empresa.id,
                ConsumoEnergetico.fecha >= since,
            )
            .all()
        )

        if consumos:
            promedio_diario = sum(c.consumo_kwh for c in consumos) / len(consumos)
            std = (
                statistics.stdev([c.consumo_kwh for c in consumos])
                if len(consumos) > 1
                else 0
            )
            confianza_consumo = max(50.0, min(95.0, 100 - (std / max(promedio_diario, 1)) * 100))
        else:
            promedio_diario = 0
            confianza_consumo = 50.0

        # 2. Pronóstico meteorológico
        forecast = await openweather_service.get_forecast()

        # 3. Predicción de producción solar por día
        producciones_dia = {}
        for item in forecast:
            fecha_dia = item["fecha"].date()
            # Estimación rudimentaria: a menor nubosidad, mayor GHI
            nubosidad = item.get("nubosidad", 30) or 30
            ghi_estimado = 5.5 * (1 - nubosidad / 100)  # Base 5.5 kWh/m²/día Riohacha
            produccion_3h = agente_solar.calcular_produccion_estimada_kwh(
                ghi_estimado / 8,  # 8 períodos de 3h diurnos aprox
                empresa.capacidad_paneles_kw,
            )
            producciones_dia[fecha_dia] = producciones_dia.get(fecha_dia, 0) + produccion_3h

        predicciones_creadas = []
        creadas_resumen = []

        for fecha_dia, produccion_total in producciones_dia.items():
            fecha_objetivo = datetime.combine(fecha_dia, datetime.min.time())
            if (fecha_objetivo - ahora).total_seconds() / 3600 > horas_horizonte:
                continue

            # Predicción producción
            p1 = Prediccion(
                empresa_id=empresa.id,
                fecha_prediccion=ahora,
                fecha_objetivo=fecha_objetivo,
                tipo="produccion_solar",
                valor=round(produccion_total, 2),
                unidad="kWh",
                confianza_pct=75.0,
            )
            db.add(p1)

            # Predicción consumo
            p2 = Prediccion(
                empresa_id=empresa.id,
                fecha_prediccion=ahora,
                fecha_objetivo=fecha_objetivo,
                tipo="consumo",
                valor=round(promedio_diario, 2),
                unidad="kWh",
                confianza_pct=round(confianza_consumo, 1),
            )
            db.add(p2)

            # Predicción costo neto
            costo = max(0, (promedio_diario - produccion_total) * empresa.tarifa_kwh)
            p3 = Prediccion(
                empresa_id=empresa.id,
                fecha_prediccion=ahora,
                fecha_objetivo=fecha_objetivo,
                tipo="costo",
                valor=round(costo, 0),
                unidad="COP",
                confianza_pct=round(confianza_consumo, 1),
            )
            db.add(p3)

            predicciones_creadas.extend([p1, p2, p3])
            creadas_resumen.append({
                "fecha": fecha_objetivo.isoformat(),
                "produccion_solar_kwh": round(produccion_total, 2),
                "consumo_kwh": round(promedio_diario, 2),
                "costo_cop": round(costo, 0),
            })

        # 4. Riesgo de apagón (basado en nubosidad alta + consumo alto)
        max_nubosidad = max((f.get("nubosidad", 0) or 0 for f in forecast[:24]), default=0)
        riesgo_apagon = 0.0
        if max_nubosidad > 75:
            riesgo_apagon = 40.0
        elif max_nubosidad > 50:
            riesgo_apagon = 25.0
        else:
            riesgo_apagon = 10.0

        p_apagon = Prediccion(
            empresa_id=empresa.id,
            fecha_prediccion=ahora,
            fecha_objetivo=ahora + timedelta(hours=24),
            tipo="riesgo_apagon",
            valor=riesgo_apagon,
            unidad="%",
            confianza_pct=60.0,
        )
        db.add(p_apagon)
        predicciones_creadas.append(p_apagon)

        db.commit()
        for p in predicciones_creadas:
            db.refresh(p)

        return {
            "predicciones_diarias": creadas_resumen,
            "riesgo_apagon_24h_pct": riesgo_apagon,
            "promedio_consumo_diario_kwh": round(promedio_diario, 2),
            "total_predicciones_guardadas": len(predicciones_creadas),
        }


agente_prediccion = AgentePrediccion()
