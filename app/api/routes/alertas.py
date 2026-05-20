from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional

from app.db.session import get_db
from app.models.models import Alerta, ConfiguracionAlerta, Empresa, User, UserRole
from app.schemas.schemas import (
    AlertaResponse,
    AlertaUpdate,
    ConfigAlertaUpdate,
)
from app.api.deps.auth import get_current_user
from app.services.agents.agente_alertas import agente_alertas

router = APIRouter(prefix="/alertas", tags=["Alertas"])


def _check_acceso(current_user: User, empresa_id: int):
    if (
        current_user.role == UserRole.EMPRESA
        and current_user.empresa_id != empresa_id
    ):
        raise HTTPException(status_code=403, detail="Sin permisos")


@router.get("/{empresa_id}", response_model=List[AlertaResponse])
def list_alertas(
    empresa_id: int,
    solo_no_leidas: bool = False,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listar alertas de la empresa."""
    _check_acceso(current_user, empresa_id)
    q = db.query(Alerta).filter(Alerta.empresa_id == empresa_id)
    if solo_no_leidas:
        q = q.filter(Alerta.leida == False)
    return q.order_by(desc(Alerta.created_at)).limit(limit).all()


@router.post("/evaluar/{empresa_id}", response_model=List[AlertaResponse])
def evaluar_alertas(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Forzar evaluación de alertas para la empresa (genera nuevas si corresponde)."""
    _check_acceso(current_user, empresa_id)
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    creadas = agente_alertas.evaluar(db, empresa)
    return [c for c in creadas if c is not None]


@router.patch("/{alerta_id}/marcar-leida", response_model=AlertaResponse)
def marcar_leida(
    alerta_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Marcar alerta como leída."""
    alerta = db.query(Alerta).filter(Alerta.id == alerta_id).first()
    if not alerta:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    _check_acceso(current_user, alerta.empresa_id)
    alerta.leida = True
    db.commit()
    db.refresh(alerta)
    return alerta


@router.get("/config/{empresa_id}")
def get_configuracion(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener configuración de alertas de la empresa."""
    _check_acceso(current_user, empresa_id)
    config = (
        db.query(ConfiguracionAlerta)
        .filter(ConfiguracionAlerta.empresa_id == empresa_id)
        .first()
    )
    if not config:
        config = ConfiguracionAlerta(empresa_id=empresa_id)
        db.add(config)
        db.commit()
        db.refresh(config)
    return {
        "id": config.id,
        "empresa_id": config.empresa_id,
        "umbral_consumo_diario_kwh": config.umbral_consumo_diario_kwh,
        "umbral_bateria_baja_pct": config.umbral_bateria_baja_pct,
        "umbral_radiacion_baja": config.umbral_radiacion_baja,
        "notificar_email": config.notificar_email,
        "notificar_dashboard": config.notificar_dashboard,
    }


@router.patch("/config/{empresa_id}")
def update_configuracion(
    empresa_id: int,
    data: ConfigAlertaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualizar configuración de alertas."""
    _check_acceso(current_user, empresa_id)
    config = (
        db.query(ConfiguracionAlerta)
        .filter(ConfiguracionAlerta.empresa_id == empresa_id)
        .first()
    )
    if not config:
        config = ConfiguracionAlerta(empresa_id=empresa_id)
        db.add(config)

    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(config, k, v)
    db.commit()
    db.refresh(config)
    return {
        "empresa_id": config.empresa_id,
        "umbral_consumo_diario_kwh": config.umbral_consumo_diario_kwh,
        "umbral_bateria_baja_pct": config.umbral_bateria_baja_pct,
        "umbral_radiacion_baja": config.umbral_radiacion_baja,
        "notificar_email": config.notificar_email,
        "notificar_dashboard": config.notificar_dashboard,
    }
