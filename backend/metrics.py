"""Metriques Prometheus du backend (GET /metrics) : supervision et MCO dans Grafana.

Format texte Prometheus, sans dependance supplementaire. Les metriques de la machine hote
(CPU, RAM, disque) utilisent psutil s'il est installe (cas du backend hors Docker).
"""

from __future__ import annotations

import time
from pathlib import Path

try:
    import psutil
except ImportError:  # conteneur backend : pas de psutil, metriques hote absentes
    psutil = None


def _line(name: str, value: float, labels: dict[str, str] | None = None) -> str:
    if labels:
        inner = ",".join(f'{k}="{str(v).replace(chr(34), "")}"' for k, v in labels.items())
        return f"{name}{{{inner}}} {value}"
    return f"{name} {value}"


def render(service, mqtt_connected: bool, vision_running: bool | None = None,
           mosquitto_log: Path | None = None) -> str:
    lines: list[str] = []

    def metric(name: str, kind: str, help_text: str, samples: list[tuple[float, dict | None]]) -> None:
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} {kind}")
        lines.extend(_line(name, value, labels) for value, labels in samples)

    metric("fortex_up", "gauge", "Backend FORTEX en fonctionnement", [(1, None)])
    metric("fortex_mqtt_connected", "gauge", "Pont MQTTS connecte au broker", [(int(mqtt_connected), None)])
    metric("fortex_database_up", "gauge", "Base PostgreSQL joignable", [(int(service.store.healthy()), None)])
    metric("fortex_readings_total", "counter", "Mesures capteurs recues (MQTT)", [(service.readings_total, None)])
    metric("fortex_readings_rejected_total", "counter", "Messages capteurs invalides ignores",
           [(service.rejected_total, None)])
    age = -1 if service.last_reading_at is None else round(time.time() - service.last_reading_at, 1)
    metric("fortex_last_reading_age_seconds", "gauge", "Anciennete de la derniere mesure (-1 = aucune)",
           [(age, None)])
    metric("fortex_alerts_total", "counter", "Alertes recues, par type et source",
           [(n, {"type": t, "source": s}) for (t, s), n in sorted(service.alerts_total.items())] or [(0, None)])
    metric("fortex_commands_total", "counter", "Commandes envoyees au boitier (buzzer, LED)",
           [(service.commands_total, None)])
    metric("fortex_websocket_clients", "gauge", "Dashboards connectes", [(len(service.hub.clients), None)])
    if vision_running is not None:
        metric("fortex_vision_running", "gauge", "Script de vision en cours", [(int(vision_running), None)])
    if mosquitto_log is not None and mosquitto_log.exists():
        metric("fortex_mosquitto_log_bytes", "gauge", "Taille du journal Mosquitto (volume des logs MQTT)",
               [(mosquitto_log.stat().st_size, None)])

    if psutil is not None:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(str(Path.cwd().anchor or "/"))
        metric("fortex_host_cpu_percent", "gauge", "CPU de la machine hote (%)",
               [(psutil.cpu_percent(interval=None), None)])
        metric("fortex_host_memory_percent", "gauge", "RAM utilisee de la machine hote (%)",
               [(memory.percent, None)])
        metric("fortex_host_memory_used_bytes", "gauge", "RAM utilisee (octets)", [(memory.used, None)])
        metric("fortex_host_disk_percent", "gauge", "Disque utilise (%)", [(disk.percent, None)])
    return "\n".join(lines) + "\n"
