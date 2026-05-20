from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from datetime import datetime, timedelta

from app.db.session import get_db
from app.models.models import ConsumoEnergetico, Empresa, User, UserRole
from app.schemas.schemas import ConsumoCreate, ConsumoResponse, DashboardKPIs
from app.api.deps.auth import get_current_user
from app.services.consumo_parser import parser

router = APIRouter(prefix="/consumo", tags=["Consumo Energético"])


def _check_acceso_empresa(current_user: User, empresa_id: int):
    if (
        current_user.role == UserRole.EMPRESA
        and current_user.empresa_id != empresa_id
    ):
        raise HTTPException(status_code=403, detail="Sin permisos sobre esta empresa")


@router.post("/", response_model=ConsumoResponse, status_code=status.HTTP_201_CREATED)
def create_consumo(
    data: ConsumoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Registrar un consumo manualmente."""
    _check_acceso_empresa(current_user, data.empresa_id)
    rec = ConsumoEnergetico(**data.model_dump())
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


@router.get("/empresa/{empresa_id}", response_model=List[ConsumoResponse])
def list_consumo_empresa(
    empresa_id: int,
    days: int = Query(30, ge=1, le=730),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listar consumo de una empresa (últimos N días)."""
    _check_acceso_empresa(current_user, empresa_id)
    since = datetime.now() - timedelta(days=days)
    return (
        db.query(ConsumoEnergetico)
        .filter(
            ConsumoEnergetico.empresa_id == empresa_id,
            ConsumoEnergetico.fecha >= since,
        )
        .order_by(desc(ConsumoEnergetico.fecha))
        .all()
    )


@router.post("/upload/{empresa_id}")
async def upload_consumo_file(
    empresa_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Subir archivo CSV o XLSX con datos de consumo.
    Columnas requeridas: fecha, consumo_kwh
    Columnas opcionales: costo_cop, demanda_pico_kw, produccion_solar_kwh, nivel_bateria_pct, periodo
    """
    _check_acceso_empresa(current_user, empresa_id)
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    contenido = await file.read()
    registros, errores = parser.parse_file(contenido, file.filename or "")

    if not registros:
        raise HTTPException(
            status_code=400,
            detail={
                "mensaje": "No se pudo procesar el archivo",
                "errores": errores,
            },
        )

    # Insertar en BD
    insertados = 0
    for r in registros:
        # Calcular costo si no viene
        if "costo_cop" not in r:
            r["costo_cop"] = r["consumo_kwh"] * empresa.tarifa_kwh

        rec = ConsumoEnergetico(empresa_id=empresa_id, **r)
        db.add(rec)
        insertados += 1
    db.commit()

    return {
        "mensaje": f"Archivo procesado correctamente",
        "registros_insertados": insertados,
        "errores": errores,
        "total_filas": insertados + len(errores),
    }


@router.get("/kpis/{empresa_id}", response_model=DashboardKPIs)
def get_dashboard_kpis(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """KPIs principales del dashboard para una empresa."""
    _check_acceso_empresa(current_user, empresa_id)
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    hoy_inicio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    mes_inicio = hoy_inicio.replace(day=1)

    consumo_hoy = (
        db.query(func.sum(ConsumoEnergetico.consumo_kwh))
        .filter(
            ConsumoEnergetico.empresa_id == empresa_id,
            ConsumoEnergetico.fecha >= hoy_inicio,
        )
        .scalar() or 0.0
    )

    consumo_mes = (
        db.query(func.sum(ConsumoEnergetico.consumo_kwh))
        .filter(
            ConsumoEnergetico.empresa_id == empresa_id,
            ConsumoEnergetico.fecha >= mes_inicio,
        )
        .scalar() or 0.0
    )

    produccion_hoy = (
        db.query(func.sum(ConsumoEnergetico.produccion_solar_kwh))
        .filter(
            ConsumoEnergetico.empresa_id == empresa_id,
            ConsumoEnergetico.fecha >= hoy_inicio,
        )
        .scalar() or 0.0
    )

    ultimo_consumo = (
        db.query(ConsumoEnergetico)
        .filter(ConsumoEnergetico.empresa_id == empresa_id)
        .order_by(desc(ConsumoEnergetico.fecha))
        .first()
    )

    # Radiación actual del último registro
    from app.models.models import RadiacionSolar
    rad_actual = (
        db.query(RadiacionSolar)
        .order_by(desc(RadiacionSolar.fecha))
        .first()
    )

    return DashboardKPIs(
        radiacion_actual_kwh=rad_actual.ghi if rad_actual else None,
        consumo_hoy_kwh=consumo_hoy,
        costo_hoy_cop=consumo_hoy * empresa.tarifa_kwh,
        produccion_solar_hoy_kwh=produccion_hoy,
        ahorro_estimado_cop=produccion_hoy * empresa.tarifa_kwh,
        nivel_bateria_pct=ultimo_consumo.nivel_bateria_pct if ultimo_consumo else None,
        consumo_mes_kwh=consumo_mes,
        costo_mes_cop=consumo_mes * empresa.tarifa_kwh,
    )


@router.delete("/{consumo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_consumo(
    consumo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Eliminar registro de consumo."""
    rec = db.query(ConsumoEnergetico).filter(ConsumoEnergetico.id == consumo_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    _check_acceso_empresa(current_user, rec.empresa_id)
    db.delete(rec)
    db.commit()
