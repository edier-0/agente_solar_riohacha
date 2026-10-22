# 🧠 Memoria del Proyecto: Agente Solar

Contexto persistente, estado del sistema y mapa de conocimiento.

## 1. Resumen del Sistema
- **Nombre**: Agente Solar Riohacha / Fonseca (La Guajira).
- **Propósito**: Copiloto de energía limpia, ahorro tarifario y resiliencia a apagones.
- **Stack**: FastAPI, Streamlit, SQLAlchemy, MySQL/Docker, Google GenAI.

## 2. Estado Actual y Contexto Activo
- **Ubicación clave**: Fonseca y Riohacha (La Guajira, Colombia).
- **Tarifa referencial**: ~$943 COP/kWh (Air-E). Radiación pico: 5.8 - 7.0 kWh/m²/día.
- **Doble perfil de usuario**: Residencial (comunitario/hogar) y Comercial (PYME).
- **Rama base de desarrollo**: `develop` (features se integran aquí previa orden).
- **Rama de producción**: `main`.

## 3. Servicios y Puertos
- Backend API: `http://localhost:8000` (Swagger: `/docs`).
- Frontend Streamlit: `http://localhost:8501`.
- Base de datos: MySQL 8.0 en Docker (`3306`) o SQLite local de respaldo.

## 4. Extensiones de Memoria
- [docs/memory/decisions.md](file:///docs/memory/decisions.md): Registro de decisiones (ADR y hitos).
- [docs/memory/system-patterns.md](file:///docs/memory/system-patterns.md): Patrones de arquitectura y cálculos solares.

## 5. Regla de Mantenimiento
- Actualizar este índice o sus extensiones al introducir cambios de fondo.
- Ningún archivo de memoria debe superar **50 líneas**.
