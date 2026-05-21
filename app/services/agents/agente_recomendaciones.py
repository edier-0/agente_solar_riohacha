"""
Agente de Recomendaciones.
Genera recomendaciones en lenguaje natural usando LLM (Ollama/Llama 3.2).
Si LLM no está disponible, usa plantillas basadas en reglas.
"""
from typing import List, Dict
import json
from sqlalchemy.orm import Session

from app.models.models import Recomendacion, Empresa
from app.services.ollama_client import ollama_client
from app.services.agents.agente_solar import agente_solar
from app.services.agents.agente_consumo import agente_consumo


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

        # 2. Fallback con reglas si LLM no funciona
        if not recomendaciones_texto:
            recomendaciones_texto = self._generar_con_reglas(
                empresa, analisis_solar, analisis_consumo
            )

        # 3. Guardar en BD
        creadas = []
        for rec in recomendaciones_texto:
            r = Recomendacion(
                empresa_id=empresa.id,
                texto=rec["texto"],
                tipo=rec.get("tipo", "ahorro"),
                impacto_estimado_cop=rec.get("impacto_cop", 0),
                confianza_pct=rec.get("confianza", 75.0),
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
        """Llama a Ollama para generar recomendaciones."""
        if not await ollama_client.is_disponible():
            return []

        prompt = f"""Genera EXACTAMENTE 5 recomendaciones de ahorro energético para la empresa "{empresa.nombre}" (tipo: {empresa.tipo or 'PYME'}) en Riohacha, La Guajira.

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

        respuesta = await ollama_client.generate(
            prompt=prompt,
            system=self.SYSTEM_PROMPT,
            temperature=0.5,
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
        promedio_kwh = consumo.get("promedio_diario_kwh", 0)
        tarifa = empresa.tarifa_kwh

        # 1. Aprovechar horario solar pico
        if solar.get("promedio_ghi", 0) > 4.5:
            ahorro = round(promedio_kwh * 0.2 * tarifa, 0)
            recomendaciones.append({
                "texto": (
                    "Concentre operaciones de alto consumo (refrigeración intensa, "
                    "bombas, procesos) entre 10 AM y 2 PM cuando la radiación solar "
                    "es máxima en Riohacha. Puede ahorrar hasta 20% en costos diurnos."
                ),
                "tipo": "redistribucion",
                "impacto_cop": ahorro,
                "confianza": 85.0,
            })

        # 2. Reducir picos de demanda nocturnos
        if promedio_kwh > 0:
            ahorro = round(promedio_kwh * 0.1 * tarifa, 0)
            recomendaciones.append({
                "texto": (
                    "Reduzca cargas no esenciales entre 6 PM y 9 PM para evitar el "
                    "pico de demanda y disminuir el cargo por potencia máxima."
                ),
                "tipo": "redistribucion",
                "impacto_cop": ahorro,
                "confianza": 80.0,
            })

        # 3. Instalación solar
        if empresa.capacidad_paneles_kw == 0:
            recomendaciones.append({
                "texto": (
                    f"Instalar 5-10 kW de paneles solares podría cubrir 30-50% de su "
                    f"consumo diario (~{promedio_kwh * 0.4:.0f} kWh/día). ROI estimado: 4-6 años en La Guajira."
                ),
                "tipo": "ahorro",
                "impacto_cop": round(promedio_kwh * 0.4 * tarifa * 30, 0),
                "confianza": 75.0,
            })

        # 4. Anomalías detectadas
        if consumo.get("num_anomalias", 0) > 0:
            recomendaciones.append({
                "texto": (
                    f"Se detectaron {consumo['num_anomalias']} días con consumo anómalo. "
                    "Revise equipos en operación esos días: aires acondicionados sin termostato, "
                    "fugas térmicas o equipos defectuosos."
                ),
                "tipo": "mantenimiento",
                "impacto_cop": round(promedio_kwh * 0.15 * tarifa, 0),
                "confianza": 70.0,
            })

        # 5. Batería de respaldo
        if empresa.capacidad_bateria_kwh == 0:
            recomendaciones.append({
                "texto": (
                    "Considere instalar un sistema de respaldo con baterías. "
                    "Riohacha tiene ~60h de apagones al año; con baterías evitaría "
                    "pérdidas operativas y costos de plantas diésel."
                ),
                "tipo": "contingencia",
                "impacto_cop": 200000,
                "confianza": 70.0,
            })

        return recomendaciones[:5]


agente_recomendaciones = AgenteRecomendaciones()
