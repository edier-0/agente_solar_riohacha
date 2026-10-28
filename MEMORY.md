# MEMORY.md — Agente Solar Riohacha / Fonseca (Ka'i)
Memoria del proyecto entre sesiones. Máximo ~50 líneas: resume o elimina lo que ya no aporte.

## Estado actual
- Plataforma operativa con FastAPI (8000/8002), Streamlit (8501/8503) y Docker Compose.
- Identidad visual **Ka'i** con frontend responsivo y paleta optimizada (#2FA38A, #D8A24A).
- Modal dialog conversacional `@st.dialog` restaurado (diseño amplio, limpio y persistente con fragment).
- Botón disparador flotante FAB fijo en esquina inferior derecha (`bottom: 24px`, `right: 24px`, `z-index: 9999999`).
- Sanitización estricta de rutas: devuelve nombres de apartados del frontend (ej. 'Administración', 'Mis Aparatos').
- Motor dual activo: Google GenAI (`gemini-3.5-flash-lite`) + fallback heurístico local.
- Rama `feature/asistente-chat-kai` integrada y fusionada vía PR #8 en `feature/preparacion-proyecto-ingenova`.
- Suite: 91 tests (pytest con `requirements-dev.txt`); el de AppTest del widget necesita streamlit instalado.
- Rama `feature/baterias-balance-solar` (sin commit): banco de varias baterías (tabla `baterias_instalacion`),
  pantalla "Mi sistema solar", balance solar diario (`/empresas/{id}/balance-solar`) y alertas solares.

## Decisiones (y por qué)
- **Modal dialog `@st.dialog` con fragment**: Ofrece la mejor experiencia visual amplia y cómoda para el usuario.
- **Botón flotante con CSS inyectado y fijado en esquina inferior derecha**: Accesible en scroll sin estorbar.
- **Sanitización regex case y accent-insensitive**: Garantiza que nunca se devuelvan archivos `.py` al frontend.
- **Aislamiento de contexto backend**: Token JWT filtra exclusivamente los datos de la entidad del usuario.
- **Tarifa Air-E ($943 COP/kWh) y reserva de baterías 30-40%**: Modelado realista para La Guajira.
- **Balance solar estimado, no medido**: producción = GHI real (Open-Meteo, respaldo NASA POWER) x kWp x PR;
  sin radiación no se inventa producción. Con paneles la factura solo es la red: se usa el consumo
  (aparatos o perfil) cuya red estimada más se parece a la factura.
- **Baterías en lista** (`baterias_instalacion`, con cantidad): las columnas de la ficha guardan la primera;
  las instalaciones viejas se migran solas al leerlas.

## Aprendizajes y errores a evitar
- El diseño modal `@st.dialog` es preferido por el usuario frente a popovers compactos.
- La directiva `@media (prefers-reduced-motion: reduce)` debe cerrarse adecuadamente para no atrapar estilos posteriores.
- **NUNCA pushear la rama `feature/asistente-chat-kai` al remoto sin orden explícita del usuario.**

## Próximos pasos
- Confirmar visualización en el frontend levantado con Docker.

