from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, timedelta

from app.db.session import get_db
from app.models.models import RadiacionSolar, User
from app.schemas.schemas import RadiacionResponse
from app.api.deps.auth import get_current_user
from app.services.openmeteo import openmeteo_service
from app.services.openweather import openweather_service
from app.services.pvgis import pvgis_service
from app.services.nasa_power import nasa_service  # legacy / respaldo
from app.services.demo_data import get_radiacion_demo

router = APIRouter(prefix="/solar", tags=["Datos Solares"])


def _start_of_day_days_ago(days: int) -> datetime:
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return today - timedelta(days=max(days - 1, 0))


def _build_virtual_radiacion_row(item: dict, index: int) -> dict:
    fecha = item["fecha"]
    return {
        "id": 900000 + index,
        "fecha": fecha,
        "ghi": item.get("ghi"),
        "dni": item.get("dni"),
        "dhi": item.get("dhi"),
        "temperatura": item.get("temperatura"),
        "temperatura_max": item.get("temperatura_max"),
        "temperatura_min": item.get("temperatura_min"),
        "nubosidad": item.get("nubosidad"),
        "precipitacion_mm": item.get("precipitacion_mm"),
        "viento_kmh_max": item.get("viento_kmh_max"),
        "fuente": item.get("fuente", "open_meteo"),
        "escenario": item.get("escenario", "real"),
        "origen_dato": item.get("origen_dato", "forecast_api"),
        "confiabilidad": item.get("confiabilidad", 75.0),
        "created_at": datetime.now(),
    }


