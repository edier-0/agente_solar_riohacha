"""
Endpoints de insights orientados al usuario común (vista 'simple').
Combinan:
- Datos crudos de BD y APIs externas.
- Capa de traducción (insights_translator).
- LLM (Ollama) para resumen narrativo opcional.
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.session import get_db
from app.models.models import (
    Empresa,
    User,
    UserRole,
    ConsumoEnergetico,
    RadiacionSolar,
    Prediccion,
)
from app.api.deps.auth import get_current_user
from app.services.insights_translator import construir_resumen_dia
from app.services.openmeteo import openmeteo_service
from app.services.ollama_client import ollama_client

router = APIRouter(prefix="/insights", tags=["Insights (Vista Simple)"])


def _check_acceso(current_user: User, empresa_id: int):
    if (
        current_user.role == UserRole.EMPRESA
        and current_user.empresa_id != empresa_id
    ):
        raise HTTPException(status_code=403, detail="Sin permisos")


@router.get("/diario/{empresa_id}")
async def insights_diario(
    empresa_id: int,
    incluir_resumen_llm: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Devuelve el panel humano-amigable del día para la empresa:
    - score global (verde/amarillo/rojo)
    - tarjetas de día solar, consumo, producción, riesgo, aire y batería
    - resumen narrativo opcional generado por Ollama
    """
    _check_acceso(current_user, empresa_id)
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    ahora = datetime.now()
    inicio_hoy = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    inicio_ayer = inicio_hoy - timedelta(days=1)

    # ---- Consumo hoy / ayer ----
    consumos_hoy = (
        db.query(ConsumoEnergetico)
        .filter(
            ConsumoEnergetico.empresa_id == empresa_id,
            ConsumoEnergetico.fecha >= inicio_hoy,
        )
        .all()
    )
    consumos_ayer = (
        db.query(ConsumoEnergetico)
        .filter(
            ConsumoEnergetico.empresa_id == empresa_id,
            ConsumoEnergetico.fecha >= inicio_ayer,
            ConsumoEnergetico.fecha < inicio_hoy,
        )
        .all()
    )
    consumo_hoy_kwh = sum(c.consumo_kwh for c in consumos_hoy) if consumos_hoy else None
    consumo_ayer_kwh = sum(c.consumo_kwh for c in consumos_ayer) if consumos_ayer else None
    produccion_kwh = (
        sum(c.produccion_solar_kwh or 0 for c in consumos_hoy) if consumos_hoy else None
    )
    nivel_bateria_pct = (
        consumos_hoy[-1].nivel_bateria_pct if consumos_hoy else None
    )

    # ---- Radiación más reciente (BD) ----
    radiacion = (
        db.query(RadiacionSolar)
        .order_by(desc(RadiacionSolar.fecha))
        .first()
    )
    ghi_actual = radiacion.ghi if radiacion else None

    # ---- Riesgo de apagón (última predicción) ----
    pred_apagon = (
        db.query(Prediccion)
        .filter(
            Prediccion.empresa_id == empresa_id,
            Prediccion.tipo == "riesgo_apagon",
        )
        .order_by(desc(Prediccion.fecha_prediccion))
        .first()
    )
    riesgo_pct = pred_apagon.valor if pred_apagon else None

    # ---- Calidad del aire (Open-Meteo, no requiere BD) ----
    polvo_pm10: Optional[float] = None
    try:
        aire = await openmeteo_service.get_calidad_aire()
        if aire.get("disponible") and aire.get("datos"):
            primer = aire["datos"][0]
            polvo_pm10 = primer.get("polvo") or primer.get("pm10")
    except Exception:
        polvo_pm10 = None

    # ---- Construir tarjetas (capa de traducción) ----
    resumen = construir_resumen_dia(
        ghi=ghi_actual,
        consumo_hoy_kwh=consumo_hoy_kwh,
        consumo_ayer_kwh=consumo_ayer_kwh,
        produccion_kwh=produccion_kwh,
        riesgo_apagon_pct=riesgo_pct,
        polvo_pm10=polvo_pm10,
        nivel_bateria_pct=nivel_bateria_pct,
        tarifa_kwh=empresa.tarifa_kwh,
    )

    # ---- Resumen narrativo (LLM) ----
    resumen_llm = None
    if incluir_resumen_llm:
        resumen_llm = await ollama_client.generar_resumen_diario(
            empresa_nombre=empresa.nombre,
            empresa_tipo=empresa.tipo or "PYME",
            resumen=resumen,
        )

    return {
        "empresa": {
            "id": empresa.id,
            "nombre": empresa.nombre,
            "tipo": empresa.tipo,
        },
        "fecha": ahora.isoformat(),
        "score_global": resumen["score_global"],
        "tarjetas": resumen["tarjetas"],
        "resumen_narrativo": resumen_llm,
        "fuente_narrativa": "llm" if (resumen_llm and await ollama_client.is_disponible()) else "plantilla",
    }
