"""
Widget flotante del Asistente Copiloto Ka'i.
Se renderiza en la esquina inferior derecha y abre el modal dialog conversacional de Ka'i,
disponible en todos los apartados de la aplicacion.
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

    # Inicializar historial si esta vacio
    if history_key not in st.session_state or not st.session_state[history_key]:
        nombre_entidad = user.get("empresa_nombre") or user.get("full_name") or "tu espacio"
        st.session_state[history_key] = [
            {
                "role": "assistant",
                "content": (
                    f"¡Hola, {escape(user.get('full_name', 'amigo'))}! Soy **Ka'i**, tu copiloto de energía solar en La Guajira. ☀️\n\n"
                    f"Estoy conectado con el perfil de **{escape(nombre_entidad)}** para resolver tus dudas sobre:\n"
                    "- 🧭 **Navegación:** En qué apartado encontrar cada función.\n"
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

    # Botones de sugerencias rapidas
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

    # Boton inferior para reiniciar chat
    col_izq, col_der = st.columns([3, 1])
    with col_der:
        if st.button("🗑️ Limpiar chat", key=f"kai_clear_{user_id}", use_container_width=True):
            st.session_state[history_key] = []
            st.rerun(scope="fragment")


def render_asistente_flotante(user: dict | None) -> None:
    """Renderiza el boton flotante en la esquina inferior derecha."""
    if not user:
        return

    st.markdown(
        """
        <style>
        .st-key-btn_preguntale_kai,
        div[data-testid="element-container"]:has(.st-key-btn_preguntale_kai),
        div[data-testid="stElementContainer"]:has(.st-key-btn_preguntale_kai),
        .element-container:has(.st-key-btn_preguntale_kai),
        div:has(> .st-key-btn_preguntale_kai) {
            position: fixed !important;
            bottom: 24px !important;
            right: 24px !important;
            z-index: 9999999 !important;
            width: auto !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        .st-key-btn_preguntale_kai button,
        div[data-testid="element-container"]:has(.st-key-btn_preguntale_kai) button,
        div[data-testid="stElementContainer"]:has(.st-key-btn_preguntale_kai) button,
        .element-container:has(.st-key-btn_preguntale_kai) button {
            background: linear-gradient(135deg, #2FA38A 0%, #155546 100%) !important;
            color: #FFFFFF !important;
            border: 1.5px solid rgba(216, 162, 74, 0.75) !important;
            border-radius: 999px !important;
            padding: 0.75rem 1.4rem !important;
            font-size: 0.95rem !important;
            font-weight: 700 !important;
            letter-spacing: 0.01em !important;
            box-shadow: 0 10px 28px rgba(0, 0, 0, 0.55), 0 0 18px rgba(47, 163, 138, 0.45) !important;
            display: inline-flex !important;
            align-items: center !important;
            gap: 0.6rem !important;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
            cursor: pointer !important;
            width: auto !important;
        }

        .st-key-btn_preguntale_kai button p,
        div[data-testid="element-container"]:has(.st-key-btn_preguntale_kai) button p,
        div[data-testid="stElementContainer"]:has(.st-key-btn_preguntale_kai) button p {
            color: #FFFFFF !important;
            font-weight: 700 !important;
            font-size: 0.95rem !important;
            margin: 0 !important;
        }

        .st-key-btn_preguntale_kai button:hover,
        div[data-testid="element-container"]:has(.st-key-btn_preguntale_kai) button:hover,
        div[data-testid="stElementContainer"]:has(.st-key-btn_preguntale_kai) button:hover {
            transform: translateY(-3px) scale(1.05) !important;
            border-color: #D8A24A !important;
            background: linear-gradient(135deg, #37BD9F 0%, #1C6E5D 100%) !important;
            box-shadow: 0 14px 36px rgba(0, 0, 0, 0.7), 0 0 28px rgba(216, 162, 74, 0.65) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if st.button(
        "💬 Pregúntale a Ka'i",
        key="btn_preguntale_kai",
        help="Pregúntale a Ka'i sobre navegación en la app, consumo de aparatos o energía solar",
    ):
        dialog_chat_kai(user)
