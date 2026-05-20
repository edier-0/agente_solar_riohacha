from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, timedelta

from app.db.session import get_db
from app.models.models import Prediccion, Empresa, User, UserRole
from app.schemas.schemas import PrediccionResponse
from app.api.deps.auth import get_current_user
from app.services.agents.agente_prediccion import agente_prediccion

router = APIRouter(prefix="/predicciones", tags=["Predicciones"])


def _check_acceso(current_user: User, empresa_id: int):
    if (
        current_user.role == UserRole.EMPRESA
        and current_user.empresa_id != empresa_id
    ):
        raise HTTPException(status_code=403, detail="Sin permisos")


@router.post("/generar/{empresa_id}")
async def generar_predicciones(
    empresa_id: int,
    horas_horizonte: int = Query(72, ge=24, le=168),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera predicciones a 24-168h para la empresa."""
    _check_acceso(current_user, empresa_id)
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    resultado = await agente_prediccion.predecir(db, empresa, horas_horizonte)
    return resultado


@router.get("/{empresa_id}", response_model=List[PrediccionResponse])
def list_predicciones(
    empresa_id: int,
    tipo: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista predicciones recientes para la empresa."""
    _check_acceso(current_user, empresa_id)
    desde = datetime.now() - timedelta(hours=12)
    q = db.query(Prediccion).filter(
        Prediccion.empresa_id == empresa_id,
        Prediccion.fecha_prediccion >= desde,
        Prediccion.fecha_objetivo >= datetime.now(),
    )
    if tipo:
        q = q.filter(Prediccion.tipo == tipo)
    return q.order_by(Prediccion.fecha_objetivo).all()
