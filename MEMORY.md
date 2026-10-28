# MEMORY.md — Agente Solar Riohacha / Fonseca (Ka'i)
Memoria del proyecto entre sesiones. Máximo ~50 líneas: resume o elimina lo que ya no aporte.

## Estado actual
- Plataforma operativa con FastAPI (8000/8002), Streamlit (8501/8503) y Docker Compose.
- Identidad visual **Ka'i** con frontend responsivo y paleta optimizada (#2FA38A, #D8A24A).
<<<<<<< HEAD
- Modal dialog conversacional `@st.dialog` restaurado (diseño amplio, limpio y persistente con fragment).
- Botón disparador flotante FAB fijo en esquina inferior derecha (`bottom: 24px`, `right: 24px`, `z-index: 9999999`).
- Sanitización estricta de rutas: devuelve nombres de apartados del frontend (ej. 'Administración', 'Mis Aparatos').
- Motor dual activo: Google GenAI (`gemini-3.5-flash-lite`) + fallback heurístico local.
- Rama `feature/asistente-chat-kai` integrada y fusionada vía PR #8 en `feature/preparacion-proyecto-ingenova`.
- Suite: 91 tests (pytest con `requirements-dev.txt`); el de AppTest del widget necesita streamlit instalado.
- Rama `feature/baterias-balance-solar` (sin commit): banco de varias baterías (tabla `baterias_instalacion`),
  pantalla "Mi sistema solar", balance solar diario (`/empresas/{id}/balance-solar`) y alertas solares.
=======
- Modal dialog conversacional `@st.dialog` con disparador FAB flotante en esquina inferior derecha.
- Sanitización estricta de rutas: devuelve exclusivamente nombres de apartados visibles en el frontend.
- Filtro estricto de navegación por rol en Ka'i (`admin`, `empresa`, `analista`): 'Datos solares' restringido para `empresa`, 'Administración' exclusivo de `admin`.
- Motor dual activo: Google GenAI (`gemini-3.5-flash-lite`) + fallback heurístico local sensible al rol.
- Transparencia en fuentes de clima: Ka'i menciona las APIs (Open-Meteo, NASA POWER, PVGIS, OpenWeatherMap) para todos los roles.
- Suite completa pasando al 100%: 86 tests (pytest con `requirements-dev.txt`).
- PR #10 fusionado en `feature/preparacion-proyecto-ingenova`: transparencia y soporte de APIs del clima en copiloto Ka'i.
>>>>>>> 71c0ebe646bca60e7f6c58389da885c1a41f8920

## Decisiones (y por qué)
- **Filtrado dinámico de navegación por rol**: Evita que Ka'i recomiende pantallas que el usuario no tiene en su menú.
- **Diferenciación heurística por perfil**: Guía al usuario `empresa` hacia 'Mi día'/'Alertas' si pregunta por datos solares o le indica solicitar al admin cambios de paneles.
- **Modal dialog `@st.dialog` con fragment**: Ofrece la mejor experiencia visual amplia y cómoda para el usuario.
- **Tarifa Air-E ($943 COP/kWh) y reserva de baterías 30-40%**: Modelado realista para La Guajira.
- **Balance solar estimado, no medido**: producción = GHI real (Open-Meteo, respaldo NASA POWER) x kWp x PR;
  sin radiación no se inventa producción. Con paneles la factura solo es la red: se usa el consumo
  (aparatos o perfil) cuya red estimada más se parece a la factura.
- **Baterías en lista** (`baterias_instalacion`, con cantidad): las columnas de la ficha guardan la primera;
  las instalaciones viejas se migran solas al leerlas.

## Aprendizajes y errores a evitar
- Sincronizar siempre los roles del asistente con `PAGE_VISIBILITY` de `streamlit_app/ui.py`.
- **NUNCA pushear ramas ni abrir PR al remoto sin orden explícita del usuario.**

## Próximos pasos
- Validar visualmente en el frontend la interacción según cada rol.


