"""
Agente de Alertas.
Monitorea umbrales y dispara notificaciones automáticas.
"""
from typing import List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.models.models import (
    Alerta,
    ConfiguracionAlerta,
    ConsumoEnergetico,
    RadiacionSolar,
    Empresa,
)


class AgenteAlertas:
    """Monitorea y crea alertas según umbrales configurados."""

    def evaluar(self, db: Session, empresa: Empresa) -> List[Alerta]:
        """Evalúa condiciones y crea alertas si corresponde."""
        escenario = empresa.escenario_default or "demo"
        config = (
            db.query(ConfiguracionAlerta)
            .filter(ConfiguracionAlerta.empresa_id == empresa.id)
            .first()
        )
        if not config:
            # Crear config por defecto
            config = ConfiguracionAlerta(empresa_id=empresa.id)
            db.add(config)
            db.commit()
            db.refresh(config)

        alertas_creadas = []
        hoy_inicio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # 1. Consumo diario alto
        consumo_hoy = (
            db.query(func.sum(ConsumoEnergetico.consumo_kwh))
            .filter(
                ConsumoEnergetico.empresa_id == empresa.id,
                ConsumoEnergetico.fecha >= hoy_inicio,
                ConsumoEnergetico.escenario == escenario,
            )
            .scalar() or 0.0
        )
        if consumo_hoy > config.umbral_consumo_diario_kwh:
            a = self._crear_si_no_existe_hoy(
                db,
                empresa.id,
                tipo="consumo_alto",
                mensaje=(
                    f"Consumo diario {consumo_hoy:.1f} kWh supera el umbral "
                    f"({config.umbral_consumo_diario_kwh:.1f} kWh). "
                    "Considere reducir cargas no esenciales."
                ),
                severidad="alta",
            )
            if a:
                alertas_creadas.append(a)

        # 2. Batería baja
        ultimo_consumo = (
            db.query(ConsumoEnergetico)
            .filter(
                ConsumoEnergetico.empresa_id == empresa.id,
                ConsumoEnergetico.escenario == escenario,
            )
            .order_by(desc(ConsumoEnergetico.fecha))
            .first()
        )
        if (
            ultimo_consumo
            and ultimo_consumo.nivel_bateria_pct is not None
            and ultimo_consumo.nivel_bateria_pct < config.umbral_bateria_baja_pct
        ):
            a = self._crear_si_no_existe_hoy(
                db,
                empresa.id,
                tipo="bateria_baja",
                mensaje=(
                    f"Nivel de batería al {ultimo_consumo.nivel_bateria_pct:.1f}% "
                    f"(umbral: {config.umbral_bateria_baja_pct:.0f}%). "
                    "Reduzca cargas y verifique sistema de carga solar."
                ),
                severidad="alta" if ultimo_consumo.nivel_bateria_pct < 15 else "media",
            )
            if a:
                alertas_creadas.append(a)

        # 3. Radiación baja
        rad_reciente = (
            db.query(RadiacionSolar)
            .filter(RadiacionSolar.escenario == escenario)
            .order_by(desc(RadiacionSolar.fecha))
            .first()
        )
        if (
            rad_reciente
            and rad_reciente.ghi is not None
            and rad_reciente.ghi < config.umbral_radiacion_baja
        ):
            a = self._crear_si_no_existe_hoy(
                db,
                empresa.id,
                tipo="baja_radiacion",
                mensaje=(
                    f"Radiación solar baja ({rad_reciente.ghi:.2f} kWh/m²/día). "
                    "Precargue baterías y reduzca dependencia solar las próximas horas."
                ),
                severidad="media",
            )
            if a:
                alertas_creadas.append(a)

        # 4. Pico de demanda
        if ultimo_consumo and ultimo_consumo.demanda_pico_kw:
            # Promedio histórico de demanda pico
            promedio_pico = (
                db.query(func.avg(ConsumoEnergetico.demanda_pico_kw))
                .filter(
                    ConsumoEnergetico.empresa_id == empresa.id,
                    ConsumoEnergetico.demanda_pico_kw.isnot(None),
                    ConsumoEnergetico.escenario == escenario,
                )
                .scalar() or 0
            )
            if (
                promedio_pico > 0
                and ultimo_consumo.demanda_pico_kw > promedio_pico * 1.5
            ):
                a = self._crear_si_no_existe_hoy(
                    db,
                    empresa.id,
                    tipo="pico_demanda",
                    mensaje=(
                        f"Pico de demanda detectado: {ultimo_consumo.demanda_pico_kw:.1f} kW "
                        f"({((ultimo_consumo.demanda_pico_kw / promedio_pico - 1) * 100):.0f}% sobre promedio). "
                        "Redistribuya cargas."
                    ),
                    severidad="alta",
                )
                if a:
                    alertas_creadas.append(a)

        return alertas_creadas

    def _crear_si_no_existe_hoy(
        self,
        db: Session,
        empresa_id: int,
        tipo: str,
        mensaje: str,
        severidad: str,
    ) -> Alerta:
        """Evita alertas duplicadas del mismo tipo en el mismo día."""
        hoy_inicio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        existente = (
            db.query(Alerta)
            .filter(
                Alerta.empresa_id == empresa_id,
                Alerta.tipo == tipo,
                Alerta.created_at >= hoy_inicio,
            )
            .first()
        )
        if existente:
            return None

        alerta = Alerta(
            empresa_id=empresa_id,
            tipo=tipo,
            mensaje=mensaje,
            severidad=severidad,
        )
        db.add(alerta)
        db.commit()
        db.refresh(alerta)
        return alerta


agente_alertas = AgenteAlertas()
