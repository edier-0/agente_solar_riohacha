from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.core.config import get_settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.session import get_db
from app.models.models import User, Empresa, ConfiguracionAlerta
from app.schemas.schemas import MessageResponse, Token, UserCreate, UserLogin, UserResponse


router = APIRouter(prefix="/auth", tags=["Autenticacion"])
settings = get_settings()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Registrar nuevo usuario."""
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo ya esta registrado",
        )

    if user_data.escenario_usuario not in ("demo", "real"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="escenario_usuario debe ser 'demo' o 'real'",
        )

    empresa_id = user_data.empresa_id
    if not empresa_id:
        # Crear automáticamente una empresa/hogar si no se provee
        nombre_emp = user_data.nombre_empresa or f"Hogar de {user_data.full_name}"
        tipo_emp = user_data.tipo_empresa or "hogar"
        tarifa = user_data.tarifa_kwh if user_data.tarifa_kwh is not None else 943.0

        nueva_empresa = Empresa(
            nombre=nombre_emp,
            tipo=tipo_emp,
            tarifa_kwh=tarifa,
            escenario_default=user_data.escenario_usuario,
        )
        db.add(nueva_empresa)
        db.commit()
        db.refresh(nueva_empresa)
        empresa_id = nueva_empresa.id

        # Crear configuración de alertas por defecto
        nueva_config = ConfiguracionAlerta(empresa_id=empresa_id)
        db.add(nueva_config)
        db.commit()

    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
        escenario_usuario=user_data.escenario_usuario,
        empresa_id=empresa_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """Login con email y password. Retorna JWT."""
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta inactiva",
        )

    access_token = create_access_token(
        data={
            "user_id": user.id,
            "email": user.email,
            "role": user.role.value,
            "empresa_id": user.empresa_id,
        },
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Obtener informacion del usuario autenticado."""
    return current_user


@router.post("/logout", response_model=MessageResponse)
def logout(current_user: User = Depends(get_current_user)):
    """
    Cerrar sesion del usuario autenticado.

    La autenticacion actual usa JWT stateless, asi que esta ruta valida el token
    recibido y permite al cliente cerrar sesion de forma explicita limpiando su
    estado local.
    """
    return MessageResponse(message=f"Sesion cerrada correctamente para {current_user.email}")
