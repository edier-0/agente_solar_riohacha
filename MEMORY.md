# MEMORY.md — Agente Solar Riohacha / Fonseca (Ka'i)
Memoria del proyecto entre sesiones. Máximo ~50 líneas: resume o elimina lo que ya no aporte.

## Estado actual
- Plataforma operativa con FastAPI (8000/8002), Streamlit (8501/8503) y Docker Compose.
- Identidad visual **Ka'i** con frontend responsivo en todas las pantallas y paleta optimizada.
- Gestión de inventario de aparatos, consumo desglosado y catálogo técnico integrado.
- Alertas de clima municipal (Fonseca/Riohacha) y avisos de carga por electrodoméstico.
- Motor dual activo: Google GenAI (`gemini-3.5-flash-lite`) + fallback heurístico local.
- Entrada por login (con cuenta demo); alta de usuarios restringida a administradores.
- Rama dedicada activa: `feature/preparacion-proyecto-ingenova` (integrando cambios de `cambio_fronen2`).

## Decisiones (y por qué)
- **Motor dual IA + Heurística**: Asegurar operación continua offline durante cortes o sin API Key.
- **Flujo Git estricto por ramas**: Evitar tocar `develop`/`main` directo y esperar orden para PRs.
- **Desacoplamiento FastAPI/Streamlit**: Permite escalar API y frontend de forma independiente.
- **Autoría del Proyecto**: Asignada formalmente al equipo Code Masters en LICENSE y AUTHORS.md.
- **Tarifa de referencia Air-E ($890 - $943 COP/kWh)**: Modelado de facturación y ahorro real.
- **Registro administrativo**: Control de acceso para despliegues institucionales/comunitarios.
- **Frontend Responsivo**: Soporte adaptativo para dispositivos móviles y tabletas en territorio.

## Aprendizajes y errores a evitar
- No hardcodear `GEMINI_API_KEY` ni asumir conexión permanente a internet en La Guajira.
- Proteger profundidad de descarga en baterías (DoD) para no acortar su vida útil.
- Mantener compatibilidad de migraciones y modelos relacionales al incorporar aparatos.

## Próximos pasos
- Validar tests de integración y endpoints en la rama `feature/preparacion-proyecto-ingenova`.
- Afinar calibración del orquestador de baterías ante simulaciones de apagón para Ingenova.
- Consolidar documentación y preparar entrega final cuando el usuario lo indique.
