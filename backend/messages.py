"""Conversion des messages vers le contrat du dashboard (Fortexworkshop/dev).

Contrat du dashboard (src/data/simulator.js) :
  { type: 'reading', ts, temp, hum, gas, pir }
  { type: 'alert', ts, device_id, kind, value, unit, level, message }
  { type: 'command-ack', ts, cmd: { actuator, state } }
"""

from __future__ import annotations

import time
from datetime import datetime


def now_ms() -> int:
    return int(time.time() * 1000)


def _ts(value) -> int:
    if isinstance(value, datetime):
        return int(value.timestamp() * 1000)
    if isinstance(value, str):
        try:
            return int(datetime.fromisoformat(value).timestamp() * 1000)
        except ValueError:
            pass
    return now_ms()


def parse_sensor_payload(payload: dict) -> dict | None:
    """Payload ESP8266 -> mesure normalisee. Accepte aussi les noms courts du dashboard."""
    def number(*keys):
        for key in keys:
            if payload.get(key) is not None:
                return float(payload[key])
        return None

    try:
        reading = {
            "temperature": number("temperature", "temp"),
            "humidity": number("humidity", "hum"),
            "gas": number("gas"),
            "pir": int(bool(number("pir", "presence") or 0)),
        }
    except (TypeError, ValueError):
        return None
    if reading["temperature"] is None or reading["humidity"] is None or reading["gas"] is None:
        return None
    return reading


def reading_message(reading: dict, ts=None) -> dict:
    return {
        "type": "reading",
        "ts": _ts(ts),
        "temp": reading["temperature"],
        "hum": reading["humidity"],
        "gas": reading["gas"],
        "pir": reading["pir"],
    }


def alert_message(alert: dict) -> dict:
    """Alerte (format IA / backend) -> message dashboard."""
    data = alert.get("data") or {}
    kind = str(alert.get("type", "alerte")).lower()
    value, unit = "", ""
    if kind == "intrusion":
        value, unit = data.get("intruders", data.get("persons", "")), " pers."
    elif kind == "env_anomaly":
        kind = "anomalie"
        value, unit = (data.get("reading") or {}).get("temperature", ""), "°C"
    elif "value" in data:
        value, unit = data["value"], data.get("unit", "")
    return {
        "type": "alert",
        "id": alert.get("id"),
        "ts": _ts(alert.get("timestamp")),
        "device_id": alert.get("node_id", ""),
        "source": alert.get("source", ""),
        "kind": kind,
        "value": value,
        "unit": unit,
        "level": alert.get("severity", "warning"),
        "message": alert.get("message", ""),
    }


class ThresholdWatcher:
    """Alertes de seuil dur (temperature, gaz) et de presence PIR, avec delai anti-repetition."""

    def __init__(self, critical_temp: float, critical_gas: float, cooldown_s: float = 30.0):
        self.critical_temp = critical_temp
        self.critical_gas = critical_gas
        self.cooldown_s = cooldown_s
        self._last: dict[tuple[str, str], float] = {}
        self._pir: dict[str, int] = {}

    def _ready(self, node: str, kind: str, now: float) -> bool:
        if now - self._last.get((node, kind), float("-inf")) < self.cooldown_s:
            return False
        self._last[(node, kind)] = now
        return True

    def check(self, node: str, reading: dict, now: float | None = None) -> list[dict]:
        now = time.time() if now is None else now
        alerts = []
        if reading["temperature"] >= self.critical_temp and self._ready(node, "temperature", now):
            alerts.append(self._alert(node, "TEMPERATURE", "critical",
                                      f"Temperature critique : {reading['temperature']:.1f} °C",
                                      reading["temperature"], "°C"))
        if reading["gas"] >= self.critical_gas and self._ready(node, "gas", now):
            alerts.append(self._alert(node, "GAS", "critical",
                                      f"Niveau de gaz critique : {reading['gas']:.0f}", reading["gas"], ""))
        previous = self._pir.get(node, 0)
        self._pir[node] = reading["pir"]
        if reading["pir"] and not previous and self._ready(node, "presence", now):
            alerts.append(self._alert(node, "PRESENCE", "warning", "Mouvement detecte par le capteur PIR", 1, ""))
        return alerts

    @staticmethod
    def _alert(node, alert_type, severity, message, value, unit) -> dict:
        return {
            "node_id": node, "source": "capteurs", "type": alert_type, "severity": severity,
            "message": message, "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            "data": {"value": round(float(value), 1), "unit": unit},
        }
