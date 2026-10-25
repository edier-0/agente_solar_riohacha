"""
Widget flotante del Asistente Copiloto Ka'i.
Implementado como Floating Action Button (FAB) en la esquina inferior derecha mediante st.popover,
fijo sobre todo el contenido al hacer scroll y disponible en todos los apartados de la aplicacion.
"""
from __future__ import annotations

import inspect
from html import escape
from typing import Optional

import streamlit as st

from api_client import chat_copiloto


FLOATING_CHAT_CSS = """
<style>
/* Marcador invisible para anclar el selector del popover adyacente */
.kai-floating-marker,
div:has(> .kai-floating-marker),
div[data-testid="stElementContainer"]:has(.kai-floating-marker),
div[data-testid="element-container"]:has(.kai-floating-marker),
.element-container:has(.kai-floating-marker) {
    display: none !important;
    height: 0 !important;
    width: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* Contenedor del Popover flotante en la esquina inferior derecha (soporta st.popover con y sin key) */
.st-key-btn_preguntale_kai,
div[data-testid="stPopover"]:has(.st-key-btn_preguntale_kai),
div[data-testid="stElementContainer"]:has(.st-key-btn_preguntale_kai),
div[data-testid="element-container"]:has(.st-key-btn_preguntale_kai),
div.element-container:has(.st-key-btn_preguntale_kai),
div:has(> .st-key-btn_preguntale_kai),
div[data-testid="stElementContainer"]:has(.kai-floating-marker) + div[data-testid="stElementContainer"],
div[data-testid="element-container"]:has(.kai-floating-marker) + div[data-testid="element-container"],
.element-container:has(.kai-floating-marker) + .element-container {
    position: fixed !important;
    bottom: 24px !important;
    right: 24px !important;
    z-index: 9999 !important;
    width: auto !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* Boton flotante disparador de Ka'i */
.st-key-btn_preguntale_kai > button,
.st-key-btn_preguntale_kai button,
div[data-testid="stPopover"]:has(.st-key-btn_preguntale_kai) button,
div[data-testid="stElementContainer"]:has(.kai-floating-marker) + div[data-testid="stElementContainer"] button,
div[data-testid="element-container"]:has(.kai-floating-marker) + div[data-testid="element-container"] button,
.element-container:has(.kai-floating-marker) + .element-container button {
    background: linear-gradient(135deg, #2FA38A 0%, #155546 100%) !important;
    color: #FFFFFF !important;
    border: 1.5px solid rgba(216, 162, 74, 0.85) !important;
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

.st-key-btn_preguntale_kai > button:hover,
.st-key-btn_preguntale_kai button:hover,
div[data-testid="stPopover"]:has(.st-key-btn_preguntale_kai) button:hover,
div[data-testid="stElementContainer"]:has(.kai-floating-marker) + div[data-testid="stElementContainer"] button:hover,
div[data-testid="element-container"]:has(.kai-floating-marker) + div[data-testid="element-container"] button:hover,
.element-container:has(.kai-floating-marker) + .element-container button:hover {
    transform: translateY(-3px) scale(1.04) !important;
    border-color: #D8A24A !important;
    background: linear-gradient(135deg, #37BD9F 0%, #1C6E5D 100%) !important;
    box-shadow: 0 14px 36px rgba(0, 0, 0, 0.7), 0 0 28px rgba(216, 162, 74, 0.65) !important;
}

.st-key-btn_preguntale_kai button p,
.st-key-btn_preguntale_kai button span,
div[data-testid="stElementContainer"]:has(.kai-floating-marker) + div[data-testid="stElementContainer"] button p,
div[data-testid="element-container"]:has(.kai-floating-marker) + div[data-testid="element-container"] button p {
    color: #FFFFFF !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    margin: 0 !important;
}

/* Ventana desplegable del Popover */
[data-testid="stPopoverBody"],
div[data-testid="stPopoverBody"] {
    background: #0F1D27 !important;
    border: 1px solid #213A49 !important;
    border-radius: 18px !important;
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.85), 0 0 24px rgba(47, 163, 138, 0.25) !important;
    width: min(440px, 92vw) !important;
    max-width: 460px !important;
    max-height: 82vh !important;
    padding: 1rem !important;
}

div[data-baseweb="popover"] {
    background: transparent !important;
}

div[data-baseweb="popover"] > div {
    background: #0F1D27 !important;
    border: 1px solid #213A49 !important;
    border-radius: 18px !important;
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.85), 0 0 24px rgba(47, 163, 138, 0.25) !important;
}

.kai-chat-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.6rem 0.85rem;
    background: rgba(47, 163, 138, 0.08);
    border: 1px solid rgba(47, 163, 138, 0.25);
    border-radius: 12px;
    margin-bottom: 0.75rem;
}

.kai-chat-header__title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: 700;
    color: #EAF2F6;
    font-size: 0.92rem;
}

.kai-chat-header__badge {
    font-size: 0.72rem;
    padding: 0.2rem 0.5rem;
    border-radius: 999px;
    background: rgba(216, 162, 74, 0.14);
    border: 1px solid rgba(216, 162, 74, 0.35);
    color: #E3B866;
    font-weight: 600;
}

.kai-chip-btn button {
    border-radius: 999px !important;
    font-size: 0.76rem !important;
    padding: 0.2rem 0.6rem !important;
    background: rgba(47, 163, 138, 0.09) !important;
    border: 1px solid rgba(47, 163, 138, 0.3) !important;
    color: #EAF2F6 !important;
    transition: all 0.2s ease !important;
}

.kai-chip-btn button:hover {
    background: rgba(47, 163, 138, 0.2) !important;
    border-color: #2FA38A !important;
    color: #FFFFFF !important;
    transform: translateY(-1px) !important;
}
</style>
"""


