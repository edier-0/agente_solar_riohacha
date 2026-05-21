"""
Script de inicialización: crea admin, empresa demo y datos de prueba.
Ejecutar: python scripts/seed.py
"""
import sys
import os
from datetime import datetime, timedelta
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal, engine, Base
from app.db.migrations import ensure_schema_compatibility
from app.models import models
from app.models.models import (
    User, Empresa, ConsumoEnergetico, RadiacionSolar,
    ConfiguracionAlerta, UserRole,
)
from app.core.security import get_password_hash


def seed():
    print("[INFO] Creando tablas...")
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility(engine)

    db: Session = SessionLocal()

    try:
        # 1. Empresa demo
        empresa = db.query(Empresa).filter(Empresa.nombre == "Hotel Solar Riohacha").first()
        if not empresa:
            empresa = Empresa(
                nombre="Hotel Solar Riohacha",
                tipo="hotel",
                direccion="Av. La Marina #5-15, Riohacha",
                ciudad="Riohacha",
                departamento="La Guajira",
                tarifa_kwh=943.0,
                capacidad_paneles_kw=15.0,
                capacidad_bateria_kwh=30.0,
            )
            db.add(empresa)
            db.commit()
            db.refresh(empresa)
            print(f"[OK] Empresa demo creada: {empresa.nombre} (ID {empresa.id})")

            # Configuración de alertas por defecto
            config = ConfiguracionAlerta(
                empresa_id=empresa.id,
                umbral_consumo_diario_kwh=400.0,
                umbral_bateria_baja_pct=20.0,
                umbral_radiacion_baja=2.5,
            )
            db.add(config)
            db.commit()
        else:
            print(f"[SKIP] Empresa demo ya existe (ID {empresa.id})")

        # 2. Usuarios
        usuarios_demo = [
            {
                "email": "admin@agentesolar.co",
                "password": "admin123",
                "full_name": "Administrador del Sistema",
                "role": UserRole.ADMIN,
                "empresa_id": None,
            },
            {
                "email": "hotel@agentesolar.co",
                "password": "hotel123",
                "full_name": "Gerente Hotel Solar",
                "role": UserRole.EMPRESA,
                "empresa_id": empresa.id,
            },
            {
                "email": "analista@agentesolar.co",
                "password": "analista123",
                "full_name": "Analista Energético",
                "role": UserRole.ANALISTA,
                "empresa_id": None,
            },
        ]

        for u_data in usuarios_demo:
            existing = db.query(User).filter(User.email == u_data["email"]).first()
            if not existing:
                u = User(
                    email=u_data["email"],
                    hashed_password=get_password_hash(u_data["password"]),
                    full_name=u_data["full_name"],
                    role=u_data["role"],
                    empresa_id=u_data["empresa_id"],
                )
                db.add(u)
                db.commit()
                print(f"[OK] Usuario creado: {u.email} ({u.role.value})")
            else:
                print(f"[SKIP] Usuario ya existe: {u_data['email']}")

        # 3. Datos sintéticos de consumo (últimos 60 días)
        consumo_count = (
            db.query(ConsumoEnergetico)
            .filter(ConsumoEnergetico.empresa_id == empresa.id)
            .count()
        )
        if consumo_count == 0:
            print("[INFO] Generando datos sintéticos de consumo (60 días)...")
            random.seed(42)
            ahora = datetime.now()
            for i in range(60):
                fecha = ahora - timedelta(days=i)
                # Hotel con patrón realista: 80% ocupación, picos en tardes
                base_consumo = 380 + random.gauss(0, 30)
                # Inyectar 2 anomalías
                if i in (15, 35):
                    base_consumo *= 1.6  # Día anómalo

                # Producción solar: depende del día
                base_produccion = max(0, 60 + random.gauss(0, 15))

                # Demanda pico (kW) ~ 18-25
                demanda = 20 + random.gauss(0, 3)

                # Batería
                bateria = max(20, min(100, 75 + random.gauss(0, 15)))

                consumo = ConsumoEnergetico(
                    empresa_id=empresa.id,
                    fecha=fecha.replace(hour=23, minute=59),
                    consumo_kwh=round(max(0, base_consumo), 2),
                    costo_cop=round(max(0, base_consumo) * empresa.tarifa_kwh, 0),
                    demanda_pico_kw=round(max(0, demanda), 2),
                    produccion_solar_kwh=round(base_produccion, 2),
                    nivel_bateria_pct=round(bateria, 1),
                    periodo="diario",
                )
                db.add(consumo)
            db.commit()
            print(f"[OK] 60 registros de consumo creados")
        else:
            print(f"[SKIP] Ya hay {consumo_count} registros de consumo")

        # 4. Datos sintéticos de radiación (últimos 60 días)
        rad_count = db.query(RadiacionSolar).count()
        if rad_count == 0:
            print("[INFO] Generando datos sintéticos de radiación solar (60 días)...")
            random.seed(7)
            ahora = datetime.now()
            for i in range(60):
                fecha = ahora - timedelta(days=i)
                # Riohacha: 5.5 - 7.0 kWh/m²/día
                ghi = 5.8 + random.gauss(0, 0.7)
                ghi = max(2.0, min(7.5, ghi))
                rad = RadiacionSolar(
                    fecha=fecha.replace(hour=12),
                    ghi=round(ghi, 2),
                    dni=round(ghi * 1.3 + random.gauss(0, 0.3), 2),
                    dhi=round(ghi * 0.4 + random.gauss(0, 0.2), 2),
                    temperatura=round(28 + random.gauss(0, 2), 1),
                    nubosidad=round(max(0, min(100, 25 + random.gauss(0, 15))), 1),
                    fuente="synthetic",
                    latitud=11.5444,
                    longitud=-72.9072,
                )
                db.add(rad)
            db.commit()
            print(f"[OK] 60 registros de radiación creados")
        else:
            print(f"[SKIP] Ya hay {rad_count} registros de radiación")

        print("\n" + "=" * 60)
        print("✅ SEED COMPLETO")
        print("=" * 60)
        print("Credenciales de acceso:")
        print("  Admin:    admin@agentesolar.co    / admin123")
        print("  Empresa:  hotel@agentesolar.co    / hotel123")
        print("  Analista: analista@agentesolar.co / analista123")
        print("=" * 60)

    except Exception as e:
        print(f"[ERROR] {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
