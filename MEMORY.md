# MEMORY.md — Agente Solar Riohacha / Fonseca (Ka'i)
Memoria del proyecto entre sesiones. Máximo ~50 líneas: resume o elimina lo que ya no aporte.

## Estado actual
- Plataforma operativa con FastAPI (8000/8002), Streamlit (8501/8503) y Docker Compose.
- Identidad visual **Ka'i** con frontend responsivo y paleta optimizada (#2FA38A, #D8A24A).
- Modal dialog conversacional `@st.dialog` con disparador FAB flotante en esquina inferior derecha.
- Sanitización estricta de rutas: devuelve exclusivamente nombres de apartados visibles en el frontend.
- Filtro estricto de navegación por rol en Ka'i (`admin`, `empresa`, `analista`): 'Datos solares' restringido para `empresa`, 'Administración' exclusivo de `admin`.
- Motor dual activo: Google GenAI (`gemini-3.5-flash-lite`) + fallback heurístico local sensible al rol.
- Transparencia en fuentes de clima: Ka'i menciona las APIs (Open-Meteo, NASA POWER, PVGIS, OpenWeatherMap) para todos los roles.
- Suite completa pasando al 100%: 86 tests (pytest con `requirements-dev.txt`).
- Rama local `feature/preparacion-proyecto-ingenova` fusionada con `feature/mencion-apis-clima-chat`.

## Decisiones (y por qué)
- **Filtrado dinámico de navegación por rol**: Evita que Ka'i recomiende pantallas que el usuario no tiene en su menú.
- **Diferenciación heurística por perfil**: Guía al usuario `empresa` hacia 'Mi día'/'Alertas' si pregunta por datos solares o le indica solicitar al admin cambios de paneles.
- **Modal dialog `@st.dialog` con fragment**: Ofrece la mejor experiencia visual amplia y cómoda para el usuario.
- **Tarifa Air-E ($943 COP/kWh) y reserva de baterías 30-40%**: Modelado realista para La Guajira.

## Aprendizajes y errores a evitar
- Sincronizar siempre los roles del asistente con `PAGE_VISIBILITY` de `streamlit_app/ui.py`.
- **NUNCA pushear ramas ni abrir PR al remoto sin orden explícita del usuario.**

## Próximos pasos
- Validar visualmente en el frontend la interacción según cada rol.


