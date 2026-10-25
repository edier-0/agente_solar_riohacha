"""
Widget flotante del Asistente Copiloto Ka'i.
Se renderiza en la esquina inferior derecha y está disponible en todos los apartados de la app.
"""
from __future__ import annotations

from html import escape
from typing import Optional

import streamlit as st

from api_client import chat_copiloto


@st.dialog("☀️ Copiloto Ka'i — Asistente Solar & Navegación", width="large")
def dialog_chat_kai(user: dict) -> None:
    """Ventana conversacional del Copiloto Ka'i con aislamiento por usuario."""
    user_id = user.get("id", "anon")
    history_key = f"kai_chat_history_{user_id}"

    # Inicializar historial si está vacío
    if history_key not in st.session_state or not st.session_state[history_key]:
        nombre_entidad = user.get("empresa_nombre") or user.get("full_name") or "tu espacio"
        st.session_state[history_key] = [
            {
                "role": "assistant",
                "content": (
                    f"¡Hola, {escape(user.get('full_name', 'amigo'))}! Soy **Ka'i**, tu copiloto de energía solar en La Guajira. ☀️\n\n"
                    f"Estoy conectado con el perfil de **{escape(nombre_entidad)}** para resolver tus dudas sobre:\n"
                    "- 🧭 **Navegación:** En qué pantalla encontrar cada función.\n"
                    "- ⚡ **Aparatos:** Dónde registrar y consultar el consumo de tus electrodomésticos.\n"
                    "- ☀️ **Energía solar:** Cómo registrar paneles y baterías, o qué significan términos como DoD, kWp y kWh.\n"
                    "- 💰 **Tarifas:** Consejos de ahorro frente a la tarifa de Air-E ($943 COP/kWh).\n\n"
                    "¿En qué te puedo orientar hoy?"
                ),
                "sugerencias": [
                    "¿Dónde registro mis paneles y baterías?",
                    "¿Cuánto consumen mis aparatos?",
                    "¿Qué significa DoD y kWp?",
                    "¿Dónde veo el ahorro estimado?",
                ],
                "origen": "bienvenida",
            }
        ]

    # Barra superior de contexto
    entidad_nombre = user.get("empresa_nombre") or "Mi espacio"
    rol_label = user.get("role", "empresa").capitalize()
    st.markdown(
        f"""
        <div class="kai-chat-header">
            <div class="kai-chat-header__title">
                <span>☀️</span>
                <span>{escape(entidad_nombre)} ({rol_label})</span>
            </div>
            <div class="kai-chat-header__badge">
                Air-E: $943/kWh · La Guajira
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Renderizar historial de mensajes
    historial = st.session_state[history_key]
    contenedor_chat = st.container(height=360)
    with contenedor_chat:
        for msg in historial:
            role = msg["role"]
            avatar = "☀️" if role == "assistant" else "👤"
            with st.chat_message(role, avatar=avatar):
                st.markdown(msg["content"])
                if role == "assistant" and msg.get("origen") and msg["origen"] != "bienvenida":
                    origen = msg["origen"]
                    tag = (
                        "⚡ Google GenAI (gemini-3.5-flash-lite)"
                        if origen == "gemini"
                        else "🛡️ Motor Heurístico Local"
                    )
                    st.caption(f"*Fuente: {tag}*")

    # Botones de sugerencias rápidas
    ultimas_sugerencias = []
    for msg in reversed(historial):
        if msg.get("sugerencias"):
            ultimas_sugerencias = msg["sugerencias"][:4]
            break

    pregunta_seleccionada: Optional[str] = None
    if ultimas_sugerencias:
        st.markdown(
            "<div style='font-size: 0.78rem; color: #9AB0BB; margin-bottom: 4px;'>Sugerencias rápidas:</div>",
            unsafe_allow_html=True,
        )
        cols = st.columns(len(ultimas_sugerencias))
        for i, sugerencia in enumerate(ultimas_sugerencias):
            with cols[i]:
                st.markdown('<div class="kai-chip-btn">', unsafe_allow_html=True)
                if st.button(sugerencia, key=f"kai_sug_{user_id}_{i}_{len(historial)}", use_container_width=True):
                    pregunta_seleccionada = sugerencia
                st.markdown("</div>", unsafe_allow_html=True)

    # Entrada de texto del usuario
    prompt = st.chat_input("Escribe tu duda sobre la app o conceptos solares...")
    mensaje_a_enviar = prompt or pregunta_seleccionada

    if mensaje_a_enviar:
        # Agregar mensaje del usuario
        st.session_state[history_key].append({"role": "user", "content": mensaje_a_enviar})

        # Historial previo para Gemini
        historial_previo = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state[history_key][:-1]
            if m["role"] in ("user", "assistant")
        ]

        with st.spinner("Ka'i está consultando..."):
            resp = chat_copiloto(mensaje_a_enviar, historial_previo)
            if resp:
                st.session_state[history_key].append(
                    {
                        "role": "assistant",
                        "content": resp.get("respuesta", "Sin respuesta disponible."),
                        "sugerencias": resp.get("sugerencias", []),
                        "origen": resp.get("origen", "gemini"),
                    }
                )
            else:
                st.session_state[history_key].append(
                    {
                        "role": "assistant",
                        "content": "No pude conectar con el copiloto en este momento. Por favor verifica tu conexión a la API.",
                        "sugerencias": ["¿Dónde registro mis paneles?", "¿Qué es un kWh?"],
                        "origen": "error",
                    }
                )
        st.rerun(scope="fragment")

    # Botón inferior para reiniciar chat
    col_izq, col_der = st.columns([3, 1])
    with col_der:
        if st.button("🗑️ Limpiar chat", key=f"kai_clear_{user_id}", use_container_width=True):
            st.session_state[history_key] = []
            st.rerun(scope="fragment")


def render_asistente_flotante(user: dict | None) -> None:
    """Renderiza el botón flotante en la esquina inferior derecha."""
    if not user:
        return

    # Ancla invisible para que el selector CSS fije el botón en la esquina inferior derecha
    st.markdown('<div id="kai-fab-anchor"></div>', unsafe_allow_html=True)
    if st.button(
        "☀️ Copiloto Ka'i",
        key="btn_kai_chat_floating",
        help="Pregúntale a Ka'i sobre cómo usar la app o conceptos solares",
    ):
        dialog_chat_kai(user)
