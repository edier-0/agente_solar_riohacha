# MEMORY.md — Agente Solar Riohacha / Fonseca (Ka'i)
Memoria del proyecto entre sesiones. Máximo ~50 líneas: resume o elimina lo que ya no aporte.

## Estado actual
- Plataforma operativa con FastAPI (8000/8002), Streamlit (8501/8503) y Docker Compose.
- Identidad visual **Ka'i** con frontend responsivo y paleta optimizada (#2FA38A, #D8A24A).
- Asistente de chat flotante **Copiloto Ka'i** implementado en la esquina inferior derecha.
- Motor dual activo: Google GenAI (`gemini-3.5-flash-lite`) + fallback heurístico local.
- Aislamiento multi-tenant por usuario autenticado (perfil hogar/negocio, aparatos y ficha solar).
- Omnipresencia en toda la app: inyectado vía `ui.py` y disponible en todas las pantallas.
- Rama dedicada activa: `feature/asistente-chat-kai` creada desde `feature/preparacion-proyecto-ingenova`.
- Suite completa pasando al 100%: 77 tests (unitarios + integración chat).

## Decisiones (y por qué)
- **Widget flotante inferior derecho (`@st.dialog` + FAB)**: Accesible globalmente sin recargar la página.
- **Aislamiento de contexto backend**: Token JWT filtra exclusivamente los datos de la entidad del usuario.
- **Motor dual IA + Heurística**: Asegurar orientación de navegación y glosario técnico sin internet ni API Key.
- **Flujo Git estricto por ramas**: Commits atómicos y esperar orden del usuario antes de abrir PRs.
- **Tarifa Air-E ($943 COP/kWh) y reserva de baterías 30-40%**: Modelado realista para La Guajira.

## Aprendizajes y errores a evitar
- SQLite en tests exige `hashed_password` en modelo `User` (usar fixture `crear_usuario`).
- En `st.dialog`, usar fragments evita recarga completa de página al enviar mensajes o chips.
- Ejecutar tests siempre con `uv run --with-requirements requirements-dev.txt pytest`.

## Próximos pasos
- Presentar widget conversacional al usuario y recoger feedback o refinamientos visuales.
- Mantener rama `feature/asistente-chat-kai` lista para merge a petición del usuario.

