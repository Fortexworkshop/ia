from sentinel.vision import IntruderTimer


def run(timer, presence, step=0.2, start=0.0):
    """presence : liste de booleens (inconnu visible a chaque image). Renvoie les instants d'alerte."""
    fired = []
    for i, unknown in enumerate(presence):
        now = start + i * step
        if timer.update(unknown, now):
            fired.append(round(now, 1))
    return fired


def test_unknown_person_triggers_after_20_seconds():
    timer = IntruderTimer(delay=20, grace=2, realert=60)
    fired = run(timer, [True] * 125)  # 25 s
    assert fired == [20.0]
    assert timer.alarm


def test_recognized_person_never_triggers():
    timer = IntruderTimer(delay=20)
    assert run(timer, [False] * 500) == []  # personne reconnue = jamais "inconnue"
    assert not timer.alarm


def test_short_loss_does_not_reset_but_leaving_does():
    timer = IntruderTimer(delay=20, grace=2)
    # 15 s inconnu, 1 s de perte (visage tourne), puis 6 s : alerte a 20 s du debut
    presence = [True] * 75 + [False] * 5 + [True] * 30
    assert run(timer, presence) == [20.0]

    timer = IntruderTimer(delay=20, grace=2)
    # 15 s inconnu, depart 5 s (> grace), retour 15 s : le compteur repart, pas d'alerte
    presence = [True] * 75 + [False] * 25 + [True] * 75
    assert run(timer, presence) == []


def test_alarm_repeats_while_intruder_stays_and_resets_after():
    timer = IntruderTimer(delay=20, grace=2, realert=60)
    fired = run(timer, [True] * 450)  # 90 s
    assert fired == [20.0, 80.0]
    run(timer, [False] * 20, start=90.0)  # parti depuis 4 s
    assert not timer.alarm and timer.elapsed(100.0) == 0.0


def test_backend_intrusion_alert_rings_buzzer_and_led():
    import pytest

    pytest.importorskip("fastapi")
    from backend.app import Hub, Service
    from backend.store import MemoryStore

    sent = []
    service = Service(MemoryStore(), Hub(), None, publish=lambda t, p: sent.append((t, p)) or True,
                      node_id="SX-01")
    service.ingest_alert({"node_id": "SX-01", "source": "anomaly", "type": "ENV_ANOMALY",
                          "severity": "warning", "message": "derive"})
    assert sent == []  # seule l'intrusion declenche l'alarme physique
    service.ingest_alert({"node_id": "SX-01", "source": "vision", "type": "INTRUSION",
                          "severity": "critical", "message": "intrus"})
    assert sent == [("sentinel/SX-01/commands", {"actuator": "buzzer", "state": True}),
                    ("sentinel/SX-01/commands", {"actuator": "led", "state": True})]
