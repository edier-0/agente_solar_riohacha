"""
Servicio OpenWeather API.
Obtiene pronóstico meteorológico y datos actuales para Riohacha.
"""
import httpx
from typing import Dict, List, Optional
from datetime import datetime
from app.core.config import get_settings

settings = get_settings()


class OpenWeatherService:
    def __init__(self):
        self.base_url = settings.OPENWEATHER_BASE_URL
        self.api_key = settings.OPENWEATHER_API_KEY
        self.lat = settings.RIOHACHA_LAT
        self.lon = settings.RIOHACHA_LON

    async def get_current_weather(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
    ) -> Dict:
        """Clima actual."""
        if not self.api_key:
            # Fallback con datos sintéticos si no hay API key
            return self._synthetic_current()

        params = {
            "lat": lat or self.lat,
            "lon": lon or self.lon,
            "appid": self.api_key,
            "units": "metric",
            "lang": "es",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(f"{self.base_url}/weather", params=params)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError:
                return self._synthetic_current()

        return {
            "fecha": datetime.now(),
            "temperatura": data.get("main", {}).get("temp"),
            "humedad": data.get("main", {}).get("humidity"),
            "nubosidad": data.get("clouds", {}).get("all"),
            "descripcion": data.get("weather", [{}])[0].get("description"),
            "viento_kmh": data.get("wind", {}).get("speed", 0) * 3.6,
            "fuente": "openweather",
        }

    async def get_forecast(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
    ) -> List[Dict]:
        """Pronóstico 5 días / 3h."""
        if not self.api_key:
            return self._synthetic_forecast()

        params = {
            "lat": lat or self.lat,
            "lon": lon or self.lon,
            "appid": self.api_key,
            "units": "metric",
            "lang": "es",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(f"{self.base_url}/forecast", params=params)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError:
                return self._synthetic_forecast()

        results = []
        for item in data.get("list", []):
            results.append({
                "fecha": datetime.fromtimestamp(item["dt"]),
                "temperatura": item.get("main", {}).get("temp"),
                "humedad": item.get("main", {}).get("humidity"),
                "nubosidad": item.get("clouds", {}).get("all"),
                "descripcion": item.get("weather", [{}])[0].get("description"),
                "viento_kmh": item.get("wind", {}).get("speed", 0) * 3.6,
            })
        return results

    def _synthetic_current(self) -> Dict:
        """Datos sintéticos cuando no hay API key configurada."""
        hour = datetime.now().hour
        # Riohacha: clima cálido, soleado típicamente
        return {
            "fecha": datetime.now(),
            "temperatura": 30.0 if 10 <= hour <= 16 else 26.0,
            "humedad": 65,
            "nubosidad": 20 if 10 <= hour <= 16 else 35,
            "descripcion": "soleado" if 8 <= hour <= 17 else "despejado",
            "viento_kmh": 18.0,
            "fuente": "synthetic",
        }

    def _synthetic_forecast(self) -> List[Dict]:
        """Pronóstico sintético basado en perfil climático de Riohacha."""
        from datetime import timedelta
        now = datetime.now()
        results = []
        for h in range(0, 120, 3):  # 5 días, cada 3h
            future = now + timedelta(hours=h)
            hour = future.hour
            results.append({
                "fecha": future,
                "temperatura": 30.0 if 10 <= hour <= 16 else 26.0,
                "humedad": 65,
                "nubosidad": 20 if 10 <= hour <= 16 else 35,
                "descripcion": "soleado",
                "viento_kmh": 18.0,
            })
        return results


openweather_service = OpenWeatherService()
