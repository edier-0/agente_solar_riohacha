"""
Servicio Open-Meteo (NÚCLEO PRINCIPAL).

Open-Meteo es la fuente principal del sistema porque ofrece:
- GHI / DNI / DHI horarios y diarios sin API key (gratis).
- Pronóstico hasta 16 días.
- Archivo histórico (ERA5) hasta 80+ años atrás.
- Calidad del aire (PM10/PM2.5) — relevante para Riohacha por polvo del desierto.

Documentación: https://open-meteo.com/en/docs
"""
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from app.core.config import get_settings

settings = get_settings()


class OpenMeteoService:
    """Cliente Open-Meteo para datos solares, meteorológicos y de calidad del aire."""

    # Variables horarias para forecast/archive
    HOURLY_VARS = ",".join([
        "temperature_2m",
        "relative_humidity_2m",
        "cloud_cover",
        "cloud_cover_low",
        "cloud_cover_mid",
        "cloud_cover_high",
        "wind_speed_10m",
        "shortwave_radiation",      # GHI (W/m²)
        "direct_normal_irradiance", # DNI (W/m²)
        "diffuse_radiation",        # DHI (W/m²)
        "precipitation",
    ])

    DAILY_VARS = ",".join([
        "temperature_2m_max",
        "temperature_2m_min",
        "shortwave_radiation_sum",  # GHI total diario (MJ/m²)
        "precipitation_sum",
        "wind_speed_10m_max",
    ])

    AIR_QUALITY_VARS = ",".join([
        "pm10",
        "pm2_5",
        "dust",
        "uv_index",
    ])

    def __init__(self):
        self.forecast_url = settings.OPENMETEO_FORECAST_URL
        self.archive_url = settings.OPENMETEO_ARCHIVE_URL
        self.air_quality_url = settings.OPENMETEO_AIR_QUALITY_URL
        self.lat = settings.RIOHACHA_LAT
        self.lon = settings.RIOHACHA_LON

    # ------------------------------------------------------------------ #
    # FORECAST
    # ------------------------------------------------------------------ #
    async def get_forecast_horario(
        self,
        days: int = 7,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
    ) -> List[Dict]:
        """Pronóstico horario con radiación solar (GHI/DNI/DHI)."""
        params = {
            "latitude": lat or self.lat,
            "longitude": lon or self.lon,
            "hourly": self.HOURLY_VARS,
            "forecast_days": min(max(days, 1), 16),
            "timezone": "America/Bogota",
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                resp = await client.get(self.forecast_url, params=params)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError:
                return self._synthetic_forecast_horario(days)

        return self._parse_hourly(data)

    async def get_forecast_diario(
        self,
        days: int = 7,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
    ) -> List[Dict]:
        """Pronóstico diario con radiación solar acumulada."""
        params = {
            "latitude": lat or self.lat,
            "longitude": lon or self.lon,
            "daily": self.DAILY_VARS,
            "forecast_days": min(max(days, 1), 16),
            "timezone": "America/Bogota",
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                resp = await client.get(self.forecast_url, params=params)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError:
                return self._synthetic_forecast_diario(days)

        return self._parse_daily(data)

    # ------------------------------------------------------------------ #
    # ARCHIVE (HISTÓRICO ERA5)
    # ------------------------------------------------------------------ #
    async def get_historico(
        self,
        start_date: str,
        end_date: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
    ) -> List[Dict]:
        """
        Histórico diario desde ERA5.
        Fechas formato: YYYY-MM-DD
        """
        params = {
            "latitude": lat or self.lat,
            "longitude": lon or self.lon,
            "start_date": start_date,
            "end_date": end_date,
            "daily": self.DAILY_VARS,
            "timezone": "America/Bogota",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(self.archive_url, params=params)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError as e:
                raise RuntimeError(f"Error consultando Open-Meteo Archive: {e}")

        return self._parse_daily(data)

    async def get_ultimos_dias(self, days: int = 30) -> List[Dict]:
        """Histórico de los últimos N días (Open-Meteo archive tiene ~5 días delay)."""
        end = datetime.now() - timedelta(days=6)
        start = end - timedelta(days=days)
        return await self.get_historico(
            start_date=start.strftime("%Y-%m-%d"),
            end_date=end.strftime("%Y-%m-%d"),
        )

    # ------------------------------------------------------------------ #
    # CALIDAD DEL AIRE (importante en La Guajira por polvo)
    # ------------------------------------------------------------------ #
    async def get_calidad_aire(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
    ) -> Dict:
        """Calidad del aire actual + pronóstico (afecta eficiencia de paneles)."""
        params = {
            "latitude": lat or self.lat,
            "longitude": lon or self.lon,
            "hourly": self.AIR_QUALITY_VARS,
            "forecast_days": 3,
            "timezone": "America/Bogota",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(self.air_quality_url, params=params)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError:
                return {"disponible": False, "datos": []}

        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        pm10 = hourly.get("pm10", [])
        pm25 = hourly.get("pm2_5", [])
        dust = hourly.get("dust", [])
        uv = hourly.get("uv_index", [])

        registros = []
        for i, t in enumerate(times):
            registros.append({
                "fecha": t,
                "pm10": pm10[i] if i < len(pm10) else None,
                "pm2_5": pm25[i] if i < len(pm25) else None,
                "polvo": dust[i] if i < len(dust) else None,
                "uv_index": uv[i] if i < len(uv) else None,
            })
        return {"disponible": True, "datos": registros}

    # ------------------------------------------------------------------ #
    # PARSERS
    # ------------------------------------------------------------------ #
    def _parse_hourly(self, data: Dict) -> List[Dict]:
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        results = []
        for i, t in enumerate(times):
            try:
                fecha = datetime.fromisoformat(t)
            except ValueError:
                continue
            ghi_w = self._safe(hourly, "shortwave_radiation", i)
            dni_w = self._safe(hourly, "direct_normal_irradiance", i)
            dhi_w = self._safe(hourly, "diffuse_radiation", i)
            results.append({
                "fecha": fecha,
                "temperatura": self._safe(hourly, "temperature_2m", i),
                "humedad": self._safe(hourly, "relative_humidity_2m", i),
                "nubosidad": self._safe(hourly, "cloud_cover", i),
                "nubosidad_baja": self._safe(hourly, "cloud_cover_low", i),
                "nubosidad_media": self._safe(hourly, "cloud_cover_mid", i),
                "nubosidad_alta": self._safe(hourly, "cloud_cover_high", i),
                "viento_kmh": self._mul(self._safe(hourly, "wind_speed_10m", i), 3.6),
                # Convertir W/m² (potencia instantánea) a kWh/m² aprox dividiendo /1000
                "ghi_w_m2": ghi_w,
                "dni_w_m2": dni_w,
                "dhi_w_m2": dhi_w,
                "precipitacion_mm": self._safe(hourly, "precipitation", i),
                "fuente": "open_meteo",
            })
        return results

    def _parse_daily(self, data: Dict) -> List[Dict]:
        daily = data.get("daily", {})
        times = daily.get("time", [])
        results = []
        for i, t in enumerate(times):
            try:
                fecha = datetime.fromisoformat(t)
            except ValueError:
                continue
            # shortwave_radiation_sum llega en MJ/m²; convertir a kWh/m² (÷ 3.6)
            ghi_mj = self._safe(daily, "shortwave_radiation_sum", i)
            ghi_kwh = round(ghi_mj / 3.6, 3) if ghi_mj is not None else None
            t_max = self._safe(daily, "temperature_2m_max", i)
            t_min = self._safe(daily, "temperature_2m_min", i)
            t_avg = (
                round((t_max + t_min) / 2, 2)
                if t_max is not None and t_min is not None
                else None
            )
            results.append({
                "fecha": fecha,
                "ghi": ghi_kwh,             # kWh/m²/día (compatible con modelo)
                "dni": None,                # archive diario no expone DNI; usar horario para detalle
                "dhi": None,
                "temperatura": t_avg,
                "temperatura_max": t_max,
                "temperatura_min": t_min,
                "nubosidad": None,
                "precipitacion_mm": self._safe(daily, "precipitation_sum", i),
                "viento_kmh_max": self._mul(self._safe(daily, "wind_speed_10m_max", i), 3.6),
                "fuente": "open_meteo",
                "latitud": self.lat,
                "longitud": self.lon,
            })
        return results

    @staticmethod
    def _safe(d: Dict, key: str, i: int):
        arr = d.get(key) or []
        return arr[i] if i < len(arr) else None

    @staticmethod
    def _mul(value, factor):
        return round(value * factor, 2) if value is not None else None

    # ------------------------------------------------------------------ #
    # FALLBACKS
    # ------------------------------------------------------------------ #
    def _synthetic_forecast_horario(self, days: int) -> List[Dict]:
        results = []
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        for h in range(0, days * 24):
            f = now + timedelta(hours=h)
            hour = f.hour
            soleado = 8 <= hour <= 17
            results.append({
                "fecha": f,
                "temperatura": 30.0 if soleado else 26.0,
                "humedad": 65,
                "nubosidad": 20 if soleado else 35,
                "nubosidad_baja": 10,
                "nubosidad_media": 5,
                "nubosidad_alta": 5,
                "viento_kmh": 18.0,
                "ghi_w_m2": 800 if soleado else 0,
                "dni_w_m2": 700 if soleado else 0,
                "dhi_w_m2": 100 if soleado else 0,
                "precipitacion_mm": 0,
                "fuente": "synthetic",
            })
        return results

    def _synthetic_forecast_diario(self, days: int) -> List[Dict]:
        results = []
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        for d in range(days):
            f = today + timedelta(days=d)
            results.append({
                "fecha": f,
                "ghi": 5.8,
                "dni": None,
                "dhi": None,
                "temperatura": 28.0,
                "temperatura_max": 32.0,
                "temperatura_min": 24.0,
                "nubosidad": None,
                "precipitacion_mm": 0,
                "viento_kmh_max": 25.0,
                "fuente": "synthetic",
                "latitud": self.lat,
                "longitud": self.lon,
            })
        return results


openmeteo_service = OpenMeteoService()
