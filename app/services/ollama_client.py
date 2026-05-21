"""
Cliente Ollama para LLM local (Llama 3.2).
Si Ollama no está disponible, usa fallback con plantillas predefinidas.
"""
import httpx
from typing import Optional, Dict
from app.core.config import get_settings

settings = get_settings()


class OllamaClient:
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self._disponible: Optional[bool] = None

    async def is_disponible(self) -> bool:
        """Verifica si Ollama está corriendo."""
        if self._disponible is not None:
            return self._disponible
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                self._disponible = resp.status_code == 200
        except Exception:
            self._disponible = False
        return self._disponible

    async def generate(self, prompt: str, system: str = "", temperature: float = 0.7) -> str:
        """Genera texto con el LLM."""
        if not await self.is_disponible():
            return ""

        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system or "Eres un asistente experto en eficiencia energética y energía solar en Colombia.",
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 512,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(f"{self.base_url}/api/generate", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("response", "").strip()
        except Exception:
            return ""

    async def generar_resumen_diario(
        self,
        empresa_nombre: str,
        empresa_tipo: str,
        resumen: Dict,
    ) -> str:
        """
        Genera un párrafo personalizado en lenguaje natural para la vista 'simple'.
        Si Ollama no está disponible, devuelve un resumen armado con plantillas.
        """
        tarjetas = resumen.get("tarjetas", {})
        score = resumen.get("score_global", {})

        # ----- Fallback determinista (sin LLM) -----
        if not await self.is_disponible():
            return self._fallback_resumen(empresa_nombre, score, tarjetas)

        # ----- Vía LLM -----
        contexto = "\n".join([
            f"- {nombre}: {t.get('titulo')} — {t.get('mensaje')}"
            for nombre, t in tarjetas.items()
        ])

        system = (
            "Eres un asistente energético amable que habla con dueños de pequeñas empresas en Riohacha, "
            "La Guajira. Hablas en español claro, sin tecnicismos, en máximo 4 oraciones cortas. "
            "Usas el saludo según la hora si conoces el contexto, y siempre cierras con una acción concreta."
        )

        prompt = (
            f"Empresa: {empresa_nombre} (tipo: {empresa_tipo or 'PYME'})\n"
            f"Estado general del día: {score.get('titulo', 'Día energético')}\n\n"
            f"Métricas del día (ya traducidas):\n{contexto}\n\n"
            "Redacta un resumen amigable en máximo 4 oraciones, sin listas, sin números crudos extra, "
            "personalizado para el tipo de negocio. Empieza con un saludo. Termina con UNA acción concreta."
        )

        respuesta = await self.generate(prompt=prompt, system=system, temperature=0.6)
        if not respuesta:
            return self._fallback_resumen(empresa_nombre, score, tarjetas)
        return respuesta

    @staticmethod
    def _fallback_resumen(empresa_nombre: str, score: Dict, tarjetas: Dict) -> str:
        """Resumen plantilla cuando Ollama no responde."""
        partes = [f"Hola {empresa_nombre}. {score.get('titulo', 'Aquí va tu resumen del día')}."]
        dia_solar = tarjetas.get("dia_solar", {})
        consumo = tarjetas.get("consumo", {})
        riesgo = tarjetas.get("riesgo_apagon", {})

        if dia_solar.get("mensaje"):
            partes.append(dia_solar["mensaje"])
        if consumo.get("mensaje"):
            partes.append(consumo["mensaje"])
        if riesgo.get("nivel") in ("amarillo", "rojo") and riesgo.get("mensaje"):
            partes.append(riesgo["mensaje"])

        # Acción al final
        accion = None
        for clave in ("riesgo_apagon", "consumo", "produccion", "dia_solar", "aire", "bateria"):
            t = tarjetas.get(clave, {})
            if t.get("accion"):
                accion = t["accion"]
                break
        if accion:
            partes.append(f"Acción sugerida: {accion}.")

        return " ".join(partes)


ollama_client = OllamaClient()
