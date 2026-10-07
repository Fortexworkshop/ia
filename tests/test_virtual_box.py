import pytest

from sentinel.sensors import normalize
from sentinel.virtual_box import LOCAL_GAS_ALARM, VirtualBox


def test_payload_matches_firmware_format():
    payload = VirtualBox("SX-01", seed=1).tick(0)
    assert normalize(payload) is not None
    assert payload["node_id"] == "SX-01" and isinstance(payload["gas"], int)


def test_values_follow_base_settings():
    box = VirtualBox("SX-01", seed=2)
    box.set_base(temperature=35, gas=5000)  # gaz borne a 1023 (ADC)
    for t in range(40):
        payload = box.tick(t)
    assert payload["temperature"] == pytest.approx(35, abs=1)
    assert box.base["gas"] == 1023


def test_slow_overheat_scenario_drifts_temperature_and_gas_together():
    box = VirtualBox("SX-01", seed=3)
    box.start_scenario("surchauffe")
    readings = [box.tick(t) for t in range(100)]
    assert readings[-1]["temperature"] - readings[0]["temperature"] > 3
    assert readings[-1]["gas"] - readings[0]["gas"] > 60
    assert readings[-1]["temperature"] < 40  # encore sous le seuil critique : l'IA doit l'anticiper


def test_gas_leak_triggers_local_alarm_like_firmware():
    box = VirtualBox("SX-01", seed=4)
    box.start_scenario("fuite_gaz")
    for t in range(60):
        box.tick(t)
    assert box.values["gas"] >= LOCAL_GAS_ALARM
    state = box.state()
    assert state["buzzer"] and state["led_red"] and "ALARME" in state["oled"][-1]
    box.start_scenario(None)
    for t in range(60):
        box.tick(t)
    assert not box.local_alarm


def test_supervisor_commands_and_pir():
    box = VirtualBox("SX-01", seed=5)
    assert box.on_command({"actuator": "led", "state": True}) and box.state()["led_red"]
    assert box.on_command({"actuator": "buzzer", "state": True}) and box.buzzer
    assert not box.on_command({"actuator": "laser", "state": True})
    box.trigger_motion(now=100, duration=5)
    assert box.tick(102)["pir"] == 1 and box.tick(106)["pir"] == 0


def test_unknown_scenario_rejected():
    with pytest.raises(ValueError):
        VirtualBox("SX-01").start_scenario("volcan")


@pytest.fixture(scope="module")
def model():
    from sentinel.anomaly import AnomalyModel
    from sentinel.simulate import training_set

    return AnomalyModel(window=30).fit(training_set(segments=8, length=500))


def first_alert(model, box, steps, consecutive=10):
    from sentinel.anomaly import StreamMonitor

    monitor, run = StreamMonitor(model), 0
    for t in range(steps):
        score = monitor.push(box.tick(t))
        run = run + 1 if score is not None and score < 0 else 0
        if run >= consecutive:
            return t
    return None


def test_ai_stays_quiet_on_normal_virtual_box(model):
    assert first_alert(model, VirtualBox("SX-01", seed=11), 400) is None


def test_ai_detects_virtual_overheat_before_critical_threshold(model):
    box = VirtualBox("SX-01", seed=12)
    for t in range(60):
        box.tick(t)
    box.start_scenario("surchauffe")
    assert first_alert(model, box, 400) is not None
    assert box.values["temperature"] < 40 and box.values["gas"] < 600
