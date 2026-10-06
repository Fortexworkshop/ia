"""Donnees capteurs simulees (DHT22 + MQ-2) pour entrainer/tester avant que l'ESP8266 soit pret.

Les seuils CRITICAL_* ne servent qu'a mesurer l'avance de la detection en evaluation :
le modele, lui, ne les utilise jamais.
"""

from __future__ import annotations

import numpy as np

CRITICAL_TEMP = 40.0   # degres C
CRITICAL_GAS = 600.0   # valeur ADC du MQ-2 (0-1023)


def normal_series(n: int, rng: np.random.Generator, base_temp: float | None = None,
                  base_gas: float | None = None) -> np.ndarray:
    """Regime normal : niveau stable, lente oscillation, bruit de mesure realiste."""
    base_temp = rng.uniform(19, 27) if base_temp is None else base_temp
    base_gas = rng.uniform(200, 380) if base_gas is None else base_gas
    base_hum = rng.uniform(35, 60)
    t = np.arange(n)
    phase = rng.uniform(0, 2 * np.pi)
    temp = base_temp + 0.4 * np.sin(2 * np.pi * t / 900 + phase) + rng.normal(0, 0.1, n)
    hum = base_hum + 0.8 * np.sin(2 * np.pi * t / 1200 + phase) + rng.normal(0, 0.4, n)
    gas = base_gas + rng.normal(0, 4, n)
    # pics isoles (perturbation ponctuelle, pas un incident)
    spikes = rng.random(n) < 0.003
    gas[spikes] += rng.uniform(15, 40, spikes.sum())
    return np.column_stack([np.round(temp, 1), np.round(hum, 1), np.round(gas)])


def training_set(segments: int = 12, length: int = 600, seed: int = 0) -> list[np.ndarray]:
    """Plusieurs regimes normaux independants (pieces, heures differentes)."""
    rng = np.random.default_rng(seed)
    return [normal_series(length, rng) for _ in range(segments)]


def incident_series(n: int, start: int, rng: np.random.Generator,
                    temp_rate: float = 0.04, gas_rate: float = 0.8) -> np.ndarray:
    """Surchauffe lente + micro-derive de gaz a partir de `start` (unites par mesure)."""
    series = normal_series(n, rng, base_temp=rng.uniform(21, 25), base_gas=rng.uniform(250, 330))
    ramp = np.clip(np.arange(n) - start, 0, None).astype(float)
    series[:, 0] += temp_rate * ramp
    series[:, 1] -= 0.01 * ramp
    series[:, 2] += gas_rate * ramp + 0.002 * ramp ** 2
    return series


def first_critical(series: np.ndarray) -> int | None:
    hits = np.where((series[:, 0] >= CRITICAL_TEMP) | (series[:, 2] >= CRITICAL_GAS))[0]
    return int(hits[0]) if len(hits) else None
