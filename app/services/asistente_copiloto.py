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

# Mapeo de navegación amigable para el frontend con roles de acceso (sincronizado con PAGE_VISIBILITY)
MAPA_NAVEGACION = [
    {
        "id": "Home",
        "nombre": "Inicio",
        "roles": ("admin", "empresa", "analista"),
        "proposito": "Página principal con resumen del sistema y acceso directo a las herramientas.",
    },
    {
        "id": "Mi_Dia",
        "nombre": "Mi día",
        "roles": ("empresa", "admin"),
        "proposito": "Resumen ejecutivo diario: clima, horas de mayor sol, nivel de batería y consejos rápidos de ahorro.",
    },
    {
        "id": "Mis_Aparatos",
        "nombre": "Mis Aparatos",
        "roles": ("admin", "empresa", "analista"),
        "proposito": "Inventario de electrodomésticos y equipos: consumo detallado en W y kWh/mes, consejos por aparato y agregar nuevos.",
    },
    {
        "id": "Dashboard",
        "nombre": "Panel (Dashboard)",
        "roles": ("admin", "empresa", "analista"),
        "proposito": "Gráficos técnicos de telemetría: curvas de consumo, radiación solar y métricas consolidadas.",
    },
    {
        "id": "Consumo",
        "nombre": "Consumo",
        "roles": ("admin", "empresa", "analista"),
        "proposito": "Registro y consulta de recibos de energía de Air-E, costos acumulados y comparativas históricas.",
    },
    {
        "id": "Recomendaciones_IA",
        "nombre": "Recomendaciones IA",
        "roles": ("admin", "empresa", "analista"),
        "proposito": "Estrategias personalizadas de eficiencia energética y optimización horaria para reducir la factura.",
    },
    {
        "id": "Alertas",
        "nombre": "Alertas",
        "roles": ("admin", "empresa", "analista"),
        "proposito": "Alertas climáticas del municipio: calor extremo, lluvias torrenciales, vientos y riesgo de cortes eléctricos de red.",
    },
    {
        "id": "Predicciones",
        "nombre": "Predicciones",
        "roles": ("admin", "empresa", "analista"),
        "proposito": "Simulador de orquestación autónoma de baterías: autonomía en horas ante apagones según el riesgo de corte.",
    },
    {
        "id": "Reportes",
        "nombre": "Reportes",
        "roles": ("admin", "analista", "empresa"),
        "proposito": "Exportación y descarga de informes ejecutivos e históricos en formatos PDF y Excel.",
    },
    {
        "id": "Datos_Solares",
        "nombre": "Datos solares",
        "roles": ("admin", "analista"),
        "proposito": "Radiación solar histórica y pronósticos climáticos de La Guajira (Open-Meteo, NASA POWER, PVGIS).",
    },
    {
        "id": "Administracion",
        "nombre": "Administración",
        "roles": ("admin",),
        "proposito": "Gestión de usuarios y entidades (solo administrador). Incluye la ficha técnica fotovoltaica en 'Tengo paneles solares'.",
    },
]

# Patrones de sanitización para eliminar cualquier ruta .py residual y devolver el nombre del frontend
PATRONES_ARCHIVOS_A_NOMBRES = [
    (r"(?:pages[/\\])?8_administraci[oó]n\.py", "Administración"),
    (r"(?:pages[/\\])?0_mi_d[ií]a\.py", "Mi día"),
    (r"(?:pages[/\\])?0_mis_aparatos\.py", "Mis Aparatos"),
    (r"(?:pages[/\\])?1_dashboard\.py", "Panel"),
    (r"(?:pages[/\\])?2_consumo\.py", "Consumo"),
    (r"(?:pages[/\\])?3_datos_solares\.py", "Datos solares"),
    (r"(?:pages[/\\])?4_recomendaciones_ia\.py", "Recomendaciones IA"),
    (r"(?:pages[/\\])?5_alertas\.py", "Alertas"),
    (r"(?:pages[/\\])?6_predicciones\.py", "Predicciones"),
    (r"(?:pages[/\\])?7_reportes\.py", "Reportes"),
    (r"\bhome\.py\b", "Inicio"),
]


