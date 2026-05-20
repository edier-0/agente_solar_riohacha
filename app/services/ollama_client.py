"""
Cliente Ollama para LLM local (Llama 3.2).
Si Ollama no está disponible, usa fallback con plantillas predefinidas.
"""
import httpx
from typing import Optional
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


ollama_client = OllamaClient()
