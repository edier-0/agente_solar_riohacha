from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.db.session import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    EMPRESA = "empresa"
    ANALISTA = "analista"


class VistaPreferida(str, enum.Enum):
    """Modo de visualización elegido por el usuario."""
    SIMPLE = "simple"            # Lenguaje natural, semáforos, sin números técnicos
    DETALLADO = "detallado"      # Series, métricas crudas, exportables
    OPERACIONAL = "operacional"  # Salud del sistema (admin)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(
        SQLEnum(UserRole, values_callable=lambda x: [e.value for e in x]),
        default=UserRole.EMPRESA,
        nullable=False,
    )
    vista_preferida = Column(
        SQLEnum(VistaPreferida, values_callable=lambda x: [e.value for e in x]),
        default=VistaPreferida.SIMPLE,
        nullable=False,
    )
    is_active = Column(Boolean, default=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    empresa = relationship("Empresa", back_populates="users")


class Empresa(Base):
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False)
    tipo = Column(String(100))  # hotel, hielera, retail, pyme, comunidad
    direccion = Column(String(500))
    ciudad = Column(String(100), default="Riohacha")
    departamento = Column(String(100), default="La Guajira")
    tarifa_kwh = Column(Float, default=943.0)  # COP/kWh
    capacidad_paneles_kw = Column(Float, default=0.0)
    capacidad_bateria_kwh = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    users = relationship("User", back_populates="empresa")
    consumos = relationship("ConsumoEnergetico", back_populates="empresa")
    alertas = relationship("Alerta", back_populates="empresa")
    recomendaciones = relationship("Recomendacion", back_populates="empresa")


class RadiacionSolar(Base):
    __tablename__ = "radiacion_solar"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(DateTime, nullable=False, index=True)
    ghi = Column(Float)  # Global Horizontal Irradiance (kWh/m²/día)
    dni = Column(Float)  # Direct Normal Irradiance
    dhi = Column(Float)  # Diffuse Horizontal Irradiance
    temperatura = Column(Float)  # °C (promedio)
    temperatura_max = Column(Float)  # °C
    temperatura_min = Column(Float)  # °C
    nubosidad = Column(Float)  # %
    precipitacion_mm = Column(Float)
    viento_kmh_max = Column(Float)
    # fuente: open_meteo (núcleo), openweather (complemento), pvgis (baseline),
    #         nasa_power (legacy), synthetic
    fuente = Column(String(50))
    latitud = Column(Float, default=11.5444)
    longitud = Column(Float, default=-72.9072)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ConsumoEnergetico(Base):
    __tablename__ = "consumo_energetico"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    fecha = Column(DateTime, nullable=False, index=True)
    consumo_kwh = Column(Float, nullable=False)
    costo_cop = Column(Float)
    demanda_pico_kw = Column(Float)
    produccion_solar_kwh = Column(Float, default=0.0)
    nivel_bateria_pct = Column(Float)
    periodo = Column(String(20))  # horario, diario, mensual
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    empresa = relationship("Empresa", back_populates="consumos")


class Alerta(Base):
    __tablename__ = "alertas"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    tipo = Column(String(50), nullable=False)  # consumo_alto, pico_demanda, bateria_baja, baja_radiacion, riesgo_apagon
    mensaje = Column(Text, nullable=False)
    severidad = Column(String(20), default="media")  # baja, media, alta, critica
    leida = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    empresa = relationship("Empresa", back_populates="alertas")


class Recomendacion(Base):
    __tablename__ = "recomendaciones"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    texto = Column(Text, nullable=False)
    tipo = Column(String(50))  # ahorro, redistribucion, contingencia, mantenimiento
    impacto_estimado_cop = Column(Float)
    confianza_pct = Column(Float)
    aplicada = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    empresa = relationship("Empresa", back_populates="recomendaciones")


class Prediccion(Base):
    __tablename__ = "predicciones"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)
    fecha_prediccion = Column(DateTime, nullable=False)
    fecha_objetivo = Column(DateTime, nullable=False)
    tipo = Column(String(50))  # produccion_solar, consumo, costo, riesgo_apagon
    valor = Column(Float, nullable=False)
    unidad = Column(String(20))  # kWh, COP, %
    confianza_pct = Column(Float)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ConfiguracionAlerta(Base):
    __tablename__ = "configuracion_alertas"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    umbral_consumo_diario_kwh = Column(Float, default=500.0)
    umbral_bateria_baja_pct = Column(Float, default=20.0)
    umbral_radiacion_baja = Column(Float, default=2.0)
    notificar_email = Column(Boolean, default=True)
    notificar_dashboard = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
