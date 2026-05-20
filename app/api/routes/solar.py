from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, timedelta

from app.db.session import get_db
from app.models.models import RadiacionSolar, User
from app.schemas.schemas import RadiacionResponse
from app.api.deps.auth import get_current_user
from app.services.nasa_power import nasa_service
from app.services.openweather import openweather_service

router = APIRouter(prefix="/solar", tags=["Datos Solares"])


@router.get("/radiacion", response_model=List[RadiacionResponse])
def get_radiacion(
    days: int = Query(30, ge=1, le=365),
    fuente: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener histórico de radiación solar almacenado."""
    since = datetime.now() - timedelta(days=days)
    q = db.query(RadiacionSolar).filter(RadiacionSolar.fecha >= since)
    if fuente:
        q = q.filter(RadiacionSolar.fuente == fuente)
    return q.order_by(desc(RadiacionSolar.fecha)).all()


@router.get("/radiacion/latest", response_model=Optional[RadiacionResponse])
def get_radiacion_latest(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Último dato de radiación solar registrado."""
    return (
        db.query(RadiacionSolar)
        .order_by(desc(RadiacionSolar.fecha))
        .first()
    )


@router.post("/sync/nasa", response_model=List[RadiacionResponse])
async def sync_nasa_power(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sincronizar datos desde NASA POWER API."""
    try:
        data = await nasa_service.get_last_days(days=days)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    created = []
    for item in data:
        # Evitar duplicados por fecha + fuente
        existing = (
            db.query(RadiacionSolar)
            .filter(
                RadiacionSolar.fecha == item["fecha"],
                RadiacionSolar.fuente == item["fuente"],
            )
            .first()
        )
        if existing:
            # Actualizar valores
            for k, v in item.items():
                setattr(existing, k, v)
            created.append(existing)
        else:
            rec = RadiacionSolar(**item)
            db.add(rec)
            created.append(rec)
    db.commit()
    for r in created:
        db.refresh(r)
    return created


@router.get("/weather/current")
async def get_current_weather(
    current_user: User = Depends(get_current_user),
):
    """Clima actual en Riohacha (OpenWeather)."""
    return await openweather_service.get_current_weather()


@router.get("/weather/forecast")
async def get_forecast(
    current_user: User = Depends(get_current_user),
):
    """Pronóstico meteorológico 5 días (OpenWeather)."""
    return await openweather_service.get_forecast()
