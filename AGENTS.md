# ☀️ Agente Solar - Directrices para Agentes

Guía operativa para agentes de IA que colaboren en este repositorio.

## 1. Identidad y Misión
- Proyecto: **Agente Solar Riohacha / Fonseca** (La Guajira, Colombia).
- Objetivo: Copiloto energético con FastAPI, Streamlit, Gemini y Docker.
- Prioridad: Resiliencia ante apagones, honestidad tarifaria y código robusto.

## 2. Flujo de Trabajo Git Obligatorio
- **Nunca trabajar directo en `main` o `develop`**.
- Crear una rama específica por tarea (`feature/*`, `fix/*`, `chore/*`).
- Realizar **commits atómicos** con Conventional Commits (`feat:`, `fix:`, etc.).
- **Protocolo de PR**: NO abrir PR ni hacer merge de forma autónoma.
  Esperar siempre la orden explícita del usuario indicando la rama destino.
- Detalles: [.agents/rules/git-workflow.md](file:///.agents/rules/git-workflow.md).

## 3. Estándares Técnicos
- Backend: FastAPI, SQLAlchemy 2.0, Pydantic v2, Python 3.11+.
- Frontend: Streamlit modular (`streamlit_app/pages/`).
- IA: Google GenAI SDK (`google-genai`), modelo Gemini 2.5/3.5 Flash Lite.
- Detalles: [.agents/rules/code-standards.md](file:///.agents/rules/code-standards.md).

## 4. Memoria y Constitución
- Consulta el contexto acumulado en [MEMORY.md](file:///MEMORY.md).
- Acata los principios éticos en [docs/constitution.md](file:///docs/constitution.md).

## 5. Regla de Brevedad Documental
- Ningún archivo de reglas o memoria debe superar **50 líneas**.
- Modularizar en extensiones si se requiere mayor profundidad.
