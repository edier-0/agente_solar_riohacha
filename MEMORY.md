# MEMORY.md — Agente Solar Riohacha / Fonseca (Ka'i)
Memoria del proyecto entre sesiones. Máximo ~50 líneas: resume o elimina lo que ya no aporte.

## Estado actual
- Plataforma operativa con FastAPI (8000/8002), Streamlit (8501/8503) y Docker Compose.
- Identidad visual **Ka'i** con frontend responsivo y paleta optimizada (#2FA38A, #D8A24A).
- Botón flotante FAB con `st.popover` fijo en esquina inferior derecha (`bottom: 24px`, `right: 24px`, `z-index: 9999`).
- Sanitización estricta de rutas: devuelve nombres de apartados del frontend (ej. 'Administración', 'Mis Aparatos').
- Motor dual activo: Google GenAI (`gemini-3.5-flash-lite`) + fallback heurístico local.
- Aislamiento multi-tenant por usuario autenticado (perfil hogar/negocio, aparatos y ficha solar).
- Rama dedicada activa: `feature/asistente-chat-kai` (100% local, no pusheada a remoto).
- Suite completa pasando al 100%: 79 tests (pytest con `requirements-dev.txt`).

## Decisiones (y por qué)
- **Widget flotante con `st.popover` y CSS**: Permite chat conversacional nativo y botón persistente al hacer scroll.
- **Doble selector CSS (marker + key condicional)**: Compatible con Streamlit 1.38 y versiones superiores.
- **Sanitización regex case y accent-insensitive**: Garantiza que nunca se devuelvan archivos `.py` al frontend.
- **Aislamiento de contexto backend**: Token JWT filtra exclusivamente los datos de la entidad del usuario.
- **Tarifa Air-E ($943 COP/kWh) y reserva de baterías 30-40%**: Modelado realista para La Guajira.

## Aprendizajes y errores a evitar
- La directiva `@media (prefers-reduced-motion: reduce)` debe cerrarse adecuadamente para no atrapar estilos posteriores.
- `st.popover` en Streamlit 1.38 no acepta argumento `key`; usar inspección de signatura y marcador HTML.
- **NUNCA pushear la rama `feature/asistente-chat-kai` al remoto sin orden explícita del usuario.**

## Próximos pasos
- Recoger confirmación del usuario sobre el FAB flotante y la navegación en el frontend.