# ---------------------------------------------------------------------------
# LECTURA DE BD
# ---------------------------------------------------------------------------
@router.get("/radiacion", response_model=List[RadiacionResponse])
async def get_radiacion(
    days: int = Query(30, ge=1, le=365),
    fuente: Optional[str] = None,
    escenario: Optional[str] = Query(None, pattern="^(demo|real)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener histórico de radiación solar almacenado."""
    if escenario == "demo":
        rows = get_radiacion_demo(days=days)
        if fuente:
            rows = [r for r in rows if str(r.get("fuente", "")) == fuente]
        for i, r in enumerate(rows):
            r.setdefault("id", 200000 + i)
            r.setdefault("created_at", r.get("fecha"))
        return rows
    since = _start_of_day_days_ago(days)
    q = db.query(RadiacionSolar).filter(RadiacionSolar.fecha >= since)
    if fuente:
        q = q.filter(RadiacionSolar.fuente == fuente)
    if escenario:
        q = q.filter(RadiacionSolar.escenario == escenario)
    rows = q.order_by(desc(RadiacionSolar.fecha)).all()

    should_append_forecast = (escenario in (None, "real")) and fuente in (None, "open_meteo")
    if not should_append_forecast:
        return rows

    existing_dates = {r.fecha.date() for r in rows if r.fecha}
    try:
        recent_series = await openmeteo_service.get_serie_reciente(days=days)
    except RuntimeError:
        return rows

    virtual_rows = []
    for item in recent_series:
        fecha = item.get("fecha")
        if not fecha or fecha.date() in existing_dates:
            continue
        if item.get("origen_dato") != "forecast_api":
            continue
        virtual_rows.append(_build_virtual_radiacion_row(item, len(virtual_rows)))

    combined = rows + virtual_rows
    combined.sort(key=lambda r: r["fecha"] if isinstance(r, dict) else r.fecha, reverse=True)
    return combined


@router.get("/radiacion/latest", response_model=Optional[RadiacionResponse])
async def get_radiacion_latest(
    escenario: Optional[str] = Query(None, pattern="^(demo|real)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Último dato de radiación solar registrado."""
    if escenario == "demo":
        rows = get_radiacion_demo(days=365)
        if not rows:
            return None
        row = rows[0]
        row.setdefault("id", 200000)
        row.setdefault("created_at", row.get("fecha"))
        return row
    q = db.query(RadiacionSolar)
    if escenario:
        q = q.filter(RadiacionSolar.escenario == escenario)
    latest = q.order_by(desc(RadiacionSolar.fecha)).first()

    should_append_forecast = escenario in (None, "real")
    if not should_append_forecast:
        return latest

    latest_date = latest.fecha.date() if latest and latest.fecha else None
    today = datetime.now().date()
    if latest_date == today:
        return latest

    try:
        recent_series = await openmeteo_service.get_serie_reciente(days=7)
    except RuntimeError:
        return latest

    forecast_today = next(
        (
            item
            for item in recent_series
            if item.get("fecha")
            and item["fecha"].date() == today
            and item.get("origen_dato") == "forecast_api"
        ),
        None,
    )
    if not forecast_today:
        return latest
    return _build_virtual_radiacion_row(forecast_today, 0)


# ---------------------------------------------------------------------------
# SINCRONIZACIÓN — NÚCLEO: OPEN-METEO
# ---------------------------------------------------------------------------
def _upsert_radiacion(db: Session, items: List[dict]) -> List[RadiacionSolar]:
    """Inserta o actualiza solo registros reales de radiación evitando duplicados."""
    out = []
    valid_cols = {c.name for c in RadiacionSolar.__table__.columns}
    for item in items:
        # Regla de oro: en BD solo persiste dato real (nunca synthetic fallback)
        fuente = str(item.get("fuente") or "").lower()
        origen = str(item.get("origen_dato") or "").lower()
        escenario = str(item.get("escenario") or "").lower()
        if fuente == "synthetic" or origen == "synthetic_fallback" or escenario == "demo":
            continue

        clean = {k: v for k, v in item.items() if k in valid_cols}
        existing = (
            db.query(RadiacionSolar)
            .filter(
                RadiacionSolar.fecha == clean["fecha"],
                RadiacionSolar.fuente == clean.get("fuente"),
            )
            .first()
        )
        if existing:
            for k, v in clean.items():
                setattr(existing, k, v)
            out.append(existing)
        else:
            rec = RadiacionSolar(**clean)
            db.add(rec)
            out.append(rec)
    db.commit()
    for r in out:
        db.refresh(r)
    return out


@router.post("/sync/openmeteo", response_model=List[RadiacionResponse])
async def sync_openmeteo(
    days: int = Query(30, ge=1, le=365),
    escenario: Optional[str] = Query(None, pattern="^(demo|real)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sincronizar histórico desde Open-Meteo Archive (NÚCLEO PRINCIPAL)."""
    if escenario == "demo":
        raise HTTPException(status_code=409, detail="Modo demo no persiste datos en BD")
    try:
        data = await openmeteo_service.get_ultimos_dias(days=days)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return _upsert_radiacion(db, data)


@router.post("/sync/nasa", response_model=List[RadiacionResponse])
async def sync_nasa_power(
    days: int = Query(30, ge=1, le=365),
    escenario: Optional[str] = Query(None, pattern="^(demo|real)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sincronizar desde NASA POWER (respaldo / validación cruzada)."""
    if escenario == "demo":
        raise HTTPException(status_code=409, detail="Modo demo no persiste datos en BD")
    try:
        data = await nasa_service.get_last_days(days=days)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return _upsert_radiacion(db, data)


# ---------------------------------------------------------------------------
# PRONÓSTICO — NÚCLEO: OPEN-METEO
# ---------------------------------------------------------------------------
@router.get("/forecast/horario")
async def get_forecast_horario(
    days: int = Query(7, ge=1, le=16),
    escenario: Optional[str] = Query(None, pattern="^(demo|real)$"),
    current_user: User = Depends(get_current_user),
):
    """Pronóstico horario con GHI/DNI/DHI (Open-Meteo)."""
    try:
        return await openmeteo_service.get_forecast_horario(
            days=days,
            allow_synthetic=escenario != "real",
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/forecast/diario")
async def get_forecast_diario(
    days: int = Query(7, ge=1, le=16),
    escenario: Optional[str] = Query(None, pattern="^(demo|real)$"),
    current_user: User = Depends(get_current_user),
):
    """Pronóstico diario con radiación acumulada (Open-Meteo)."""
    try:
        return await openmeteo_service.get_forecast_diario(
            days=days,
            allow_synthetic=escenario != "real",
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/air-quality")
async def get_air_quality(
    escenario: Optional[str] = Query(None, pattern="^(demo|real)$"),
    current_user: User = Depends(get_current_user),
):
    """Calidad del aire (Open-Meteo). Crítico por polvo en La Guajira."""
    if escenario == "demo":
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        return {
            "disponible": True,
            "datos": [
                {
                    "fecha": now.isoformat(),
                    "pm10": 32.0,
                    "pm2_5": 14.0,
                    "polvo": 36.0,
                    "uv_index": 8.0,
                }
            ],
        }
    return await openmeteo_service.get_calidad_aire()


# ---------------------------------------------------------------------------
# COMPLEMENTO — OPENWEATHER
# ---------------------------------------------------------------------------
@router.get("/weather/current")
async def get_current_weather(
    escenario: Optional[str] = Query(None, pattern="^(demo|real)$"),
    current_user: User = Depends(get_current_user),
):
    """Clima actual (OpenWeather, capa de validación)."""
    try:
        return await openweather_service.get_current_weather(
            allow_synthetic=escenario != "real"
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/weather/forecast")
async def get_forecast_openweather(
    escenario: Optional[str] = Query(None, pattern="^(demo|real)$"),
    current_user: User = Depends(get_current_user),
):
    """Pronóstico 5 días/3h (OpenWeather, complemento)."""
    try:
        return await openweather_service.get_forecast(
            allow_synthetic=escenario != "real"
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/weather/air-pollution")
async def get_air_pollution_openweather(
    current_user: User = Depends(get_current_user),
):
    """Calidad del aire (OpenWeather)."""
    return await openweather_service.get_air_pollution()


@router.get("/weather/cross-check")
async def cross_check(
    escenario: Optional[str] = Query(None, pattern="^(demo|real)$"),
    current_user: User = Depends(get_current_user),
):
    """
    Compara clima actual entre Open-Meteo (núcleo) y OpenWeather (complemento)
    para validar consistencia entre fuentes.
    """
    allow_synthetic = escenario != "real"
    try:
        om_horario = await openmeteo_service.get_forecast_horario(
            days=1, allow_synthetic=allow_synthetic
        )
        ow_actual = await openweather_service.get_current_weather(
            allow_synthetic=allow_synthetic
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    om_actual = om_horario[0] if om_horario else None

    delta_temp = None
    if om_actual and om_actual.get("temperatura") is not None and ow_actual.get("temperatura") is not None:
        delta_temp = round(abs(om_actual["temperatura"] - ow_actual["temperatura"]), 2)

    return {
        "open_meteo": om_actual,
        "openweather": ow_actual,
        "delta_temperatura_c": delta_temp,
        "consistente": delta_temp is None or delta_temp <= 3.0,
    }


# ---------------------------------------------------------------------------
# OPCIONAL — PVGIS (BASELINE)
# ---------------------------------------------------------------------------
@router.get("/pvgis/tmy")
async def get_pvgis_tmy(
    current_user: User = Depends(get_current_user),
):
    """Año Meteorológico Típico de Riohacha (baseline PVGIS)."""
    return await pvgis_service.get_tmy()


@router.get("/pvgis/monthly")
async def get_pvgis_monthly(
    anio_inicio: int = Query(2010, ge=2005, le=2023),
    anio_fin: int = Query(2020, ge=2005, le=2023),
    current_user: User = Depends(get_current_user),
):
    """Promedios mensuales históricos PVGIS."""
    return await pvgis_service.get_radiacion_mensual(
        anio_inicio=anio_inicio, anio_fin=anio_fin
    )


@router.get("/pvgis/pvcalc")
async def get_pvgis_pvcalc(
    capacidad_kwp: float = Query(..., gt=0),
    inclinacion: int = Query(10, ge=0, le=60),
    azimut: int = Query(0, ge=-180, le=180),
    perdidas_pct: float = Query(14.0, ge=0, le=50),
    current_user: User = Depends(get_current_user),
):
    """Estimación de generación PV anual con PVGIS PVcalc."""
    return await pvgis_service.estimar_generacion_pv(
        capacidad_kwp=capacidad_kwp,
        inclinacion=inclinacion,
        azimut=azimut,
        perdidas_pct=perdidas_pct,
    )
