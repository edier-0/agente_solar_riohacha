# MEMORY.md — Agente Solar Riohacha / Fonseca
Memoria del proyecto entre sesiones. Máximo ~50 líneas: resume o elimina lo que ya no aporte.

## Estado actual
- Plataforma operativa con FastAPI (8000), Streamlit (8501) y Docker Compose.
- Datos y modelos migrados a Fonseca y Riohacha (La Guajira), radiación pico ~5.85 kWh/m²/día.
- Motor dual activo: Google GenAI (`gemini-2.5/3.5-flash-lite`) + fallback heurístico local.
- Perfiles adaptativos funcionando: Residencial (hogar/comunidad) y Comercial (PYME).
- Rama base de desarrollo: `develop` (al día y sincronizada con `main`).

## Decisiones (y por qué)
- **Motor dual IA + Heurística**: Asegurar operación continua offline durante cortes o sin API Key.
- **Flujo Git estricto por ramas**: Evitar tocar `develop`/`main` directo y esperar orden para PRs.
- **Desacoplamiento FastAPI/Streamlit**: Permite escalar API y frontend de forma independiente.
- **Regla <= 50 líneas**: Modularizar detalles en [docs/memory/decisions.md](file:///docs/memory/decisions.md) y [docs/memory/system-patterns.md](file:///docs/memory/system-patterns.md).
- **Autoría del Proyecto**: Asignada formalmente al equipo Code Masters y sus 4 integrantes en LICENSE y AUTHORS.md.

## Aprendizajes y errores a evitar
- No hardcodear `GEMINI_API_KEY` ni asumir conexión permanente a internet en La Guajira.
- Tarifa real de Air-E es ~$943 COP/kWh; nunca inventar métricas de ahorro sin sustento.
- Proteger profundidad de descarga en baterías (DoD) para no acortar su vida útil.

## Próximos pasos
- Afinar calibración del orquestador autónomo de baterías ante simulaciones de apagón.
- Robustecer suite de tests unitarios y de integración para endpoints clave.
