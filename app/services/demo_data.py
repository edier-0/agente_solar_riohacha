"""
Lectura de datasets demo en JSON (sin persistencia en BD).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = ROOT / "scripts" / "demo_data"
CONSUMO_FILE = DEMO_DIR / "consumo_demo.json"
RADIACION_FILE = DEMO_DIR / "radiacion_demo.json"
DEMO_EMPRESA_ID = 1


def _write(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def _load(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _ensure_ids(rows: List[Dict[str, Any]], path: Path) -> List[Dict[str, Any]]:
    max_id = max((r.get("id") for r in rows if isinstance(r.get("id"), int)), default=99999)
    next_id = max(max_id + 1, 100000)
    updated = False
    for row in rows:
        if row.get("id") is None:
            row["id"] = next_id
            next_id += 1
            updated = True
        if path == CONSUMO_FILE and row.get("empresa_id") is None:
            row["empresa_id"] = DEMO_EMPRESA_ID
            updated = True
    if updated:
        _write(path, rows)
    return rows


def _serialize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(row.get("fecha"), datetime):
        row["fecha"] = row["fecha"].isoformat()
    return row


def _within_days(fecha_iso: str, days: int) -> bool:
    try:
        fecha = datetime.fromisoformat(fecha_iso)
    except ValueError:
        return False
    return fecha >= datetime.now() - timedelta(days=days)


def _find_record(rows: List[Dict[str, Any]], record_id: int) -> Optional[Dict[str, Any]]:
    return next((r for r in rows if int(r.get("id", -1)) == record_id), None)


def get_consumo_demo(days: int = 30) -> List[Dict[str, Any]]:
    rows = _ensure_ids(_load(CONSUMO_FILE), CONSUMO_FILE)
    rows = [r for r in rows if _within_days(str(r.get("fecha", "")), days)]
    rows.sort(key=lambda x: x.get("fecha", ""), reverse=True)
    return rows


def get_radiacion_demo(days: int = 30) -> List[Dict[str, Any]]:
    rows = _ensure_ids(_load(RADIACION_FILE), RADIACION_FILE)
    rows = [r for r in rows if _within_days(str(r.get("fecha", "")), days)]
    rows.sort(key=lambda x: x.get("fecha", ""), reverse=True)
    return rows


def save_consumo_demo(data: Dict[str, Any]) -> Dict[str, Any]:
    rows = _ensure_ids(_load(CONSUMO_FILE), CONSUMO_FILE)
    record = {**data}
    record["empresa_id"] = DEMO_EMPRESA_ID
    record["escenario"] = "demo"
    record["origen_dato"] = "json_demo"
    record["confiabilidad"] = record.get("confiabilidad", 50.0)
    record = _serialize_row(record)
    max_id = max((r.get("id") for r in rows if isinstance(r.get("id"), int)), default=99999)
    record["id"] = max(max_id + 1, 100000)
    rows.insert(0, record)
    _write(CONSUMO_FILE, rows)
    return record


def update_consumo_demo(consumo_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rows = _ensure_ids(_load(CONSUMO_FILE), CONSUMO_FILE)
    record = _find_record(rows, consumo_id)
    if record is None:
        return None
    for key, value in updates.items():
        if value is None:
            continue
        if key == "fecha" and isinstance(value, datetime):
            record[key] = value.isoformat()
        else:
            record[key] = value
    _write(CONSUMO_FILE, rows)
    return record


def delete_consumo_demo(consumo_id: int) -> bool:
    rows = _ensure_ids(_load(CONSUMO_FILE), CONSUMO_FILE)
    remaining = [r for r in rows if int(r.get("id", -1)) != consumo_id]
    if len(remaining) == len(rows):
        return False
    _write(CONSUMO_FILE, remaining)
    return True


def save_radiacion_demo(data: Dict[str, Any]) -> Dict[str, Any]:
    rows = _ensure_ids(_load(RADIACION_FILE), RADIACION_FILE)
    record = {**data}
    record["escenario"] = "demo"
    record["origen_dato"] = record.get("origen_dato", "json_demo")
    record["confiabilidad"] = record.get("confiabilidad", 35.0)
    record = _serialize_row(record)
    max_id = max((r.get("id") for r in rows if isinstance(r.get("id"), int)), default=99999)
    record["id"] = max(max_id + 1, 100000)
    rows.insert(0, record)
    _write(RADIACION_FILE, rows)
    return record


def update_radiacion_demo(radiacion_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rows = _ensure_ids(_load(RADIACION_FILE), RADIACION_FILE)
    record = _find_record(rows, radiacion_id)
    if record is None:
        return None
    for key, value in updates.items():
        if value is None:
            continue
        if key == "fecha" and isinstance(value, datetime):
            record[key] = value.isoformat()
        else:
            record[key] = value
    _write(RADIACION_FILE, rows)
    return record


def delete_radiacion_demo(radiacion_id: int) -> bool:
    rows = _ensure_ids(_load(RADIACION_FILE), RADIACION_FILE)
    remaining = [r for r in rows if int(r.get("id", -1)) != radiacion_id]
    if len(remaining) == len(rows):
        return False
    _write(RADIACION_FILE, remaining)
    return True


def get_demo_empresa() -> Dict[str, Any]:
    return {
        "id": DEMO_EMPRESA_ID,
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