def render_asistente_flotante(user: dict | None) -> None:
    """Renderiza el boton flotante de chat fijo en la esquina inferior derecha usando st.popover."""
    if not user:
        return

    # Inyeccion de estilos para garantizar posicionamiento flotante sobre el contenido
    st.markdown(FLOATING_CHAT_CSS, unsafe_allow_html=True)
    st.markdown('<span class="kai-floating-marker"></span>', unsafe_allow_html=True)

    popover_kwargs = {
        "help": "Preguntale a Ka'i sobre navegacion en la app, consumo de aparatos o energia solar",
    }
    # Soporte compatible para versiones nuevas de Streamlit que admiten key en st.popover
    if "key" in inspect.signature(st.popover).parameters:
        popover_kwargs["key"] = "btn_preguntale_kai"

    popover = st.popover("💬 Pregúntale a Ka'i", **popover_kwargs)

    with popover:
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

        # Historial de mensajes
        historial = st.session_state[history_key]
        contenedor_chat = st.container(height=340)
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
                ultimas_sugerencias = msg["sugerencias"][:3]
                break

        pregunta_seleccionada: Optional[str] = None
        if ultimas_sugerencias:
            st.markdown(
                "<div style='font-size: 0.76rem; color: #9AB0BB; margin: 4px 0 2px 2px; font-weight: 600;'>Sugerencias rápidas:</div>",
                unsafe_allow_html=True,
            )
            cols = st.columns(len(ultimas_sugerencias))
            for i, sugerencia in enumerate(ultimas_sugerencias):
                with cols[i]:
                    st.markdown('<div class="kai-chip-btn">', unsafe_allow_html=True)
                    if st.button(
                        sugerencia,
                        key=f"kai_sug_{user_id}_{i}_{len(historial)}",
                        use_container_width=True,
                    ):
                        pregunta_seleccionada = sugerencia
                    st.markdown("</div>", unsafe_allow_html=True)

        # Entrada de texto del usuario nativa
        prompt = st.chat_input("Escribe tu duda sobre la app o conceptos solares...")
        mensaje_a_enviar = prompt or pregunta_seleccionada

        if mensaje_a_enviar:
            st.session_state[history_key].append({"role": "user", "content": mensaje_a_enviar})

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
            st.rerun()

        # Boton inferior para reiniciar chat
        col_izq, col_der = st.columns([2.8, 1.2])
        with col_der:
            if st.button("🗑️ Limpiar", key=f"kai_clear_{user_id}", use_container_width=True):
                st.session_state[history_key] = []
                st.rerun()
