"""Normalisation des mesures capteurs, quel que soit l'emetteur.

Formats acceptes (memes valeurs, noms differents selon la brique) :
  firmware ESP8266 / IA : {"temperature", "humidity", "gas", "pir"}       topic sentinel/<id>/sensors
  simulateur infra      : {"temperature", "humidite", "niveau_gaz", "presence"}  topic fortex/capteurs/mesures
  dashboard (contrat)   : {"temp", "hum", "gas", "pir"}
"""

from __future__ import annotations

ALIASES = {
    "temperature": ("temperature", "temp", "temperature_c"),
    "humidity": ("humidity", "hum", "humidite", "humidite_pct"),
    "gas": ("gas", "niveau_gaz", "gaz"),
    "pir": ("pir", "presence", "presence_detectee"),
}


def _first(payload: dict, keys: tuple[str, ...]):
    for key in keys:
        if payload.get(key) is not None:
            return payload[key]
    return None


def normalize(payload: dict) -> dict | None:
    """-> {"temperature", "humidity", "gas", "pir"} (floats, pir 0/1), ou None si incomplet / invalide."""
    if not isinstance(payload, dict):
        return None
    try:
        values = {name: _first(payload, keys) for name, keys in ALIASES.items()}
        reading = {name: float(values[name]) for name in ("temperature", "humidity", "gas")
                   if values[name] is not None}
        reading["pir"] = int(bool(values["pir"]))
    except (TypeError, ValueError):
        return None
    return reading if len(reading) == 4 else None


def topics(value: str) -> list[str]:
    """"a,b" -> ["a", "b"] : plusieurs topics separes par des virgules."""
    return [t.strip() for t in value.split(",") if t.strip()]
