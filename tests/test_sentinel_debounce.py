from sentinel.debounce import Debouncer


def test_fires_after_required_then_cooldown():
    deb = Debouncer(required=3, cooldown_seconds=10)
    results = [deb.update(True, t) for t in range(6)]
    assert results == [False, False, True, False, False, False]
    assert deb.active


def test_interruption_resets():
    deb = Debouncer(required=2)
    deb.update(True, 0)
    deb.update(False, 1)
    assert deb.update(True, 2) is False
    assert not deb.active


def test_fires_again_after_cooldown():
    deb = Debouncer(required=1, cooldown_seconds=10)
    assert deb.update(True, 0)
    assert not deb.update(True, 5)
    assert deb.update(True, 11)
