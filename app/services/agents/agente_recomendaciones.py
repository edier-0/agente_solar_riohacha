"""
Agente de Recomendaciones.
Genera recomendaciones en lenguaje natural usando LLM (Gemini).
Si LLM no está disponible, usa plantillas basadas en reglas.
"""
from typing import List, Dict
import json
from sqlalchemy.orm import Session

from app.models.models import Recomendacion, Empresa
from app.services.gemini_client import obtener_respuesta_gemini


class AgenteRecomendaciones:
    """Genera recomendaciones de ahorro energético."""

    SYSTEM_PROMPT = """Eres un experto en eficiencia energética y energía solar en Riohacha, La Guajira, Colombia.
Conoces que:
- Riohacha tiene radiación solar excelente (hasta 7.0 kWh/m²/día).
- La tarifa eléctrica promedio es de 943 COP/kWh.
- Hay apagones frecuentes (~60h/año).
- Las empresas locales (hoteles, hieleras, retail, PYMES) pagan hasta 33% de OpEx en energía.
- El polvo y arena del desierto guajiro reduce la eficiencia de paneles solares (~5-15%).

Fuentes de datos disponibles:
- Open-Meteo (NÚCLEO): GHI/DNI/DHI horarios, pronóstico 16 días, archivo ERA5.
- OpenWeather (COMPLEMENTO): clima actual, alertas, calidad del aire.
- PVGIS (BASELINE OPCIONAL): TMY climatológico de 15+ años.

Genera SIEMPRE recomendaciones en español, cortas (1-2 oraciones), prácticas, accionables y específicas con horarios.
Cada recomendación debe tener un impacto económico estimado claro."""

    async def generar(
        self,
        db: Session,
        empresa: Empresa,
        analisis_solar: Dict,
        analisis_consumo: Dict,
    ) -> List[Recomendacion]:
        """Genera y guarda recomendaciones para una empresa."""
        # 1. Intentar con LLM
        recomendaciones_texto = await self._generar_con_llm(
            empresa, analisis_solar, analisis_consumo
        )
        usado_llm = bool(recomendaciones_texto)

        # 2. Fallback con reglas si LLM no funciona
        if not recomendaciones_texto:
            recomendaciones_texto = self._generar_con_reglas(
                empresa, analisis_solar, analisis_consumo
            )

        # 3. Guardar en BD
        creadas = []
        escenario = empresa.escenario_default or "demo"
        origen = "llm" if usado_llm else "reglas"
        confiabilidad_datos = 80.0 if escenario == "real" else 55.0
        for rec in recomendaciones_texto:
            r = Recomendacion(
                empresa_id=empresa.id,
                texto=rec["texto"],
                tipo=rec.get("tipo", "ahorro"),
                impacto_estimado_cop=rec.get("impacto_cop", 0),
                confianza_pct=rec.get("confianza", 75.0),
                escenario=escenario,
                origen_dato=origen,
                confiabilidad_datos=confiabilidad_datos,
            )
            db.add(r)
            creadas.append(r)
        db.commit()
        for r in creadas:
            db.refresh(r)
        return creadas

    async def _generar_con_llm(
        self,
        empresa: Empresa,
        solar: Dict,
        consumo: Dict,
    ) -> List[Dict]:
        """Llama a Gemini para generar recomendaciones."""
        es_hogar = (empresa.tipo == "hogar")
        desc_tipo = "Hogar / Familia Residencial" if es_hogar else f"empresa (giro: {empresa.tipo or 'PYME'})"
        contexto_adicional = (
            "Como es un Hogar/Residencial, enfócate en hábitos familiares, electrodomésticos del hogar (lavadora, "
            "nevera, aires acondicionados domésticos, luces) y evita términos industriales como 'cargas pesadas', "
            "'procesos productivos', 'picos de demanda de potencia contratada' o 'planta diésel'."
            if es_hogar else
            "Como es un comercio/PYME, enfócate en eficiencia operativa, reducción de picos de potencia, "
            "maquinaria y retorno de inversión."
        )

        prompt = f"""Genera EXACTAMENTE 5 recomendaciones de ahorro energético para el cliente "{empresa.nombre}" (perfil: {desc_tipo}) en Riohacha, La Guajira.
{contexto_adicional}

Datos solares (últimos 30 días):
- Radiación GHI promedio: {solar.get('promedio_ghi', 'N/A')} kWh/m²/día
- Producción solar estimada: {solar.get('produccion_estimada_diaria_kwh', 0)} kWh/día
- Capacidad paneles instalados: {empresa.capacidad_paneles_kw} kW

Datos consumo (últimos 30 días):
- Consumo total: {consumo.get('total_kwh', 0)} kWh
- Promedio diario: {consumo.get('promedio_diario_kwh', 0)} kWh
- Demanda pico: {consumo.get('demanda_pico_kw', 0)} kW
- Anomalías detectadas: {consumo.get('num_anomalias', 0)}
- Tarifa: {empresa.tarifa_kwh} COP/kWh

Responde EXCLUSIVAMENTE con un JSON válido con este formato (sin texto adicional):
{{"recomendaciones": [
  {{"texto": "...", "tipo": "ahorro|redistribucion|contingencia|mantenimiento", "impacto_cop": 50000, "confianza": 85}},
  ...
]}}"""

        respuesta = await obtener_respuesta_gemini(
            prompt=prompt,
            system_instruction=self.SYSTEM_PROMPT,
            model_name="gemini-2.5-flash-lite"
        )

        if not respuesta:
            return []

        # Intentar parsear JSON
        try:
            # Buscar el primer { y último }
            start = respuesta.find("{")
            end = respuesta.rfind("}")
            if start == -1 or end == -1:
                return []
            data = json.loads(respuesta[start : end + 1])
            return data.get("recomendaciones", [])[:5]
        except (json.JSONDecodeError, ValueError):
            return []


    def _generar_con_reglas(
        self,
        empresa: Empresa,
        solar: Dict,
        consumo: Dict,
    ) -> List[Dict]:
        """Recomendaciones basadas en reglas (fallback)."""
        recomendaciones = []
        promedio_kwh = (consumo.get("promedio_diario_kwh") or 0.0) if consumo else 0.0
        promedio_ghi = (solar.get("promedio_ghi") or 0.0) if solar else 0.0
        tarifa = (empresa.tarifa_kwh or 943.0) if empresa else 943.0
        num_anomalias = (consumo.get("num_anomalias") or 0) if consumo else 0
        es_hogar = (empresa and empresa.tipo == "hogar")

        # 1. Aprovechar horario solar pico
        if promedio_ghi > 4.5:
            ahorro = round(promedio_kwh * 0.2 * tarifa, 0)
            texto_rec = (
                "Lave, planche o encienda los electrodomésticos de mayor consumo de su casa entre 10 AM y 2 PM, "
                "aprovechando las horas de máxima radiación solar en Riohacha para reducir lo comprado a Air-E."
                if es_hogar else
                "Concentre operaciones de alto consumo (refrigeración intensa, bombas, procesos) entre 10 AM y 2 PM "
                "cuando la radiación solar es máxima en Riohacha. Puede ahorrar hasta 20% en costos diurnos."
            )
            recomendaciones.append({
                "texto": texto_rec,
                "tipo": "redistribucion",
                "impacto_cop": ahorro,
                "confianza": 85.0,
            })

        # 2. Reducir consumos nocturnos / pico
        if promedio_kwh > 0:
            ahorro = round(promedio_kwh * 0.1 * tarifa, 0)
            texto_rec = (
                "Apague luces y equipos de climatización innecesarios entre 6 PM y 9 PM para disminuir el consumo "
                "acumulado nocturno y fomentar hábitos de ahorro familiar."
                if es_hogar else
                "Reduzca cargas no esenciales entre 6 PM y 9 PM para evitar el pico de demanda y disminuir el cargo por potencia máxima."
            )
            recomendaciones.append({
                "texto": texto_rec,
                "tipo": "redistribucion",
                "impacto_cop": ahorro,
                "confianza": 80.0,
            })

        # 3. Instalación solar
        if empresa and empresa.capacidad_paneles_kw == 0:
            texto_rec = (
                "Instalar un sistema solar residencial recomendado de 2.5 kWp podría cubrir hasta el 50% de su consumo familiar diurno. "
                "Ahorrará dinero directo en cada factura de Air-E."
                if es_hogar else
                f"Instalar 5-10 kW de paneles solares podría cubrir 30-50% de su consumo diario (~{promedio_kwh * 0.4:.0f} kWh/día). ROI estimado: 4-6 años en La Guajira."
            )
            recomendaciones.append({
                "texto": texto_rec,
                "tipo": "ahorro",
                "impacto_cop": round(promedio_kwh * 0.4 * tarifa * 30, 0),
                "confianza": 75.0,
            })

        # 4. Anomalías detectadas
        if num_anomalias > 0:
            texto_rec = (
                f"Se detectaron {num_anomalias} días con consumo inusualmente alto en su casa. "
                "Revise si algún aire acondicionado doméstico se dejó encendido sin termostato, "
                "o si hay fugas de calor por ventanas abiertas."
                if es_hogar else
                f"Se detectaron {num_anomalias} días con consumo anómalo. Revise equipos en operación esos días: "
                "aires acondicionados sin termostato, fugas térmicas o equipos defectuosos."
            )
            recomendaciones.append({
                "texto": texto_rec,
                "tipo": "mantenimiento",
                "impacto_cop": round(promedio_kwh * 0.15 * tarifa, 0),
                "confianza": 70.0,
            })

        # 5. Batería de respaldo
        if empresa and empresa.capacidad_bateria_kwh == 0:
            texto_rec = (
                "Considere equipar su hogar con un banco de baterías básico (ej. 5 kWh). "
                "Evitará que los frecuentes apagones de Riohacha apaguen sus luces y dañen los alimentos de su nevera."
                if es_hogar else
                "Considere instalar un sistema de respaldo con baterías. Riohacha tiene ~60h de apagones al año; con baterías evitaría pérdidas operativas y costos de plantas diésel."
            )
            recomendaciones.append({
                "texto": texto_rec,
                "tipo": "contingencia",
                "impacto_cop": 50000 if es_hogar else 200000,
                "confianza": 70.0,
            })

        return recomendaciones[:5]


agente_recomendaciones = AgenteRecomendaciones()
