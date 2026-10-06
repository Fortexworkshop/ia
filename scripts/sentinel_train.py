"""Entraine le modele de maintenance predictive (Isolation Forest) et l'evalue.

python scripts/sentinel_train.py                         # donnees simulees
python scripts/sentinel_train.py --csv data/sensors.csv  # mesures reelles enregistrees (regime normal)

L'evaluation rejoue des incidents simules (surchauffe lente + derive de gaz) et mesure :
taux de detection, fausses alertes sur du normal, et avance sur le seuil critique.
"""

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sentinel import config  # noqa: E402
from sentinel.anomaly import DEFAULT_WINDOW, AnomalyModel, to_array  # noqa: E402
from sentinel.simulate import first_critical, incident_series, normal_series, training_set  # noqa: E402

CONSECUTIVE = 10  # fenetres anormales de suite avant alerte (comme en production)


def load_csv(path: Path) -> np.ndarray:
    with path.open(encoding="utf-8") as f:
        return to_array(csv.DictReader(f))


def first_alert(scores: np.ndarray, consecutive: int = CONSECUTIVE) -> int | None:
    run = 0
    for i, score in enumerate(scores):
        run = run + 1 if score < 0 else 0
        if run >= consecutive:
            return i
    return None


def evaluate(model: AnomalyModel, runs: int, period: float, seed: int = 123) -> None:
    rng = np.random.default_rng(seed)
    detected, leads, false_alarms = 0, [], 0
    for _ in range(runs):
        series = incident_series(900, start=300, rng=rng)
        alert = first_alert(model.scores(series))
        critical = first_critical(series)
        if alert is not None:
            alert_index = alert + model.window - 1  # indice de la derniere mesure de la fenetre
            if alert_index >= 300:
                detected += 1
                if critical is not None:
                    leads.append((critical - alert_index) * period)
        if first_alert(model.scores(normal_series(900, rng))) is not None:
            false_alarms += 1

    print(f"\nEvaluation sur {runs} incidents et {runs} series normales simulees "
          f"(1 mesure / {period:g} s, alerte apres {CONSECUTIVE} fenetres anormales) :")
    print(f"  incidents detectes      : {detected}/{runs}")
    print(f"  series normales alertees: {false_alarms}/{runs}")
    if leads:
        print(f"  avance sur seuil critique (40 C / gaz 600) : moyenne {np.mean(leads):.0f} s, "
              f"min {np.min(leads):.0f} s")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", type=Path, help="mesures reelles en regime normal (colonnes temperature,humidity,gas)")
    parser.add_argument("--window", type=int, default=DEFAULT_WINDOW)
    parser.add_argument("--quantile", type=float, default=0.0,
                        help="percentile des scores normaux pris comme seuil (0 = minimum)")
    parser.add_argument("--period", type=float, default=2.0, help="secondes entre deux mesures ESP8266")
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--out", type=Path, default=config.ANOMALY_MODEL)
    args = parser.parse_args()

    series = [load_csv(args.csv)] if args.csv else training_set()
    total = sum(len(s) for s in series)
    source = args.csv or "simulation"
    if total < args.window * 5:
        sys.exit(f"Pas assez de mesures ({total}), il en faut au moins {args.window * 5}")
    print(f"Entrainement sur {total} mesures ({source}), fenetre {args.window}")

    model = AnomalyModel(args.window, args.quantile).fit(series)
    model.save(args.out)
    print(f"Modele sauvegarde : {args.out}")
    evaluate(model, args.runs, args.period)


if __name__ == "__main__":
    main()
