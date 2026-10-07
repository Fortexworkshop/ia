"""Boitier SENTINEL-X virtuel : remplace l'ESP8266 et ses capteurs physiques.

Reproduit le comportement du firmware (firmware/sentinel-x/src/main.cpp) :
- mesures DHT22 (temperature, humidite), MQ-2 (gaz, valeur ADC 0-1023), PIR (mouvement)
- commandes {"actuator": "buzzer"|"led", "state": bool} recues du superviseur
- garde-fou local : buzzer + LED rouge si le gaz depasse LOCAL_GAS_ALARM
- LED verte = lien serveur OK

Les valeurs suivent une base reglable (curseurs) avec un bruit realiste, ou un scenario d'incident.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime

import numpy as np

LOCAL_GAS_ALARM = 700
LIMITS = {"temperature": (-10.0, 80.0), "humidity": (0.0, 100.0), "gas": (0.0, 1023.0)}
NOISE = {"temperature": 0.1, "humidity": 0.4, "gas": 4.0}  # ecart-type du bruit des capteurs reels

# scenario -> (derive par mesure : temperature, humidite, gaz, terme quadratique du gaz)
SCENARIOS = {
    "surchauffe": (0.05, -0.01, 0.9, 0.002),   # hausse lente correlee temperature + gaz (exemple du sujet)
    "fuite_gaz": (0.0, 0.0, 12.0, 0.0),         # fuite franche
}


class VirtualBox:
    def __init__(self, node_id: str, seed: int | None = None):
        self.node_id = node_id
        self.rng = np.random.default_rng(seed)
        self.base = {"temperature": 23.0, "humidity": 45.0, "gas": 300.0}
        self.level = dict(self.base)   # niveau reel (suit la base en douceur) ; mesure = niveau + bruit
        self.values = dict(self.base)
        self.scenario_origin = dict(self.base)
        self.pir = 0
        self.pir_until = 0.0
        self.scenario: str | None = None
        self.scenario_step = 0
        self.buzzer_remote = False
        self.led_remote = False
        self.mqtt_connected = False
        self.published = 0
        self.ip = "192.168.10.42"
        self.events: deque[str] = deque(maxlen=12)

    # --- commandes de l'interface ---------------------------------------------
    def set_base(self, **values: float) -> None:
        for name, value in values.items():
            if name in self.base and value is not None:
                low, high = LIMITS[name]
                self.base[name] = float(min(max(value, low), high))

    def start_scenario(self, name: str | None) -> None:
        if name is not None and name not in SCENARIOS:
            raise ValueError(f"scenario inconnu : {name}")
        self.scenario, self.scenario_step = name, 0
        self.scenario_origin = dict(self.level)
        self._log(f"scenario : {name or 'normal'}")

    def trigger_motion(self, now: float, duration: float = 6.0) -> None:
        self.pir_until = now + duration
        self._log("mouvement devant le PIR")

    # --- commandes MQTT du superviseur ----------------------------------------
    def on_command(self, payload: dict) -> bool:
        actuator, state = payload.get("actuator"), bool(payload.get("state", False))
        if actuator == "buzzer":
            self.buzzer_remote = state
        elif actuator == "led":
            self.led_remote = state
        else:
            return False
        self._log(f"commande superviseur : {actuator} {'ON' if state else 'OFF'}")
        return True

    # --- simulation ---------------------------------------------------------------
    def tick(self, now: float) -> dict:
        """Une mesure (toutes les 2 s sur le vrai boitier). Renvoie le payload MQTT."""
        if self.scenario:
            self.scenario_step += 1
            k = self.scenario_step
            dt, dh, dg, dg2 = SCENARIOS[self.scenario]
            origin = self.scenario_origin
            self.level = {"temperature": origin["temperature"] + dt * k,
                          "humidity": origin["humidity"] + dh * k,
                          "gas": origin["gas"] + dg * k + dg2 * k * k}
        else:
            for name in self.level:  # le niveau rejoint la base reglee en douceur (inertie thermique)
                self.level[name] += (self.base[name] - self.level[name]) * 0.2
        for name in self.values:
            # mesure = niveau + bruit blanc du capteur (comme les donnees d'entrainement de l'IA)
            self.values[name] = self.level[name] + self.rng.normal(0, NOISE[name])
        for name, (low, high) in LIMITS.items():
            self.values[name] = min(max(self.values[name], low), high)
        self.pir = int(now < self.pir_until)
        return {
            "node_id": self.node_id,
            "temperature": round(self.values["temperature"], 1),
            "humidity": round(self.values["humidity"], 1),
            "gas": int(round(self.values["gas"])),
            "pir": self.pir,
            "ip": self.ip,
            "rssi": -55,
            "virtual": True,
        }

    # --- sorties (comme le firmware) ------------------------------------------
    @property
    def local_alarm(self) -> bool:
        return self.values["gas"] >= LOCAL_GAS_ALARM

    @property
    def buzzer(self) -> bool:
        return self.buzzer_remote or self.local_alarm

    def oled(self) -> list[str]:
        if self.local_alarm:
            status = "!! ALARME GAZ !!"
        elif self.buzzer_remote or self.led_remote:
            status = "Alerte superviseur"
        else:
            status = "Statut : normal"
        return [
            "SENTINEL-X",
            f"IP {self.ip}",
            f"MQTT {'OK (TLS)' if self.mqtt_connected else 'echec'}",
            f"T {self.values['temperature']:.1f}C  H {self.values['humidity']:.0f}%",
            f"Gaz {int(round(self.values['gas']))}  PIR {'OUI' if self.pir else 'non'}",
            status,
        ]

    def state(self) -> dict:
        return {
            "node_id": self.node_id,
            "values": {k: round(v, 1) for k, v in self.values.items()},
            "base": self.base,
            "pir": self.pir,
            "scenario": self.scenario,
            "scenario_step": self.scenario_step,
            "mqtt_connected": self.mqtt_connected,
            "published": self.published,
            "led_green": self.mqtt_connected,
            "led_red": self.led_remote or self.local_alarm,
            "led_red_blink": not self.mqtt_connected,
            "buzzer": self.buzzer,
            "local_alarm": self.local_alarm,
            "oled": self.oled(),
            "events": list(self.events),
        }

    def _log(self, text: str) -> None:
        self.events.appendleft(f"{datetime.now():%H:%M:%S} {text}")
