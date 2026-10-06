"""Maintenance predictive : detection d'anomalies cinetiques sur les series des capteurs ESP8266.

Pas de seuil statique (if temp > 40) : on decoupe le flux en fenetres glissantes, on calcule des
indicateurs de dynamique (niveau, variabilite, pente, correlation temperature/gaz) et un
Isolation Forest apprend a quoi ressemble une fenetre "normale". Une derive lente et simultanee
de la temperature et du gaz sort de ce profil bien avant d'atteindre un seuil critique.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np

SENSORS = ("temperature", "humidity", "gas")
FEATURES = (
    "temp_mean", "temp_std", "temp_slope",
    "hum_mean", "hum_slope",
    "gas_mean", "gas_std", "gas_slope",
    "temp_gas_corr",
)
DEFAULT_WINDOW = 30  # 30 mesures = 1 min si l'ESP8266 publie toutes les 2 s


def _slope(values: np.ndarray) -> float:
    """Pente de la droite de regression (unite par mesure)."""
    x = np.arange(len(values), dtype=float)
    x -= x.mean()
    return float(np.dot(x, values - values.mean()) / np.dot(x, x))


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    if a.std() < 1e-9 or b.std() < 1e-9:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def window_features(window: np.ndarray) -> np.ndarray:
    """window : tableau (n, 3) temperature, humidite, gaz -> vecteur de FEATURES."""
    temp, hum, gas = window[:, 0], window[:, 1], window[:, 2]
    return np.array([
        temp.mean(), temp.std(), _slope(temp),
        hum.mean(), _slope(hum),
        gas.mean(), gas.std(), _slope(gas),
        _corr(temp, gas),
    ])


def sliding_features(readings: np.ndarray, window: int = DEFAULT_WINDOW, stride: int = 1) -> np.ndarray:
    return np.array([window_features(readings[i:i + window])
                     for i in range(0, len(readings) - window + 1, stride)])


def to_array(readings: Iterable[Mapping[str, float]]) -> np.ndarray:
    return np.array([[float(r[s]) for s in SENSORS] for r in readings], dtype=float)


class AnomalyModel:
    """StandardScaler + IsolationForest sur les indicateurs de fenetre."""

    def __init__(self, window: int = DEFAULT_WINDOW, quantile: float = 0.0, seed: int = 42):
        """quantile : percentile des scores d'entrainement pris comme seuil (0 = le pire cas normal vu).

        Le seuil est appris sur les donnees, pas fixe a la main : une fenetre est anormale si
        elle est plus atypique que toutes (ou presque toutes) les fenetres normales d'entrainement.
        """
        from sklearn.ensemble import IsolationForest
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler

        self.window = window
        self.quantile = quantile
        self.threshold = 0.0
        self.pipeline = make_pipeline(
            StandardScaler(),
            IsolationForest(n_estimators=200, random_state=seed),
        )

    def fit(self, normal_readings: np.ndarray | Sequence[np.ndarray], stride: int = 2) -> "AnomalyModel":
        """normal_readings : une serie (n, 3) ou une liste de series continues.

        Les fenetres ne chevauchent jamais deux series : une coupure (autre jour, autre salle)
        creerait une fausse pente que le modele apprendrait comme "normale".
        """
        series = [normal_readings] if isinstance(normal_readings, np.ndarray) else normal_readings
        features = np.vstack([sliding_features(s, self.window, stride)
                              for s in series if len(s) >= self.window])
        self.pipeline.fit(features)
        self.threshold = float(np.percentile(self.pipeline.score_samples(features), self.quantile))
        return self

    def score(self, window: np.ndarray) -> float:
        """< 0 : fenetre anormale ; plus c'est negatif, plus l'anomalie est marquee."""
        return float(self.pipeline.score_samples(window_features(window)[None, :])[0] - self.threshold)

    def scores(self, readings: np.ndarray) -> np.ndarray:
        return self.pipeline.score_samples(sliding_features(readings, self.window)) - self.threshold

    def save(self, path: str | Path) -> None:
        import joblib

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"window": self.window, "features": FEATURES, "pipeline": self.pipeline,
                     "threshold": self.threshold}, path)

    @classmethod
    def load(cls, path: str | Path) -> "AnomalyModel":
        import joblib

        data = joblib.load(path)
        model = cls.__new__(cls)
        model.window, model.pipeline, model.threshold = data["window"], data["pipeline"], data["threshold"]
        return model


class StreamMonitor:
    """Recoit les mesures une par une et renvoie le score des que la fenetre est pleine."""

    def __init__(self, model: AnomalyModel):
        self.model = model
        self.buffer: deque[Sequence[float]] = deque(maxlen=model.window)

    def push(self, reading: Mapping[str, float]) -> float | None:
        self.buffer.append([float(reading[s]) for s in SENSORS])
        if len(self.buffer) < self.model.window:
            return None
        return self.model.score(np.array(self.buffer))

    def explain(self) -> dict:
        """Indicateurs de la derniere fenetre, joints a l'alerte pour le dashboard."""
        if len(self.buffer) < self.model.window:
            return {}
        return {name: round(float(v), 4) for name, v in zip(FEATURES, window_features(np.array(self.buffer)))}
