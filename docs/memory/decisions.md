# 🏛️ Registro de Decisiones de Arquitectura (ADR)

Histórico de decisiones clave tomadas en el proyecto.

## ADR-001: Motor Dual de Recomendaciones (IA + Heurística)
- **Decisión**: Integrar Gemini API con un motor heurístico de respaldo.
- **Razón**: Garantizar funcionamiento offline/sin credenciales durante demos o cortes.

## ADR-002: Arquitectura Desacoplada (FastAPI + Streamlit)
- **Decisión**: Backend REST independiente de la interfaz Streamlit.
- **Razón**: Permite evolucionar el frontend o integrar clientes móviles sin tocar lógica.

## ADR-003: Enfoque Regional (Riohacha y Fonseca, La Guajira)
- **Decisión**: Adaptar perfiles solares, tarifas ($943 COP/kWh) y datos a La Guajira.
- **Razón**: Resolver la paradoja energética real de la región bajo criterios MinTIC.

## ADR-004: Adopción del SDK `google-genai` y Modelos Flash
- **Decisión**: Usar SDK oficial `google-genai` con modelo `gemini-2.5/3.5-flash-lite`.
- **Razón**: Respuestas ultrarrápidas, menor latencia y costo eficiente.

## ADR-005: Flujo Git Estricto por Ramas Atómicas
- **Decisión**: Ramas `feature/*`, commits atómicos y PR condicionado a orden manual.
- **Razón**: Mantener estabilidad en `develop`/`main` y control total del desarrollador.