def limpiar_rutas_archivos(texto: str) -> str:
    """Reemplaza cualquier mención de archivos o rutas .py por el nombre visible del apartado en el frontend."""
    if not texto:
        return ""
    resultado = texto
    for patron, nombre in PATRONES_ARCHIVOS_A_NOMBRES:
        resultado = re.sub(rf"[`'\"]?{patron}[`'\"]?", f"**'{nombre}'**", resultado, flags=re.IGNORECASE)
    # Limpieza de patrones genéricos residuales como 'pages/X_Algo.py', 'X_Algo.py' o cualquier archivo .py
    resultado = re.sub(r"[`'\"]?pages[/\\]\d+_([a-zA-Z_]+)\.py[`'\"]?", r"**'\1'**", resultado, flags=re.IGNORECASE)
    resultado = re.sub(r"[`'\"]?\b\d+_([a-zA-Z_]+)\.py\b[`'\"]?", r"**'\1'**", resultado, flags=re.IGNORECASE)
    resultado = re.sub(r"[`'\"]?\b([a-zA-Z_]+)\.py\b[`'\"]?", r"**'\1'**", resultado, flags=re.IGNORECASE)
    return resultado


def construir_contexto_usuario(db: Session, user: User) -> Dict:
    """Extrae el contexto del usuario autenticado para inyectar en el asistente sin mezclar datos."""
    empresa: Optional[Empresa] = None
    if user.empresa_id:
        empresa = db.query(Empresa).filter(Empresa.id == user.empresa_id).first()

    rol_str = (user.role.value if hasattr(user.role, "value") else str(user.role)).lower()

    # Filtrar apartados según el rol del usuario (sincronizado con PAGE_VISIBILITY de Streamlit)
    apartados_permitidos = [
        {"nombre": p["nombre"], "proposito": p["proposito"]}
        for p in MAPA_NAVEGACION
        if rol_str in p["roles"]
    ]
    apartados_restringidos = [
        {"nombre": p["nombre"], "proposito": p["proposito"], "roles_permitidos": list(p["roles"])}
        for p in MAPA_NAVEGACION
        if rol_str not in p["roles"]
    ]

    contexto = {
        "usuario": {
            "nombre": user.full_name or "Usuario",
            "email": user.email,
            "rol": rol_str,
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
        "navegacion": apartados_permitidos,
        "apartados_restringidos": apartados_restringidos,
        "nombres_permitidos": [p["nombre"] for p in apartados_permitidos],
        "nombres_restringidos": [p["nombre"] for p in apartados_restringidos],
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


def _sugerencias_por_defecto(tipo_entidad: str, rol: str = "empresa") -> List[str]:
    rol_limpio = (rol or "empresa").lower()
    if rol_limpio == "admin":
        return [
            "¿Dónde veo el consumo de mis aparatos?",
            "¿Cómo registro paneles en Administración?",
            "¿Qué significa DoD y kWp?",
            "¿Dónde veo los datos solares y radiación?",
        ]
    elif rol_limpio == "analista":
        return [
            "¿Dónde veo los datos solares de La Guajira?",
            "¿Dónde consulto los reportes de energía?",
            "¿Qué significa kWh y kWp?",
            "¿Cómo simulo la autonomía ante apagones?",
        ]
    return [
        "¿Dónde veo el consumo de mis aparatos?",
        "¿Qué significa kWh y kWp?",
        "¿Cómo prepararme ante un riesgo de corte?",
        "¿Dónde veo mi factura y tarifa de Air-E?",
    ]


def generar_respuesta_heuristica(mensaje: str, ctx: Dict) -> Tuple[str, List[str]]:
    """Motor heurístico de contingencia cuando no hay conexión a internet o no hay GEMINI_API_KEY."""
    m = mensaje.lower().strip()
    u = ctx.get("usuario", {})
    e = ctx.get("entidad", {})
    sol = ctx.get("solar", {})
    ap = ctx.get("aparatos", {})

    nombre_u = u.get("nombre", "amigo")
    rol = str(u.get("rol", "empresa")).lower()
    tipo_ent = e.get("tipo", "hogar")
    es_hogar = tipo_ent == "hogar"

    sugerencias = _sugerencias_por_defecto(tipo_ent, rol)

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

    # 3. Paneles solares y baterías (dónde registrarlos o verlos según rol)
    if any(k in m for k in ("panel", "paneles", "batería", "baterias", "bateria", "inversor", "registrar panel")):
        if sol.get("tiene_paneles") or sol.get("tiene_bateria"):
            info = f"Actualmente tienes registrados **{sol['capacidad_paneles_kw']:.1f} kWp en paneles**"
            if sol.get("tiene_bateria"):
                info += f" y un banco de baterías de **{sol['capacidad_bateria_kwh']:.1f} kWh**."
            else:
                info += " y sin baterías de almacenamiento."
        else:
            info = "Actualmente no tienes paneles ni baterías registrados en tu cuenta."

        if rol == "admin":
            donde = (
                "**¿Dónde se registran o editan?**\n"
                "Como Administrador, puedes gestionar los equipos fotovoltaicos desde el menú **'Administración'** "
                "en la pestaña **'Nueva cuenta / Entidad'**, haciendo clic en el botón verde 👉 **'Tengo paneles solares →'**. "
                "Allí se configura la ficha técnica completa: cantidad de paneles, potencia en W, química de la batería "
                "(Litio LiFePO4, Gel) y capacidad en Ah."
            )
        else:
            donde = (
                "**¿Dónde se registran o editan?**\n"
                "El alta y modificación de fichas técnicas de paneles solares y baterías se gestiona desde el apartado **'Administración'**, "
                "el cual está reservado exclusivamente para usuarios con rol **Administrador**.\n\n"
                "Si necesitas actualizar o agregar nuevos paneles o baterías en tu instalación, solicita al administrador "
                "de la plataforma que actualice la ficha técnica de tu entidad."
            )

        return (
            f"{info}\n\n{donde}",
            ["¿Qué es kWp?", "¿Qué es la profundidad de descarga (DoD)?", "¿Dónde veo la autonomía de batería?"],
        )

    # 4. Fuentes y APIs de Información Climática y Solar (Transparencia para todos los usuarios y perfiles)
    es_pregunta_fuentes_clima = any(
        k in m
        for k in (
            "de donde consulta",
            "de dónde consulta",
            "de donde saca",
            "de dónde saca",
            "de donde saca la informacion",
            "de dónde saca la información",
            "de donde consulta la informacion",
            "de dónde consulta la información",
            "de donde obtiene",
            "de dónde obtiene",
            "de donde proviene",
            "de dónde proviene",
            "fuentes del clima",
            "fuente del clima",
            "fuentes de informacion",
            "fuentes de información",
            "que api",
            "qué api",
            "que apis",
            "qué apis",
            "cuales apis",
            "cuáles apis",
            "origen de los datos",
            "origen del clima",
            "como sabe el clima",
            "cómo sabe el clima",
        )
    ) or (
        any(k in m for k in ("clima", "radiacion", "radiación", "temperatura", "lluvia", "viento"))
        and any(f in m for f in ("de donde", "de dónde", "fuente", "fuentes", "api", "apis", "satelite", "satélite", "origen"))
    )

    if es_pregunta_fuentes_clima:
        texto_apis = (
            "**Fuentes y APIs de Información Climática y Solar en Ka'i:**\n\n"
            "El sistema consulta y cruza datos en tiempo real de 4 fuentes y modelos satelitales oficiales:\n\n"
            "1. 🛰️ **Open-Meteo API:** Pronósticos meteorológicos horarios de alta resolución (temperatura, probabilidad de lluvia, "
            "viento, radiación solar GHI/DNI y niveles de polvo sahariano PM10 en el aire de La Guajira).\n"
            "2. 🚀 **NASA POWER API:** Series satelitales de radiación solar global e irradiancia térmica calibradas para las coordenadas de Fonseca y Riohacha.\n"
            "3. ☀️ **PVGIS (Comisión Europea):** Base de datos científica fotovoltaica del Joint Research Centre para modelar la producción solar y calcular las Horas de Sol Pico (HSP).\n"
            "4. ⚡ **OpenWeatherMap API:** Monitoreo y alertas meteorológicas tempranas de tormentas eléctricas, vientos severos y olas de calor.\n\n"
        )
        if rol in ("admin", "analista"):
            texto_vis = (
                "**¿Dónde puedes consultarlo en el aplicativo?**\n"
                "- En **'Mi día'** y **'Alertas'** ves el impacto diario en tu consumo y avisos de red.\n"
                "- Como tu perfil tiene permisos de **Analista / Administrador**, también tienes habilitado el apartado "
                "**'Datos solares'** en tu menú lateral para comparar las curvas entre Open-Meteo, NASA POWER y PVGIS y revisar históricos."
            )
            sugs_f = ["Ir a Datos solares", "Ver Alertas del clima", "¿Qué significa HSP en radiación?"]
        else:
            texto_vis = (
                "**¿Dónde puedes consultarlo en el aplicativo?**\n"
                "- En el apartado **'Mi día'** ves el resumen diario con las mejores horas de sol y consejos de ahorro para tu hogar o negocio.\n"
                "- En el apartado **'Alertas'** monitoreas los avisos preventivos del clima y posibles riesgos de corte en tu municipio.\n"
                "*(Nota: El módulo técnico 'Datos solares' con comparativas de curvas satelitales avanzadas está reservado para perfiles analistas y administradores).*"
            )
            sugs_f = ["Ir a Mi día", "Ver Alertas del clima", "¿Qué es kWp?"]

        return (f"{texto_apis}{texto_vis}", sugs_f)

    # 5. Datos Solares y Radiación (Control de acceso por rol: solo admin y analista tienen 'Datos solares')
    if any(k in m for k in ("datos solares", "radiacion", "radiación", "pvgis", "nasa power", "hsp", "horas de sol")):
        if rol in ("admin", "analista"):
            return (
                "**Consulta de Datos Solares y Radiación:**\n\n"
                "Tienes acceso al apartado **'Datos solares'** en tu menú lateral. "
                "Allí puedes consultar curvas de radiación global (GHI), radiación directa, difusa y comparar modelos "
                "meteorológicos satelitales (Open-Meteo, NASA POWER y PVGIS) para Fonseca, Riohacha y toda La Guajira.",
                ["Ir a Datos solares", "¿Qué significa HSP en radiación?", "Ver Alertas del clima"],
            )
        else:
            return (
                "**Consulta de Datos Solares y Radiación:**\n\n"
                "Ka'i procesa la radiación y el clima integrando las APIs de **Open-Meteo**, **NASA POWER** y **PVGIS**.\n\n"
                "El apartado especializado **'Datos solares'** (con descarga de modelos satelitales avanzados y comparativas técnicas) "
                "es una herramienta reservada para perfiles de **Analista** y **Administrador**.\n\n"
                "Sin embargo, en tu cuenta puedes consultar las horas de mayor sol y la radiación estimada de hoy en el apartado **'Mi día'**, "
                "o revisar las condiciones y avisos meteorológicos en el apartado **'Alertas'**.",
                ["Ir a Mi día", "Ver Alertas del clima", "¿De dónde consulta el clima?"],
            )

    # 6. Términos energéticos (Glosario)
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

    # 7. Apagones, cortes y orquestación
    if any(k in m for k in ("apagon", "corte", "sin luz", "autonomia", "bateria")):
        return (
            "**Resiliencia ante Apagones:**\n\n"
            "En la sección **'Predicciones'** encontrarás el **Simulador de Orquestación de Baterías**. "
            "Allí puedes simular el nivel de riesgo de corte eléctrico en La Guajira y observar cuántas horas de autonomía "
            "tendría tu instalación según tus electrodomésticos críticos (nevera, iluminación, internet).",
            ["Ir a Predicciones", "Ver Alertas del clima", "¿Cómo proteger mis electrodomésticos?"],
        )

    # 8. Alertas del clima
    if any(k in m for k in ("alerta", "clima", "lluvia", "calor", "viento", "polvo")):
        return (
            f"En la sección **'Alertas'** monitoreamos el clima en tiempo real para **{e.get('ciudad', 'La Guajira')}** "
            "a través de las APIs de **Open-Meteo** y **OpenWeatherMap**. "
            "El sistema evalúa calor extremo, tormentas que puedan causar cortes de luz y niveles de polvo PM10 en el aire "
            "que requieran limpiar tus paneles para que no pierdan producción.",
            ["Ir a Alertas", "¿De dónde consulta el clima?", "¿Cómo afecta el polvo a los paneles?"],
        )

    # 9. Recibos y facturación
    if any(k in m for k in ("factura", "recibo", "aire", "air-e", "tarifa", "costo")):
        return (
            f"En la sección **'Consumo'** puedes consultar el historial de facturación de tu energía y registrar recibos de Air-E. "
            f"Tu tarifa configurada es de **${e.get('tarifa_cop_kwh', 943):,.0f} COP/kWh**.",
            ["Ir a Consumo", "¿Dónde veo el ahorro estimado?", "¿Qué electrodoméstico gasta más?"],
        )

    # 10. Fuera de alcance o general
    permitidos_str = ", ".join([f"**'{p['nombre']}'**" for p in ctx.get("navegacion", [])])
    return (
        f"Con gusto te oriento, {nombre_u}. Como copiloto del aplicativo **Ka'i**, puedo ayudarte con:\n\n"
        f"1. **Navegación**: indicarte en qué pantalla encontrar consumos, reportes, alertas o simulaciones.\n"
        f"   (Apartados disponibles en tu menú: {permitidos_str})\n"
        f"2. **Tus datos**: informarte sobre los {ap.get('total_registrados', 0)} aparatos registrados en {e.get('nombre')} o tu sistema solar.\n"
        "3. **Términos solares**: explicarte qué significan kWh, kWp, baterías, inversores o tarifas de Air-E.\n"
        "4. **Clima y APIs**: explicarte las fuentes oficiales (Open-Meteo, NASA POWER, PVGIS, OpenWeatherMap) que alimentan la plataforma.\n\n"
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
            sugerencias=_sugerencias_por_defecto(
                contexto.get("entidad", {}).get("tipo", "hogar"),
                contexto.get("usuario", {}).get("rol", "empresa"),
            ),
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

    pantallas_guia = "\n".join([f"- Menú **'{p['nombre']}'**: {p['proposito']}" for p in contexto.get("navegacion", [])])
    restringidas_lista = contexto.get("nombres_restringidos", [])
    restringidas_str = ", ".join(restringidas_lista) if restringidas_lista else "Ninguno (tiene acceso a todos los apartados)"

    system_instruction = (
        "Eres Ka'i, el copiloto inteligente de energía solar y transición energética para hogares y empresas en La Guajira, Colombia.\n"
        "Tu misión es guiar al usuario en el uso del aplicativo Ka'i, explicar términos técnicos de energía solar y responder preguntas "
        "sobre sus propios aparatos y datos energéticos con máxima precisión, empatía y claridad.\n\n"
        "REGLAS OBLIGATORIAS:\n"
        "1. ALCANCE ESTRICTO: Responde únicamente sobre el aplicativo web Ka'i, navegación entre sus pantallas, uso de electrodomésticos, "
        "paneles solares, baterías, facturación de energía (Air-E) y transición energética en La Guajira. Si el usuario pregunta cosas no "
        "relacionadas (fútbol, cocina, tareas escolares, política general), declina cortésmente indicando tu función como copiloto solar.\n"
        "2. ADAPTACIÓN AL PERFIL: El usuario actual es de tipo '" + str(e.get("tipo")) + "'. Si es hogar/residencial, usa lenguaje amigable "
        "sin tecnicismos innecesarios. Si es comercial/pyme, habla en términos de costo, ROI y gestión operativa.\n"
        "3. DATOS REALES DEL USUARIO: Usa los datos provistos en el contexto para responder sobre sus aparatos o su sistema solar. "
        "Nunca inventes datos de otros usuarios ni mezcles información.\n"
        "4. NAVEGACIÓN EN EL FRONTEND (MUY IMPORTANTE): Al responder sobre en qué pantalla o lugar encontrar cualquier cosa, "
        "refiérete SIEMPRE al nombre del apartado donde el usuario puede verlo en la interfaz (por ejemplo: 'en el apartado **Mis Aparatos**', "
        "'en el apartado **Mi día**', 'en el apartado **Consumo**', 'en el apartado **Alertas**', "
        "'en el apartado **Predicciones**', 'en el apartado **Reportes**'). ESTÁ COMPLETAMENTE PROHIBIDO devolver nombres de archivos de código fuente, "
        "rutas de carpetas o extensiones técnicas, tales como 'pages/8_Administracion.py', 'pages/0_Mis_Aparatos.py', 'Home.py' o cualquier archivo con extensión '.py'. "
        "El usuario es una persona navegando en su navegador web, indícale siempre el nombre del apartado visible.\n"
        "5. CONCISIÓN: Mantén tus respuestas claras y directas (2 a 4 párrafos cortos como máximo).\n"
        "6. CONTROL ESTRICTO DE PERMISOS POR ROL: "
        f"El usuario actual tiene rol '{u['rol']}'. "
        f"SUS APARTADOS VISIBLES Y PERMITIDOS SON: {', '.join(contexto.get('nombres_permitidos', []))}.\n"
        f"SUS APARTADOS RESTRINGIDOS / NO DISPONIBLES SON: {restringidas_str}.\n"
        "NUNCA le digas al usuario que navegue a un apartado restringido como si estuviera en su menú lateral. "
        "Si el usuario pregunta por una función de un apartado al que NO tiene acceso (por ejemplo, si un usuario con rol 'empresa' "
        "pregunta por el apartado 'Datos solares' o 'Administración'):\n"
        "- Aclárale cortésmente que dicho apartado está reservado para perfiles Analista o Administrador.\n"
        "- Oriéntalo de inmediato hacia las pantallas a las que SÍ tiene acceso (ej. ver horas de sol en 'Mi día' o 'Alertas', "
        "o contactar al Administrador para cambios en su ficha técnica).\n"
        "7. TRANSPARENCIA EN FUENTES Y APIS DEL CLIMA (APLICA A TODOS LOS ROLES): "
        "Si el usuario (sea 'empresa', 'analista' o 'admin') pregunta de dónde se consulta la información del clima o radiación, "
        "MENCIONA SIEMPRE las 4 APIs y modelos satelitales que alimentan a Ka'i: Open-Meteo (pronósticos horarios y radiación en tiempo real), "
        "NASA POWER (datos satelitales de radiación solar global), PVGIS de la Comisión Europea (base científica para Horas de Sol Pico - HSP) "
        "y OpenWeatherMap (alertas de tormentas y calor extremo). Explica que estos datos alimentan los pronósticos en 'Mi día' y 'Alertas' "
        "para todos los usuarios, mientras que las curvas analíticas completas se visualizan en 'Datos solares' para perfiles técnicos (Analista/Admin)."
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
        f"APARTADOS DISPONIBLES EN EL MENÚ DEL USUARIO (Rol: {u['rol']}):\n"
        f"{pantallas_guia}\n\n"
        f"APARTADOS RESTRINGIDOS PARA SU ROL:\n"
        f"- {restringidas_str}\n\n"
        f"HISTORIAL RECIENTE:\n{historial_str}\n"
        f"PREGUNTA DEL USUARIO:\n{mensaje_usuario}\n\n"
        "Responde como Ka'i dirigiéndote al usuario de forma personalizada:"
    )

    # Intento con Gemini
    try:
        respuesta_llm = await obtener_respuesta_gemini(prompt, system_instruction=system_instruction)
        if respuesta_llm and len(respuesta_llm.strip()) > 15:
            sugerencias = _sugerencias_por_defecto(e.get("tipo", "hogar"), u.get("rol", "empresa"))
            limpia = limpiar_rutas_archivos(respuesta_llm.strip())
            return ChatAsistenteResponse(
                respuesta=limpia,
                sugerencias=sugerencias,
                origen="gemini",
            )
    except Exception as err:
        print(f"[COPILOTO KA'I] Error al consultar Gemini: {err}")

    # Fallback heurístico
    resp_heuristica, sugerencias = generar_respuesta_heuristica(mensaje_usuario, contexto)
    return ChatAsistenteResponse(
        respuesta=limpiar_rutas_archivos(resp_heuristica),
        sugerencias=sugerencias,
        origen="heuristico",
    )
