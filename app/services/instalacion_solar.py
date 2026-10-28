"""
Instalación solar de un hogar o empresa: paneles, banco de baterías, inversor y perfil de consumo.

Se registra en "Tengo paneles solares" (registro) y se edita en "Mi sistema solar". Al guardarla se
actualizan capacidad_paneles_kw y capacidad_bateria_kwh de la empresa, que usan los demás cálculos.
"""
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.models.models import BateriaInstalacion, Empresa, InstalacionSolar


def migrar_bateria_unica(inst: InstalacionSolar) -> bool:
    """Las instalaciones guardadas antes de la lista de baterías tienen una sola, en las columnas de la ficha."""
    if inst.baterias or not inst.tiene_bateria or not inst.voltaje_banco_v or not inst.capacidad_ah:
        return False
    inst.baterias.append(
        BateriaInstalacion(
            orden=1,
            quimica=inst.quimica_bateria,
            voltaje_v=inst.voltaje_banco_v,
            capacidad_ah=inst.capacidad_ah,
            cantidad=1,
        )
    )
    return True


def aplicar_baterias(inst: InstalacionSolar, baterias: Iterable) -> None:
    """Reemplaza el banco de baterías. Sin lista, usa la batería de voltaje_banco_v y capacidad_ah."""
    nuevas = [
        BateriaInstalacion(
            orden=i,
            quimica=b.quimica,
            voltaje_v=b.voltaje_v,
            capacidad_ah=b.capacidad_ah,
            cantidad=b.cantidad,
        )
        for i, b in enumerate(baterias or [], start=1)
    ]
    inst.baterias = nuevas
    if not inst.tiene_bateria:
        inst.baterias = []
        return
    if nuevas:
        primera = nuevas[0]
        inst.quimica_bateria = primera.quimica
        inst.voltaje_banco_v = primera.voltaje_v
        inst.capacidad_ah = primera.capacidad_ah
    else:
        migrar_bateria_unica(inst)


def actualizar_capacidades(empresa: Empresa, inst: InstalacionSolar) -> None:
    empresa.capacidad_paneles_kw = inst.potencia_pico_kw
    empresa.capacidad_bateria_kwh = inst.bateria_kwh


def obtener_instalacion(db: Session, empresa_id: int) -> Optional[InstalacionSolar]:
    inst = db.query(InstalacionSolar).filter(InstalacionSolar.empresa_id == empresa_id).first()
    if inst is not None and migrar_bateria_unica(inst):
        db.commit()
        db.refresh(inst)
    return inst


def guardar_instalacion(db: Session, empresa: Empresa, datos) -> InstalacionSolar:
    """Crea o reemplaza la ficha de la instalación con sus baterías (datos: InstalacionSolarCreate)."""
    inst = db.query(InstalacionSolar).filter(InstalacionSolar.empresa_id == empresa.id).first()
    if inst is None:
        inst = InstalacionSolar(empresa_id=empresa.id)
        db.add(inst)
    for campo, valor in datos.model_dump(exclude={"baterias"}).items():
        setattr(inst, campo, valor)
    aplicar_baterias(inst, datos.baterias)
    actualizar_capacidades(empresa, inst)
    db.commit()
    db.refresh(inst)
    return inst
