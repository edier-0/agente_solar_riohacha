"""
Capa de traducción para alertas: convierte alertas técnicas en mensajes
accionables con emoji + acción sugerida concreta.

Tipos de alerta soportados (definidos en agente_alertas):
- consumo_alto, pico_demanda, bateria_baja, baja_radiacion, riesgo_apagon
"""
from typing import Dict, Optional


SEVERIDAD_NIVEL = {
    "critica": "rojo",
    "alta": "rojo",
    "media": "amarillo",
    "baja": "verde",
}

ICONO_TIPO = {
    "consumo_alto": "⚡",
    "pico_demanda": "📈",
    "bateria_baja": "🔋",
    "baja_radiacion": "☁️",
    "riesgo_apagon": "🔌",
}

# Plantillas de mensaje + acción por tipo de alerta.
# El mensaje original técnico se conserva como detail.
PLANTILLAS = {
    "consumo_alto": {
        "titulo": "Tu consumo está disparado",
        "accion": "Revisa qué equipos están encendidos sin necesidad y apágalos ahora.",
    },
    "pico_demanda": {
        "titulo": "Pico de demanda detectado",
        "accion": "Distribuye el uso de equipos pesados para evitar cargo por potencia máxima.",
    },
    "bateria_baja": {
        "titulo": "Batería baja",
        "accion": "Reduce cargas no esenciales y conecta a red mientras se recarga.",
    },
    "baja_radiacion": {
        "titulo": "Día con poca radiación solar",
        "accion": "Hoy tus paneles producen menos. Pospón equipos pesados si es posible.",
    },
    "riesgo_apagon": {
        "titulo": "Riesgo de apagón próximo",
        "accion": "Carga las baterías al máximo y prepara tu plan de contingencia.",
    },
}


def humanizar_alerta(alerta: Dict) -> Dict:
    """
    Toma un dict de alerta crudo (de la BD) y devuelve la versión humanizada.
    No modifica el original.
    """
    tipo = alerta.get("tipo", "")
    severidad = alerta.get("severidad", "media")
    plantilla = PLANTILLAS.get(tipo, {
        "titulo": "Aviso del sistema",
        "accion": "Revisa el detalle y toma la acción que corresponda.",
    })

    return {
        "id": alerta.get("id"),
        "emoji": ICONO_TIPO.get(tipo, "🚨"),
        "nivel": SEVERIDAD_NIVEL.get(severidad, "amarillo"),
        "titulo": plantilla["titulo"],
        "mensaje": alerta.get("mensaje", ""),
        "accion": plantilla["accion"],
        "tipo_original": tipo,
        "severidad": severidad,
        "leida": alerta.get("leida", False),
        "created_at": alerta.get("created_at"),
        "empresa_id": alerta.get("empresa_id"),
    }


def humanizar_lote(alertas: list) -> list:
    return [humanizar_alerta(a) for a in alertas]
