from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List

from app.db.session import get_db
from app.models.models import Empresa, User, UserRole, Recomendacion
from app.schemas.schemas import RecomendacionResponse
from app.api.deps.auth import get_current_user
from app.services.agents.agente_solar import agente_solar
from app.services.agents.agente_consumo import agente_consumo
from app.services.agents.agente_recomendaciones import agente_recomendaciones
from app.services.ollama_client import ollama_client

router = APIRouter(prefix="/ia", tags=["Motor IA"])


def _check_acceso(current_user: User, empresa_id: int):
    if (
        current_user.role == UserRole.EMPRESA
        and current_user.empresa_id != empresa_id
    ):
        raise HTTPException(status_code=403, detail="Sin permisos")


@router.get("/status")
async def get_ia_status():
    """Verifica si Ollama (LLM local) está disponible."""
    disponible = await ollama_client.is_disponible()
    return {
        "ollama_disponible": disponible,
        "modelo": ollama_client.model,
        "base_url": ollama_client.base_url,
        "modo": "LLM" if disponible else "Reglas (fallback)",
    }


@router.get("/analisis/solar/{empresa_id}")
def analisis_solar(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Análisis solar para la empresa."""
    _check_acceso(current_user, empresa_id)
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return agente_solar.analizar(db, empresa)


@router.get("/analisis/consumo/{empresa_id}")
def analisis_consumo(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Análisis de consumo y detección de anomalías."""
    _check_acceso(current_user, empresa_id)
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return agente_consumo.analizar(db, empresa)


@router.post("/recomendaciones/{empresa_id}", response_model=List[RecomendacionResponse])
async def generar_recomendaciones(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera nuevas recomendaciones IA para la empresa."""
    _check_acceso(current_user, empresa_id)
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    solar = agente_solar.analizar(db, empresa)
    consumo = agente_consumo.analizar(db, empresa)
    recomendaciones = await agente_recomendaciones.generar(db, empresa, solar, consumo)
    return recomendaciones


@router.get("/recomendaciones/{empresa_id}", response_model=List[RecomendacionResponse])
def list_recomendaciones(
    empresa_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listar recomendaciones guardadas para la empresa."""
    _check_acceso(current_user, empresa_id)
    return (
        db.query(Recomendacion)
        .filter(Recomendacion.empresa_id == empresa_id)
        .order_by(desc(Recomendacion.created_at))
        .limit(limit)
        .all()
    )


@router.patch("/recomendaciones/{rec_id}/aplicar", response_model=RecomendacionResponse)
def marcar_aplicada(
    rec_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Marcar recomendación como aplicada."""
    rec = db.query(Recomendacion).filter(Recomendacion.id == rec_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recomendación no encontrada")
    _check_acceso(current_user, rec.empresa_id)
    rec.aplicada = True
    db.commit()
    db.refresh(rec)
    return rec
