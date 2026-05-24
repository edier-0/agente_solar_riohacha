"""
Lectura de datasets demo en JSON (sin persistencia en BD).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = ROOT / "scripts" / "demo_data"
CONSUMO_FILE = DEMO_DIR / "consumo_demo.json"
RADIACION_FILE = DEMO_DIR / "radiacion_demo.json"


def _load(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _within_days(fecha_iso: str, days: int) -> bool:
    try:
        fecha = datetime.fromisoformat(fecha_iso)
    except ValueError:
        return False
    return fecha >= datetime.now() - timedelta(days=days)


def get_consumo_demo(days: int = 30) -> List[Dict[str, Any]]:
    rows = [r for r in _load(CONSUMO_FILE) if _within_days(str(r.get("fecha", "")), days)]
    rows.sort(key=lambda x: x.get("fecha", ""), reverse=True)
    return rows


def get_radiacion_demo(days: int = 30) -> List[Dict[str, Any]]:
    rows = [r for r in _load(RADIACION_FILE) if _within_days(str(r.get("fecha", "")), days)]
    rows.sort(key=lambda x: x.get("fecha", ""), reverse=True)
    return rows


def get_demo_empresa() -> Dict[str, Any]:
    return {
        "id": 1,
        "nombre": "Hotel Solar Riohacha (Demo)",
        "tipo": "hotel",
        "direccion": "Av. La Marina #5-15, Riohacha",
        "ciudad": "Riohacha",
        "departamento": "La Guajira",
        "tarifa_kwh": 943.0,
        "capacidad_paneles_kw": 15.0,
        "capacidad_bateria_kwh": 30.0,
        "is_active": True,
        "created_at": datetime.now().isoformat(),
    }
