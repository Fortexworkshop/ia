import numpy as np
import pytest

from sentinel.anomaly import FEATURES, AnomalyModel, StreamMonitor, sliding_features, window_features
from sentinel.simulate import first_critical, incident_series, normal_series, training_set


def test_features_capture_slope_and_correlation():
    n = 30
    ramp = np.arange(n, dtype=float)
    window = np.column_stack([20 + 0.5 * ramp, np.full(n, 45.0), 300 + 2 * ramp])
    f = dict(zip(FEATURES, window_features(window)))
    assert f["temp_slope"] == pytest.approx(0.5)
    assert f["gas_slope"] == pytest.approx(2.0)
    assert f["hum_slope"] == pytest.approx(0.0)
    assert f["temp_gas_corr"] == pytest.approx(1.0)


def test_flat_signal_has_zero_correlation():
    window = np.column_stack([np.full(30, 22.0), np.full(30, 40.0), np.full(30, 300.0)])
    assert window_features(window)[FEATURES.index("temp_gas_corr")] == 0.0


def test_sliding_features_shape():
    assert sliding_features(np.zeros((100, 3)), window=30, stride=10).shape == (8, len(FEATURES))


@pytest.fixture(scope="module")
def model():
    return AnomalyModel(window=30).fit(training_set(segments=8, length=500))


def test_normal_series_mostly_normal(model):
    scores = model.scores(normal_series(600, np.random.default_rng(7)))
    assert (scores < 0).mean() < 0.05


def test_incident_detected_before_critical_threshold(model):
    series = incident_series(900, start=300, rng=np.random.default_rng(3))
    scores = model.scores(series)
    critical = first_critical(series)
    anomalous = np.where(scores < 0)[0] + model.window - 1
    first = anomalous[anomalous >= 300][0]
    assert critical is not None and first < critical
    # une derive lente : le seuil statique serait atteint bien plus tard
    assert critical - first > 50


def test_save_load_and_stream(model, tmp_path):
    path = tmp_path / "anomaly.joblib"
    model.save(path)
    loaded = AnomalyModel.load(path)
    series = normal_series(40, np.random.default_rng(1))

    monitor = StreamMonitor(loaded)
    results = [monitor.push(dict(zip(("temperature", "humidity", "gas"), row))) for row in series]
    assert results[:29] == [None] * 29
    assert results[29] == pytest.approx(model.score(series[:30]))
    assert set(monitor.explain()) == set(FEATURES)
