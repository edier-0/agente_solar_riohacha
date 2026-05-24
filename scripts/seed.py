"""
Script de inicializacion: crea empresa y usuarios demo.
Opcionalmente puede persistir series sinteticas en BD para compatibilidad legacy.
Ejecutar: python scripts/seed.py
"""
from __future__ import annotations

import os
import random
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.db.migrations import ensure_schema_compatibility
from app.db.session import Base, SessionLocal, engine
from app.models.models import (
    ConfiguracionAlerta,
    ConsumoEnergetico,
    Empresa,
    RadiacionSolar,
    User,
    UserRole,
)


def seed() -> None:
    print("[INFO] Creando tablas...")
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility(engine)

    db: Session = SessionLocal()
    persistir_sinteticos = os.getenv("SEED_PERSIST_SYNTHETIC", "0").strip().lower() in ("1", "true", "yes")

    try:
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
                escenario_default="demo",
            )
            db.add(empresa)
            db.commit()
            db.refresh(empresa)
            print(f"[OK] Empresa demo creada: {empresa.nombre} (ID {empresa.id})")

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

        usuarios_demo = [
            {
                "email": "admin@agentesolar.co",
                "password": "admin123",
                "full_name": "Administrador del Sistema",
                "role": UserRole.ADMIN,
                "empresa_id": None,
                "escenario_usuario": "demo",
            },
            {
                "email": "hotel@agentesolar.co",
                "password": "hotel123",
                "full_name": "Gerente Hotel Solar",
                "role": UserRole.EMPRESA,
                "empresa_id": empresa.id,
                "escenario_usuario": "demo",
            },
            {
                "email": "analista@agentesolar.co",
                "password": "analista123",
                "full_name": "Analista Energetico",
                "role": UserRole.ANALISTA,
                "empresa_id": None,
                "escenario_usuario": "demo",
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
                    escenario_usuario=u_data["escenario_usuario"],
                    empresa_id=u_data["empresa_id"],
                )
                db.add(u)
                db.commit()
                print(f"[OK] Usuario creado: {u.email} ({u.role.value}, {u.escenario_usuario})")
            else:
                print(f"[SKIP] Usuario ya existe: {u_data['email']}")

        if persistir_sinteticos:
            consumo_count = (
                db.query(ConsumoEnergetico)
                .filter(ConsumoEnergetico.empresa_id == empresa.id)
                .count()
            )
            if consumo_count == 0:
                print("[INFO] Generando datos sinteticos de consumo (60 dias)...")
                random.seed(42)
                ahora = datetime.now()
                for i in range(60):
                    fecha = ahora - timedelta(days=i)
                    base_consumo = 380 + random.gauss(0, 30)
                    if i in (15, 35):
                        base_consumo *= 1.6
                    base_produccion = max(0, 60 + random.gauss(0, 15))
                    demanda = 20 + random.gauss(0, 3)
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
                        escenario="demo",
                        origen_dato="seed_demo",
                        confiabilidad=35.0,
                    )
                    db.add(consumo)
                db.commit()
                print("[OK] 60 registros de consumo creados")

            rad_count = db.query(RadiacionSolar).count()
            if rad_count == 0:
                print("[INFO] Generando datos sinteticos de radiacion solar (60 dias)...")
                random.seed(7)
                ahora = datetime.now()
                for i in range(60):
                    fecha = ahora - timedelta(days=i)
                    ghi = max(2.0, min(7.5, 5.8 + random.gauss(0, 0.7)))
                    rad = RadiacionSolar(
                        fecha=fecha.replace(hour=12),
                        ghi=round(ghi, 2),
                        dni=round(ghi * 1.3 + random.gauss(0, 0.3), 2),
                        dhi=round(ghi * 0.4 + random.gauss(0, 0.2), 2),
                        temperatura=round(28 + random.gauss(0, 2), 1),
                        nubosidad=round(max(0, min(100, 25 + random.gauss(0, 15))), 1),
                        fuente="synthetic",
                        escenario="demo",
                        origen_dato="seed_demo",
                        confiabilidad=35.0,
                        latitud=11.5444,
                        longitud=-72.9072,
                    )
                    db.add(rad)
                db.commit()
                print("[OK] 60 registros de radiacion creados")
        else:
            print("[INFO] Seed sin series sinteticas en BD (SEED_PERSIST_SYNTHETIC=0).")

        print("\n" + "=" * 60)
        print("SEED COMPLETO")
        print("=" * 60)
        print("Credenciales demo:")
        print("  Admin:    admin@agentesolar.co    / admin123")
        print("  Empresa:  hotel@agentesolar.co    / hotel123")
        print("  Analista: analista@agentesolar.co / analista123")
        print("=" * 60)

    except Exception as exc:
        print(f"[ERROR] {exc}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()

