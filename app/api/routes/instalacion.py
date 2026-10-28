"""Instalación solar de la empresa (paneles, baterías, inversor) y su balance solar diario."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.db.session import get_db
from app.models.models import Empresa, User, UserRole
from app.schemas.schemas import InstalacionSolarCreate, InstalacionSolarResponse
from app.services.balance_solar import calcular_balance
from app.services.instalacion_solar import guardar_instalacion, obtener_instalacion

router = APIRouter(tags=["Instalación solar"])


def _empresa_con_acceso(db: Session, current_user: User, empresa_id: int, escribir: bool = False) -> Empresa:
    if current_user.role == UserRole.EMPRESA and current_user.empresa_id != empresa_id:
        raise HTTPException(status_code=403, detail="Sin permisos sobre esta empresa")
    if escribir and current_user.role == UserRole.ANALISTA:
        raise HTTPException(status_code=403, detail="El rol analista solo puede consultar")
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return empresa


@router.get("/empresas/{empresa_id}/instalacion", response_model=Optional[InstalacionSolarResponse])
def ver_instalacion(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ficha de la instalación solar con su banco de baterías (null si no tiene)."""
    _empresa_con_acceso(db, current_user, empresa_id)
    return obtener_instalacion(db, empresa_id)


@router.put("/empresas/{empresa_id}/instalacion", response_model=InstalacionSolarResponse)
def actualizar_instalacion(
    empresa_id: int,
    datos: InstalacionSolarCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crea o reemplaza la instalación (incluida la lista de baterías) y actualiza las capacidades."""
    empresa = _empresa_con_acceso(db, current_user, empresa_id, escribir=True)
    return guardar_instalacion(db, empresa, datos)


@router.get("/empresas/{empresa_id}/balance-solar")
async def balance_solar(
    empresa_id: int,
    days: int = Query(30, ge=1, le=180),
    pronostico: int = Query(3, ge=0, le=7),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Producción, consumo, batería, excedentes y red por día (radiación real de Open-Meteo/NASA POWER)."""
    empresa = _empresa_con_acceso(db, current_user, empresa_id)
    return await calcular_balance(db, empresa, days=days, pronostico=pronostico)
