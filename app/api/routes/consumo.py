import calendar
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from datetime import datetime, timedelta

from app.db.session import get_db
from app.models.models import ConsumoEnergetico, Empresa, User, UserRole, Alerta
from app.schemas.schemas import ConsumoCreate, ConsumoMensualCreate, ConsumoResponse, DashboardKPIs
from app.api.deps.auth import get_current_user
from app.services.consumo_parser import parser
from app.services.demo_data import get_consumo_demo, get_demo_empresa, get_radiacion_demo

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
    escenario: Optional[str] = Query(None, pattern="^(demo|real)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Registrar un consumo manualmente."""
    if escenario == "demo":
        raise HTTPException(status_code=409, detail="Modo demo es solo lectura (JSON)")
    _check_acceso_empresa(current_user, data.empresa_id)
    payload = data.model_dump()
    empresa = db.query(Empresa).filter(Empresa.id == data.empresa_id).first()
    rec = ConsumoEnergetico(
        **payload,
        escenario=escenario or (empresa.escenario_default if empresa else "demo"),
        origen_dato="real_upload",
        confiabilidad=95.0,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


@router.post("/monthly", status_code=status.HTTP_201_CREATED)
def create_consumo_mensual(
    data: ConsumoMensualCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Registrar una factura mensual y distribuirla en consumos diarios."""
    _check_acceso_empresa(current_user, data.empresa_id)
    empresa = db.query(Empresa).filter(Empresa.id == data.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    if data.mes < 1 or data.mes > 12:
        raise HTTPException(status_code=400, detail="El mes debe estar entre 1 y 12")

    # Obtener el número de días del mes
    _, num_dias = calendar.monthrange(data.anio, data.mes)

    consumo_diario = data.consumo_total_kwh / num_dias
    costo_diario = data.costo_energia_cop / num_dias

    # Eliminar registros previos reales de este mismo mes para evitar duplicidad
    inicio_mes = datetime(data.anio, data.mes, 1, 0, 0, 0)
    fin_mes = datetime(data.anio, data.mes, num_dias, 23, 59, 59)
    db.query(ConsumoEnergetico).filter(
        ConsumoEnergetico.empresa_id == data.empresa_id,
        ConsumoEnergetico.fecha >= inicio_mes,
        ConsumoEnergetico.fecha <= fin_mes,
        ConsumoEnergetico.escenario == "real",
    ).delete(synchronize_session=False)

    # Insertar un registro diario por cada día del mes
    insertados = 0
    for dia in range(1, num_dias + 1):
        fecha_registro = datetime(data.anio, data.mes, dia, 12, 0, 0)
        rec = ConsumoEnergetico(
            empresa_id=data.empresa_id,
            fecha=fecha_registro,
            consumo_kwh=consumo_diario,
            costo_cop=costo_diario,
            demanda_pico_kw=None,
            produccion_solar_kwh=0.0,
            nivel_bateria_pct=None,
            periodo="diario",
            escenario="real",
            origen_dato="real_monthly_bill",
            confiabilidad=90.0,
        )
        db.add(rec)
        insertados += 1

    alerta_creada = False
    if data.fecha_pago_oportuno is not None:
        # Calcular severidad basada en días restantes
        dias_restantes = (data.fecha_pago_oportuno.date() - datetime.now().date()).days
        if dias_restantes < 0:
            severidad = "media"  # Ya pasó, pero de todos modos se reporta
        elif dias_restantes <= 2:
            severidad = "critica"
        elif dias_restantes <= 5:
            severidad = "alta"
        else:
            severidad = "media"

        fecha_pago_str = data.fecha_pago_oportuno.strftime("%d/%m/%Y")
        fecha_susp_str = data.fecha_suspension.strftime("%d/%m/%Y") if data.fecha_suspension else "pronto"
        
        mensaje_alerta = (
            f"📌 Recordatorio de Pago: Tu recibo de energía de {data.mes}/{data.anio} tiene como fecha oportuna de "
            f"pago el {fecha_pago_str}. Evita la suspensión del servicio programada a partir del {fecha_susp_str}."
        )

        # Eliminar recordatorios previos para el mismo mes
        db.query(Alerta).filter(
            Alerta.empresa_id == data.empresa_id,
            Alerta.tipo == "recordatorio_pago",
            Alerta.mensaje.like(f"%{data.mes}/{data.anio}%")
        ).delete(synchronize_session=False)

        # Crear nueva alerta
        alerta_rec = Alerta(
            empresa_id=data.empresa_id,
            tipo="recordatorio_pago",
            mensaje=mensaje_alerta,
            severidad=severidad,
            leida=False,
        )
        db.add(alerta_rec)
        alerta_creada = True

    db.commit()

    return {
        "mensaje": f"Factura mensual de {data.mes}/{data.anio} procesada e interpolada exitosamente.",
        "registros_insertados": insertados,
        "consumo_diario_kwh": round(consumo_diario, 2),
        "costo_diario_cop": round(costo_diario, 2),
        "alerta_creada": alerta_creada,
    }


@router.get("/empresa/{empresa_id}", response_model=List[ConsumoResponse])
def list_consumo_empresa(
    empresa_id: int,
    days: int = Query(30, ge=1, le=730),
    escenario: Optional[str] = Query(None, pattern="^(demo|real)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listar consumo de una empresa (últimos N días)."""
    if escenario == "demo":
        if empresa_id != get_demo_empresa()["id"]:
            return []
        rows = get_consumo_demo(days=days)
        for i, r in enumerate(rows):
            r.setdefault("id", 100000 + i)
            r.setdefault("empresa_id", empresa_id)
            r.setdefault("created_at", r.get("fecha"))
        return rows
    _check_acceso_empresa(current_user, empresa_id)
    since = datetime.now() - timedelta(days=days)
    q = (
        db.query(ConsumoEnergetico)
        .filter(
            ConsumoEnergetico.empresa_id == empresa_id,
            ConsumoEnergetico.fecha >= since,
        )
    )
    if escenario:
        q = q.filter(ConsumoEnergetico.escenario == escenario)
    return q.order_by(desc(ConsumoEnergetico.fecha)).all()


@router.post("/upload/{empresa_id}")
async def upload_consumo_file(
    empresa_id: int,
    escenario: Optional[str] = Query(None, pattern="^(demo|real)$"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Subir archivo CSV o XLSX con datos de consumo.
    Columnas requeridas: fecha, consumo_kwh
    Columnas opcionales: costo_cop, demanda_pico_kw, produccion_solar_kwh, nivel_bateria_pct, periodo
    """
    if escenario == "demo":
        raise HTTPException(status_code=409, detail="Modo demo es solo lectura (JSON)")
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
        rec.escenario = escenario or empresa.escenario_default or "demo"
        rec.origen_dato = "real_upload"
        rec.confiabilidad = 95.0
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
    escenario: Optional[str] = Query(None, pattern="^(demo|real)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """KPIs principales del dashboard para una empresa."""
    if escenario == "demo":
        demo = get_demo_empresa()
        if empresa_id != demo["id"]:
            raise HTTPException(status_code=404, detail="Empresa demo no encontrada")
        consumos = get_consumo_demo(days=30)
        if not consumos:
            return DashboardKPIs()
        hoy = datetime.now().date()
        consumo_hoy = sum((r.get("consumo_kwh") or 0) for r in consumos if datetime.fromisoformat(r["fecha"]).date() == hoy)
        consumo_mes = sum((r.get("consumo_kwh") or 0) for r in consumos if datetime.fromisoformat(r["fecha"]).month == hoy.month)
        prod_hoy = sum((r.get("produccion_solar_kwh") or 0) for r in consumos if datetime.fromisoformat(r["fecha"]).date() == hoy)
        ultimo = consumos[0]
        rad = get_radiacion_demo(days=7)
        rad_actual = rad[0].get("ghi") if rad else None
        return DashboardKPIs(
            radiacion_actual_kwh=rad_actual,
            consumo_hoy_kwh=consumo_hoy,
            costo_hoy_cop=consumo_hoy * demo["tarifa_kwh"],
            produccion_solar_hoy_kwh=prod_hoy,
            ahorro_estimado_cop=prod_hoy * demo["tarifa_kwh"],
            nivel_bateria_pct=ultimo.get("nivel_bateria_pct"),
            consumo_mes_kwh=consumo_mes,
            costo_mes_cop=consumo_mes * demo["tarifa_kwh"],
        )
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
            True if not escenario else ConsumoEnergetico.escenario == escenario,
        )
        .scalar() or 0.0
    )

    consumo_mes = (
        db.query(func.sum(ConsumoEnergetico.consumo_kwh))
        .filter(
            ConsumoEnergetico.empresa_id == empresa_id,
            ConsumoEnergetico.fecha >= mes_inicio,
            True if not escenario else ConsumoEnergetico.escenario == escenario,
        )
        .scalar() or 0.0
    )

    produccion_hoy = (
        db.query(func.sum(ConsumoEnergetico.produccion_solar_kwh))
        .filter(
            ConsumoEnergetico.empresa_id == empresa_id,
            ConsumoEnergetico.fecha >= hoy_inicio,
            True if not escenario else ConsumoEnergetico.escenario == escenario,
        )
        .scalar() or 0.0
    )

    q_ultimo = db.query(ConsumoEnergetico).filter(ConsumoEnergetico.empresa_id == empresa_id)
    if escenario:
        q_ultimo = q_ultimo.filter(ConsumoEnergetico.escenario == escenario)
    ultimo_consumo = q_ultimo.order_by(desc(ConsumoEnergetico.fecha)).first()

    # Radiación actual del último registro
    from app.models.models import RadiacionSolar
    q_rad = db.query(RadiacionSolar)
    if escenario:
        q_rad = q_rad.filter(RadiacionSolar.escenario == escenario)
    rad_actual = q_rad.order_by(desc(RadiacionSolar.fecha)).first()

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
    escenario: Optional[str] = Query(None, pattern="^(demo|real)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Eliminar registro de consumo."""
    if escenario == "demo":
        raise HTTPException(status_code=409, detail="Modo demo es solo lectura (JSON)")
    rec = db.query(ConsumoEnergetico).filter(ConsumoEnergetico.id == consumo_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    _check_acceso_empresa(current_user, rec.empresa_id)
    db.delete(rec)
    db.commit()
