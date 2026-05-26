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
    """Monitorea y crea alertas de manera dinámica y proactiva según el perfil y APIs externas."""

    async def evaluar(self, db: Session, empresa: Empresa) -> List[Alerta]:
        """Evalúa condiciones climáticas y telemetría histórica de forma proactiva y personalizada."""
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

        # Identificar qué equipamiento real tiene el usuario para evitar alucinaciones.
        # Buscamos en el perfil (capacidad > 0) OR si existe telemetría inyectada con valores válidos.
        tiene_telemetria_bateria = db.query(ConsumoEnergetico).filter(
            ConsumoEnergetico.empresa_id == empresa.id,
            ConsumoEnergetico.nivel_bateria_pct.isnot(None),
            ConsumoEnergetico.escenario == escenario
        ).first() is not None

        tiene_telemetria_solar = db.query(ConsumoEnergetico).filter(
            ConsumoEnergetico.empresa_id == empresa.id,
            ConsumoEnergetico.produccion_solar_kwh > 0.0,
            ConsumoEnergetico.escenario == escenario
        ).first() is not None

        tiene_paneles = ((empresa.capacidad_paneles_kw or 0.0) > 0.0) or tiene_telemetria_solar
        tiene_baterias = ((empresa.capacidad_bateria_kwh or 0.0) > 0.0) or tiene_telemetria_bateria

        alertas_creadas = []
        hoy_inicio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Limpiar alertas no leídas creadas hoy para esta empresa, para poder regenerarlas con el contexto y reglas frescas
        db.query(Alerta).filter(
            Alerta.empresa_id == empresa.id,
            Alerta.leida == False,
            Alerta.created_at >= hoy_inicio
        ).delete()
        db.commit()

        # Importar el agente de consumo para el cálculo de desviación estándar histórica
        from app.services.agents.agente_consumo import agente_consumo

        # 1. Consumo diario alto (DINÁMICO)
        # Solo se evalúa si hay un promedio histórico registrado > 0 para evitar falsos positivos
        analisis_consumo = agente_consumo.analizar(db, empresa, days=30)
        promedio_diario = analisis_consumo.get("promedio_diario_kwh", 0.0)
        std_diario = analisis_consumo.get("std_kwh", 0.0)

        if promedio_diario > 0.0:
            consumo_hoy = (
                db.query(func.sum(ConsumoEnergetico.consumo_kwh))
                .filter(
                    ConsumoEnergetico.empresa_id == empresa.id,
                    ConsumoEnergetico.fecha >= hoy_inicio,
                    ConsumoEnergetico.escenario == escenario,
                )
                .scalar() or 0.0
            )

            # Si el umbral de consumo diario es el valor por defecto (500.0), calculamos dinámicamente.
            if config.umbral_consumo_diario_kwh == 500.0:
                umbral_consumo = max(promedio_diario + 2 * std_diario, 50.0)  # Piso de seguridad de 50 kWh
                motivo_umbral = f"calculado dinámicamente basado en tu promedio histórico ({promedio_diario:.1f} kWh) más varianza (+2σ)"
            else:
                umbral_consumo = config.umbral_consumo_diario_kwh
                motivo_umbral = f"anulación manual en configuración avanzada"

            if consumo_hoy > umbral_consumo:
                a = self._crear_si_no_existe_hoy(
                    db,
                    empresa.id,
                    tipo="consumo_alto",
                    mensaje=(
                        f"Consumo diario acumulado de {consumo_hoy:.1f} kWh ha superado el umbral inteligente de {umbral_consumo:.1f} kWh "
                        f"({motivo_umbral}). Se sugiere desconectar cargas no críticas."
                    ),
                    severidad="alta",
                )
                if a:
                    alertas_creadas.append(a)

        # 2. Resiliencia de Batería Baja / Riesgo de Apagón Predictivo (DINÁMICO - Solo si tiene Baterías)
        if tiene_baterias:
            umbral_bateria = config.umbral_bateria_baja_pct
            motivo_bateria = "límite mínimo estándar"

            # Si el valor de batería es el por defecto (20%), elevamos el umbral dinámicamente si el pronóstico meteorológico es adverso
            if config.umbral_bateria_baja_pct == 20.0:
                try:
                    from app.services.openmeteo import openmeteo_service
                    forecast = await openmeteo_service.get_forecast_diario(days=3, allow_synthetic=True)
                    if forecast and len(forecast) > 1:
                        mañana = forecast[1]
                        ghi_mañana = mañana.get("ghi")
                        lluvia_mañana = mañana.get("precipitacion_mm", 0.0) or 0.0
                        
                        # Si mañana habrá baja radiación solar (< 3.0 kWh/m²/día) o lluvia intensa (> 10mm)
                        if (ghi_mañana is not None and ghi_mañana < 3.0) or (lluvia_mañana > 10.0):
                            umbral_bateria = 40.0
                            motivo_bateria = (
                                f"elevado preventivamente a {umbral_bateria:.0f}% debido a pronóstico de baja radiación "
                                f"({ghi_mañana:.1f} kWh/m²/día) o lluvias en Riohacha para mañana"
                            )
                except Exception:
                    pass

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
                and ultimo_consumo.nivel_bateria_pct < umbral_bateria
            ):
                a = self._crear_si_no_existe_hoy(
                    db,
                    empresa.id,
                    tipo="bateria_baja",
                    mensaje=(
                        f"El banco de almacenamiento solar está al {ultimo_consumo.nivel_bateria_pct:.1f}% "
                        f"({motivo_bateria}). Reduzca cargas no críticas para preservar reserva eléctrica."
                    ),
                    severidad="alta" if ultimo_consumo.nivel_bateria_pct < 15 else "media",
                )
                if a:
                    alertas_creadas.append(a)

        # 3. Radiación Baja (DINÁMICO - Solo si tiene Paneles Solares)
        if tiene_paneles:
            rad_reciente = (
                db.query(RadiacionSolar)
                .filter(RadiacionSolar.escenario == escenario)
                .order_by(desc(RadiacionSolar.fecha))
                .first()
            )

            umbral_radiacion = config.umbral_radiacion_baja
            motivo_radiacion = "límite manual"

            # Si está en el valor por defecto (2.0), calculamos dinámicamente. La radiación típica de Riohacha es excelente,
            # así que definimos recurso bajo si está por debajo del 60% de la media habitual (~3.5 kWh/m²/día).
            if config.umbral_radiacion_baja == 2.0:
                umbral_radiacion = 3.5
                motivo_radiacion = "calculado dinámicamente según la media climatológica de Riohacha"

            if (
                rad_reciente
                and rad_reciente.ghi is not None
                and rad_reciente.ghi < umbral_radiacion
            ):
                a = self._crear_si_no_existe_hoy(
                    db,
                    empresa.id,
                    tipo="baja_radiacion",
                    mensaje=(
                        f"Recurso solar actual bajo en Riohacha ({rad_reciente.ghi:.2f} kWh/m²/día, "
                        f"umbral dinámico: {umbral_radiacion:.1f} kWh/m²/día, {motivo_radiacion}). "
                        "Pre-cargue baterías desde la red y posponga consumos de alta potencia."
                    ),
                    severidad="media",
                )
                if a:
                    alertas_creadas.append(a)

        # 4. Pico de demanda (DINÁMICO)
        ultimo_consumo_pico = (
            db.query(ConsumoEnergetico)
            .filter(
                ConsumoEnergetico.empresa_id == empresa.id,
                ConsumoEnergetico.escenario == escenario,
            )
            .order_by(desc(ConsumoEnergetico.fecha))
            .first()
        )
        if ultimo_consumo_pico and ultimo_consumo_pico.demanda_pico_kw:
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
                and ultimo_consumo_pico.demanda_pico_kw > promedio_pico * 1.5
            ):
                exceso_pct = ((ultimo_consumo_pico.demanda_pico_kw / promedio_pico - 1) * 100)
                a = self._crear_si_no_existe_hoy(
                    db,
                    empresa.id,
                    tipo="pico_demanda",
                    mensaje=(
                        f"Pico de potencia registrado de {ultimo_consumo_pico.demanda_pico_kw:.1f} kW "
                        f"supera en {exceso_pct:.0f}% tu promedio histórico ({promedio_pico:.1f} kW). "
                        "Evita encender maquinaria o aires acondicionados de forma simultánea para reducir recargos de Air-E."
                    ),
                    severidad="alta",
                )
                if a:
                    alertas_creadas.append(a)

        # 5. Alerta de Riesgo de Apagón Predictivo por Tormentas y Vientos Fuertes (APIs externas - DINÁMICO y adaptado)
        try:
            from app.services.openmeteo import openmeteo_service
            forecast = await openmeteo_service.get_forecast_diario(days=3, allow_synthetic=True)
            if forecast:
                hoy_forecast = forecast[0]
                viento_max = hoy_forecast.get("viento_kmh_max", 0.0) or 0.0
                lluvia = hoy_forecast.get("precipitacion_mm", 0.0) or 0.0
                
                # Si el viento supera 40 km/h o la lluvia supera 20 mm (muy destructivo en infraestructura eléctrica de La Guajira)
                if viento_max > 40.0 or lluvia > 20.0:
                    # Adaptar el consejo dependiendo de si tiene baterías de respaldo
                    if tiene_baterias:
                        consejo_apagon = "Se recomienda activar la Carga Máxima Preventiva de tus baterías al 100% para asegurar la máxima autonomía de tu respaldo."
                    else:
                        consejo_apagon = "Como no cuentas con un sistema de baterías de respaldo solar, te recomendamos asegurar la carga completa de tus dispositivos móviles, linternas portátiles y tener a la mano sistemas de iluminación de emergencia."

                    a = self._crear_si_no_existe_hoy(
                        db,
                        empresa.id,
                        tipo="riesgo_apagon",
                        mensaje=(
                            f"Alerta climática de Red: Pronóstico de vientos fuertes ({viento_max:.1f} km/h) "
                            f"o lluvias ({lluvia:.1f} mm) en Riohacha. Estos factores aumentan en un 70% la probabilidad "
                            f"de cortes eléctricos y caída del suministro local. {consejo_apagon}"
                        ),
                        severidad="critica",
                    )
                    if a:
                        alertas_creadas.append(a)
        except Exception:
            pass

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
