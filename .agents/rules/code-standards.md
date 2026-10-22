# 🛠️ Estándares de Código y Arquitectura

Convenciones técnicas para backend, frontend y componentes de IA.

## 1. Backend (FastAPI)
- Rutas organizadas bajo `app/api/v1/endpoints/`.
- Modelos SQLAlchemy en `app/models/` y esquemas Pydantic v2 en `app/schemas/`.
- Inyección de dependencias para sesiones de base de datos (`get_db`).
- Respuestas HTTP con códigos de estado semánticos y tipado estricto.

## 2. Frontend (Streamlit)
- Entry point en `streamlit_app/Home.py` y páginas en `streamlit_app/pages/`.
- Separar lógica visual: invocar estilos y tarjetas desde `streamlit_app/design.py`.
- Consumo centralizado de endpoints vía `streamlit_app/api_client.py`.
- Manejo defensivo de estado en `st.session_state` con loaders y alertas amigables.

## 3. Capa de Inteligencia Artificial (Gemini)
- Uso de `google-genai` SDK (modelo `gemini-2.5-flash-lite` / `3.5`).
- Fallback obligatorio: si no hay `GEMINI_API_KEY`, activar el motor heurístico local.
- No romper flujos en caso de rate limits o desconexión externa.

## 4. Datos y Entorno
- Respetar `.env.example` y variables de configuración en `app/core/config.py`.
- Prohibido hardcodear credenciales, tokens o URLs sensibles.
- Cuidar compatibilidad con despliegues en Docker (`docker-compose.yml`).
