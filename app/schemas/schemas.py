from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.models.models import UserRole, VistaPreferida


# --- Auth Schemas ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.EMPRESA
    empresa_id: Optional[int] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    vista_preferida: VistaPreferida = VistaPreferida.SIMPLE
    is_active: bool
    empresa_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserPreferenciasUpdate(BaseModel):
    vista_preferida: VistaPreferida


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None
    role: Optional[str] = None


# --- Empresa Schemas ---
class EmpresaCreate(BaseModel):
    nombre: str
    tipo: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: str = "Riohacha"
    departamento: str = "La Guajira"
    tarifa_kwh: float = 943.0
    capacidad_paneles_kw: float = 0.0
    capacidad_bateria_kwh: float = 0.0


class EmpresaUpdate(BaseModel):
    nombre: Optional[str] = None
    tipo: Optional[str] = None
    direccion: Optional[str] = None
    tarifa_kwh: Optional[float] = None
    capacidad_paneles_kw: Optional[float] = None
    capacidad_bateria_kwh: Optional[float] = None


class EmpresaResponse(BaseModel):
    id: int
    nombre: str
    tipo: Optional[str]
    direccion: Optional[str]
    ciudad: str
    departamento: str
    tarifa_kwh: float
    capacidad_paneles_kw: float
    capacidad_bateria_kwh: float
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- Consumo Schemas ---
class ConsumoCreate(BaseModel):
    empresa_id: int
    fecha: datetime
    consumo_kwh: float
    costo_cop: Optional[float] = None
    demanda_pico_kw: Optional[float] = None
    produccion_solar_kwh: float = 0.0
    nivel_bateria_pct: Optional[float] = None
    periodo: str = "diario"


class ConsumoResponse(BaseModel):
    id: int
    empresa_id: int
    fecha: datetime
    consumo_kwh: float
    costo_cop: Optional[float]
    demanda_pico_kw: Optional[float]
    produccion_solar_kwh: float
    nivel_bateria_pct: Optional[float]
    periodo: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- Radiación Solar Schemas ---
class RadiacionResponse(BaseModel):
    id: int
    fecha: datetime
    ghi: Optional[float]
    dni: Optional[float]
    dhi: Optional[float]
    temperatura: Optional[float]
    temperatura_max: Optional[float] = None
    temperatura_min: Optional[float] = None
    nubosidad: Optional[float]
    precipitacion_mm: Optional[float] = None
    viento_kmh_max: Optional[float] = None
    fuente: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# --- Alertas Schemas ---
class AlertaResponse(BaseModel):
    id: int
    empresa_id: int
    tipo: str
    mensaje: str
    severidad: str
    leida: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AlertaUpdate(BaseModel):
    leida: bool = True


# --- Recomendaciones Schemas ---
class RecomendacionResponse(BaseModel):
    id: int
    empresa_id: int
    texto: str
    tipo: Optional[str]
    impacto_estimado_cop: Optional[float]
    confianza_pct: Optional[float]
    aplicada: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- Predicción Schemas ---
class PrediccionResponse(BaseModel):
    id: int
    empresa_id: Optional[int]
    fecha_prediccion: datetime
    fecha_objetivo: datetime
    tipo: str
    valor: float
    unidad: Optional[str]
    confianza_pct: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


# --- Configuración Alertas ---
class ConfigAlertaUpdate(BaseModel):
    umbral_consumo_diario_kwh: Optional[float] = None
    umbral_bateria_baja_pct: Optional[float] = None
    umbral_radiacion_baja: Optional[float] = None
    notificar_email: Optional[bool] = None
    notificar_dashboard: Optional[bool] = None


# --- Dashboard KPIs ---
class DashboardKPIs(BaseModel):
    radiacion_actual_kwh: Optional[float] = None
    consumo_hoy_kwh: Optional[float] = None
    costo_hoy_cop: Optional[float] = None
    produccion_solar_hoy_kwh: Optional[float] = None
    ahorro_estimado_cop: Optional[float] = None
    nivel_bateria_pct: Optional[float] = None
    consumo_mes_kwh: Optional[float] = None
    costo_mes_cop: Optional[float] = None
