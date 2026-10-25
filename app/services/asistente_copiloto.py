"""
Servicio del Asistente Copiloto Ka'i.
Responde dudas de navegación, glosario técnico y guía de uso del aplicativo,
inyectando el contexto aislado de la empresa o casa del usuario autenticado.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.models import AparatoUsuario, Empresa, InstalacionSolar, User
from app.schemas.schemas import ChatAsistenteRequest, ChatAsistenteResponse
from app.services.aparatos import calcular_estadisticas
from app.services.gemini_client import obtener_respuesta_gemini

# Mapeo de navegación de la aplicación Ka'i
MAPA_NAVEGACION = [
    {
        "nombre": "Mi día",
        "archivo": "pages/0_Mi_Dia.py",
        "proposito": "Resumen ejecutivo diario: clima, horas de mayor sol, nivel de batería y consejos rápidos de ahorro.",
    },
    {
        "nombre": "Mis Aparatos",
        "archivo": "pages/0_Mis_Aparatos.py",
        "proposito": "Inventario de electrodomésticos y equipos: consumo detallado en W y kWh/mes, consejos por aparato y agregar nuevos.",
    },
    {
        "nombre": "Panel (Dashboard)",
        "archivo": "pages/1_Dashboard.py",
        "proposito": "Gráficos técnicos de telemetría: curvas de consumo, radiación solar y métricas consolidadas.",
    },
    {
        "nombre": "Consumo",
        "archivo": "pages/2_Consumo.py",
        "proposito": "Registro y consulta de recibos de energía de Air-E, costos acumulados y comparativas históricas.",
    },
    {
        "nombre": "Recomendaciones IA",
        "archivo": "pages/4_Recomendaciones_IA.py",
        "proposito": "Estrategias personalizadas de eficiencia energética y optimización horaria para reducir la factura.",
    },
    {
        "nombre": "Alertas",
        "archivo": "pages/5_Alertas.py",
        "proposito": "Alertas climáticas del municipio: calor extremo, lluvias torrenciales, vientos y riesgo de cortes eléctricos de red.",
    },
    {
        "nombre": "Predicciones",
        "archivo": "pages/6_Predicciones.py",
        "proposito": "Simulador de orquestación autónoma de baterías: autonomía en horas ante apagones según el riesgo de corte.",
    },
    {
        "nombre": "Reportes",
        "archivo": "pages/7_Reportes.py",
        "proposito": "Exportación y descarga de informes ejecutivos e históricos en formatos PDF y Excel.",
    },
    {
        "nombre": "Datos Solares",
        "archivo": "pages/3_Datos_Solares.py",
        "proposito": "Radiación solar histórica y pronósticos climáticos de La Guajira (Open-Meteo, NASA POWER, PVGIS).",
    },
    {
        "nombre": "Administración",
        "archivo": "pages/8_Administracion.py",
        "proposito": "Gestión de usuarios y entidades (solo administrador). Incluye la ficha técnica fotovoltaica en 'Tengo paneles solares'.",
    },
]


def construir_contexto_usuario(db: Session, user: User) -> Dict:
    """Extrae el contexto del usuario autenticado para inyectar en el asistente sin mezclar datos."""
    empresa: Optional[Empresa] = None
    if user.empresa_id:
        empresa = db.query(Empresa).filter(Empresa.id == user.empresa_id).first()

    contexto = {
        "usuario": {
            "nombre": user.full_name or "Usuario",
            "email": user.email,
            "rol": user.role.value if hasattr(user.role, "value") else str(user.role),
        },
        "entidad": {
            "nombre": empresa.nombre if empresa else "Sin entidad asignada",
            "tipo": empresa.tipo_entidad if empresa and empresa.tipo_entidad else "hogar",
            "ciudad": empresa.ciudad if empresa else "Fonseca",
            "departamento": empresa.departamento if empresa else "La Guajira",
            "tarifa_cop_kwh": empresa.tarifa_kwh if empresa else 943.0,
        },
        "solar": {
            "tiene_paneles": bool(empresa and empresa.capacidad_paneles_kw > 0),
            "capacidad_paneles_kw": empresa.capacidad_paneles_kw if empresa else 0.0,
            "tiene_bateria": bool(empresa and empresa.capacidad_bateria_kwh > 0),
            "capacidad_bateria_kwh": empresa.capacidad_bateria_kwh if empresa else 0.0,
        },
        "aparatos": {
            "total_registrados": 0,
            "consumo_estimado_kwh_mes": 0.0,
            "principales": [],
        },
        "navegacion": MAPA_NAVEGACION,
    }

    if empresa:
        # Ficha técnica si existe
        instalacion: Optional[InstalacionSolar] = (
            db.query(InstalacionSolar).filter(InstalacionSolar.empresa_id == empresa.id).first()
        )
        if instalacion:
            contexto["solar"]["detalles"] = {
                "potencia_panel_w": instalacion.potencia_panel_w,
                "cantidad_paneles": instalacion.cantidad_paneles,
                "orientacion": instalacion.orientacion,
                "quimica_bateria": instalacion.quimica_bateria,
                "voltaje_banco_v": instalacion.voltaje_banco_v,
                "capacidad_ah": instalacion.capacidad_ah,
                "potencia_inversor_w": instalacion.potencia_inversor_w,
            }

        # Resumen de aparatos
        try:
            stats = calcular_estadisticas(db, empresa)
            aparatos_lista = stats.get("aparatos", [])
            contexto["aparatos"]["total_registrados"] = len(aparatos_lista)
            contexto["aparatos"]["consumo_estimado_kwh_mes"] = round(stats.get("total_kwh_mes", 0.0), 1)
            # Top aparatos que más consumen
            ordenados = sorted(aparatos_lista, key=lambda a: a.get("consumo_kwh_mes", 0.0), reverse=True)
            contexto["aparatos"]["principales"] = [
                f"{a['nombre']} ({a['consumo_kwh_mes']:.1f} kWh/mes)" for a in ordenados[:4]
            ]
        except Exception:
            pass

    return contexto


def _sugerencias_por_defecto(tipo_entidad: str) -> List[str]:
    return [
        "¿Dónde veo el consumo de mis aparatos?",
        "¿Qué significa kWh y kWp?",
        "¿Cómo registro paneles solares o baterías?",
        "¿Qué precauciones tener ante riesgo de corte?",
    ]


def generar_respuesta_heuristica(mensaje: str, ctx: Dict) -> Tuple[str, List[str]]:
    """Motor heurístico de contingencia cuando no hay conexión a internet o no hay GEMINI_API_KEY."""
    m = mensaje.lower().strip()
    u = ctx.get("usuario", {})
    e = ctx.get("entidad", {})
    sol = ctx.get("solar", {})
    ap = ctx.get("aparatos", {})

    nombre_u = u.get("nombre", "amigo")
    tipo_ent = e.get("tipo", "hogar")
    es_hogar = tipo_ent == "hogar"

    sugerencias = _sugerencias_por_defecto(tipo_ent)

    # 1. Saludos
    if any(k in m for k in ("hola", "buenos días", "buenas tardes", "buenas noches", "saludos", "que tal")):
        tipo_str = "tu hogar" if es_hogar else "tu negocio"
        paneles_str = (
            f"con sistema solar de {sol['capacidad_paneles_kw']:.1f} kWp"
            if sol.get("tiene_paneles")
            else "sin paneles registrados aún"
        )
        return (
            f"¡Hola, {nombre_u}! Soy **Ka'i**, tu copiloto de energía solar en La Guajira. "
            f"Estoy aquí para guiarte en {tipo_str} ({e.get('nombre')}, {paneles_str}). "
            "¿En qué puedo orientarte hoy? Puedes preguntarme cómo navegar por el aplicativo, "
            "dónde consultar el consumo de tus equipos o qué significa cualquier término de energía.",
            sugerencias,
        )

    # 2. Dónde ver aparatos y consumo por aparato
    if any(k in m for k in ("aparato", "electrodomestico", "nevera", "aire", "consumen", "consumo de mis")):
        total = ap.get("total_registrados", 0)
        kwh = ap.get("consumo_estimado_kwh_mes", 0.0)
        principales = ", ".join(ap.get("principales", [])) if ap.get("principales") else "ninguno registrado aún"
        return (
            f"Para consultar cuánto consumen tus equipos, dirígete a la sección **'Mis Aparatos'** en el menú lateral. "
            f"\n\nEn {e.get('nombre')} tienes registrados **{total} aparatos** que suman un estimado de **{kwh} kWh al mes** "
            f"(principales: {principales}). En esa pantalla también puedes agregar aparatos del catálogo, ingresar equipos propios "
            "o editar las horas diarias que los utilizas.",
            ["Ir a Mis Aparatos", "¿Cómo registrar más aparatos?", "¿Qué es un kWh?"],
        )

    # 3. Paneles solares y baterías (dónde registrarlos o verlos)
    if any(k in m for k in ("panel", "paneles", "batería", "baterias", "bateria", "inversor", "registrar panel")):
        if sol.get("tiene_paneles") or sol.get("tiene_bateria"):
            info = f"Actualmente tienes registrados **{sol['capacidad_paneles_kw']:.1f} kWp en paneles**"
            if sol.get("tiene_bateria"):
                info += f" y un banco de baterías de **{sol['capacidad_bateria_kwh']:.1f} kWh**."
            else:
                info += " y sin baterías de almacenamiento."
        else:
            info = "Actualmente no tienes paneles ni baterías registrados en tu cuenta."

        return (
            f"{info}\n\n"
            "**¿Dónde se registran o editan?**\n"
            "Por seguridad, el alta de equipos fotovoltaicos se hace desde el menú **'Administración'** "
            "(con usuario Administrador) en la pestaña **'Nueva cuenta / Entidad'**, haciendo clic en el botón verde "
            "👉 **'Tengo paneles solares →'**. Allí se configura la ficha técnica completa: cantidad de paneles, potencia en W, "
            "química de la batería (Litio LiFePO4, Gel) y capacidad en Ah.",
            ["¿Qué es kWp?", "¿Qué es la profundidad de descarga (DoD)?", "¿Dónde veo la autonomía de batería?"],
        )

    # 4. Términos energéticos (Glosario)
    if "kwh" in m or "kilovatio hora" in m:
        return (
            "**¿Qué es un kWh (Kilovatio-hora)?**\n\n"
            "Es la unidad con la que la empresa de energía (Air-E) mide tu consumo y te cobra en la factura. "
            "Representa el uso de 1.000 vatios de potencia durante 1 hora continua. "
            f"En La Guajira, la tarifa de referencia de Air-E ronda los **${e.get('tarifa_cop_kwh', 943):,.0f} COP por cada kWh**.",
            ["¿Cuál es la diferencia entre kW y kWh?", "¿Qué es kWp?", "¿Dónde veo mis recibos de energía?"],
        )

    if "kwp" in m or "kilovatio pico" in m:
        return (
            "**¿Qué es kWp (Kilovatio pico)?**\n\n"
            "Es la potencia máxima que puede entregar tu conjunto de paneles solares bajo condiciones ideales de radiación "
            "(1.000 W/m² de sol y 25 °C). Por ejemplo, 10 paneles de 500 W suman 5.000 Wp = **5.0 kWp**.",
            ["¿Dónde veo cuántos kWp tengo?", "¿Qué significa HSP en radiación?", "¿Qué es un inversor?"],
        )

    if "dod" in m or "descarga" in m or "soc" in m:
        return (
            "**DoD y SoC en Baterías Solares:**\n\n"
            "- **SoC (State of Charge):** Es el porcentaje de batería disponible en este momento (100% = llena).\n"
            "- **DoD (Depth of Discharge):** Es la profundidad máxima recomendada para descargarla. En baterías de litio "
            "(LiFePO4) suele ser 80%-90%, mientras que en baterías de gel o plomo no debe superar el 50% para proteger su vida útil. "
            "En La Guajira, Ka'i recomienda programar una reserva mínima del 30%-40% para afrontar cortes repentinos de red.",
            ["¿Dónde simulo el uso de mi batería?", "¿Cómo me preparo ante un apagón?"],
        )

    # 5. Apagones, cortes y orquestación
    if any(k in m for k in ("apagon", "corte", "sin luz", "autonomia", "bateria")):
        return (
            "**Resiliencia ante Apagones:**\n\n"
            "En la sección **'Predicciones'** encontrarás el **Simulador de Orquestación de Baterías**. "
            "Allí puedes simular el nivel de riesgo de corte eléctrico en La Guajira y observar cuántas horas de autonomía "
            "tendría tu instalación según tus electrodomésticos críticos (nevera, iluminación, internet).",
            ["Ir a Predicciones", "Ver Alertas del clima", "¿Cómo proteger mis electrodomésticos?"],
        )

    # 6. Alertas del clima
    if any(k in m for k in ("alerta", "clima", "lluvia", "calor", "viento", "polvo")):
        return (
            f"En la sección **'Alertas'** monitoreamos el clima en tiempo real para **{e.get('ciudad', 'La Guajira')}**. "
            "El sistema evalúa calor extremo, tormentas que puedan causar cortes de luz y niveles de polvo PM10 en el aire "
            "que requieran limpiar tus paneles para que no pierdan producción.",
            ["Ir a Alertas", "¿Cómo afecta el polvo a los paneles?", "¿Dónde veo la radiación solar?"],
        )

    # 7. Recibos y facturación
    if any(k in m for k in ("factura", "recibo", "aire", "air-e", "tarifa", "costo")):
        return (
            f"En la sección **'Consumo'** puedes consultar el historial de facturación de tu energía y registrar recibos de Air-E. "
            f"Tu tarifa configurada es de **${e.get('tarifa_cop_kwh', 943):,.0f} COP/kWh**.",
            ["Ir a Consumo", "¿Dónde veo el ahorro estimado?", "¿Qué electrodoméstico gasta más?"],
        )

    # 8. Fuera de alcance o general
    return (
        f"Con gusto te oriento, {nombre_u}. Como copiloto del aplicativo **Ka'i**, puedo ayudarte con:\n\n"
        "1. **Navegación**: indicarte en qué pantalla encontrar consumos, reportes, alertas o simulaciones.\n"
        f"2. **Tus datos**: informarte sobre los {ap.get('total_registrados', 0)} aparatos registrados en {e.get('nombre')} o tu sistema solar.\n"
        "3. **Términos solares**: explicarte qué significan kWh, kWp, baterías, inversores o tarifas de Air-E.\n\n"
        "¿Hay alguna sección del aplicativo o término que desees conocer?",
        sugerencias,
    )


async def responder_chat_asistente(
    db: Session,
    user: User,
    request: ChatAsistenteRequest,
) -> ChatAsistenteResponse:
    """Procesa el mensaje del usuario con Gemini y hace fallback heurístico si no hay conexión."""
    contexto = construir_contexto_usuario(db, user)
    mensaje_usuario = request.mensaje.strip()

    # Si el mensaje es muy corto
    if len(mensaje_usuario) < 2:
        return ChatAsistenteResponse(
            respuesta="Por favor escribe tu duda sobre el aplicativo o sobre energía solar.",
            sugerencias=_sugerencias_por_defecto(contexto.get("entidad", {}).get("tipo", "hogar")),
            origen="heuristico",
        )

    # Contexto en formato texto para el prompt
    u = contexto["usuario"]
    e = contexto["entidad"]
    sol = contexto["solar"]
    ap = contexto["aparatos"]

    datos_instalacion_str = (
        f"- Capacidad solar: {sol['capacidad_paneles_kw']:.1f} kWp en paneles fotovoltaicos.\n"
        f"- Baterías: {sol['capacidad_bateria_kwh']:.1f} kWh de almacenamiento.\n"
        if sol["tiene_paneles"] or sol["tiene_bateria"]
        else "- Instalación solar: Sin paneles ni baterías registrados actualmente.\n"
    )

    aparatos_str = (
        f"- Total aparatos registrados: {ap['total_registrados']}\n"
        f"- Consumo mensual estimado de sus aparatos: {ap['consumo_estimado_kwh_mes']} kWh/mes\n"
        f"- Principales equipos que más consumen: {', '.join(ap['principales']) if ap['principales'] else 'ninguno'}\n"
    )

    pantallas_guia = "\n".join([f"- **{p['nombre']}** ({p['archivo']}): {p['proposito']}" for p in MAPA_NAVEGACION])

    system_instruction = (
        "Eres Ka'i, el copiloto inteligente de energía solar y transición energética para hogares y empresas en La Guajira, Colombia.\n"
        "Tu misión es guiar al usuario en el uso del aplicativo Ka'i, explicar términos técnicos de energía solar y responder preguntas "
        "sobre sus propios aparatos y datos energéticos con máxima precisión, empatía y claridad.\n\n"
        "REGLAS OBLIGATORIAS:\n"
        "1. ALCANCE ESTRICTO: Responde únicamente sobre el aplicativo web Ka'i, navegación entre sus páginas, uso de electrodomésticos, "
        "paneles solares, baterías, facturación de energía (Air-E) y transición energética en La Guajira. Si el usuario pregunta cosas no "
        "relacionadas (fútbol, cocina, tareas escolares, política general), declina cortésmente indicando tu función como copiloto solar.\n"
        "2. ADAPTACIÓN AL PERFIL: El usuario actual es de tipo '" + str(e.get("tipo")) + "'. Si es hogar/residencial, usa lenguaje amigable "
        "sin tecnicismos innecesarios. Si es comercial/pyme, habla en términos de costo, ROI y gestión operativa.\n"
        "3. DATOS REALES DEL USUARIO: Usa los datos provistos en el contexto para responder sobre sus aparatos o su sistema solar. "
        "Nunca inventes datos de otros usuarios ni mezcles información.\n"
        "4. NAVEGACIÓN PRECISA: Indica exactamente a qué pantalla del menú lateral debe ir el usuario para realizar cada acción.\n"
        "5. CONCISIÓN: Mantén tus respuestas claras y directas (2 a 4 párrafos cortos como máximo)."
    )

    historial_str = ""
    for h in request.historial[-6:]:  # últimos 6 mensajes
        rol_tag = "Usuario" if h.role == "user" else "Ka'i"
        historial_str += f"{rol_tag}: {h.content}\n"

    prompt = (
        f"DATOS DEL USUARIO ACTUAL (CONTEXTO SEGURO Y AISLADO):\n"
        f"- Nombre: {u['nombre']} (Rol: {u['rol']})\n"
        f"- Entidad: {e['nombre']} (Tipo: {e['tipo']}, Ubicación: {e['ciudad']}, {e['departamento']})\n"
        f"- Tarifa de energía actual: ${e['tarifa_cop_kwh']:,.0f} COP/kWh\n"
        f"{datos_instalacion_str}"
        f"{aparatos_str}\n"
        f"MAPA DE PANTALLAS DEL APLICATIVO:\n"
        f"{pantallas_guia}\n\n"
        f"HISTORIAL RECIENTE:\n{historial_str}\n"
        f"PREGUNTA DEL USUARIO:\n{mensaje_usuario}\n\n"
        "Responde como Ka'i dirigiéndote al usuario de forma personalizada:"
    )

    # Intento con Gemini
    try:
        respuesta_llm = await obtener_respuesta_gemini(prompt, system_instruction=system_instruction)
        if respuesta_llm and len(respuesta_llm.strip()) > 15:
            sugerencias = _sugerencias_por_defecto(e.get("tipo", "hogar"))
            return ChatAsistenteResponse(
                respuesta=respuesta_llm.strip(),
                sugerencias=sugerencias,
                origen="gemini",
            )
    except Exception as err:
        print(f"[COPILOTO KA'I] Error al consultar Gemini: {err}")

    # Fallback heurístico
    resp_heuristica, sugerencias = generar_respuesta_heuristica(mensaje_usuario, contexto)
    return ChatAsistenteResponse(
        respuesta=resp_heuristica,
        sugerencias=sugerencias,
        origen="heuristico",
    )
