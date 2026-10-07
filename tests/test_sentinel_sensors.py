from sentinel.sensors import normalize, topics


def test_all_formats_give_same_reading():
    expected = {"temperature": 22.5, "humidity": 40.0, "gas": 300.0, "pir": 1}
    assert normalize({"temperature": 22.5, "humidity": 40, "gas": 300, "pir": 1}) == expected
    assert normalize({"temperature": 22.5, "humidite": 40, "niveau_gaz": 300, "presence": True}) == expected
    assert normalize({"temp": 22.5, "hum": 40, "gas": 300, "pir": 1}) == expected


def test_incomplete_or_invalid():
    assert normalize({"temperature": 22}) is None
    assert normalize({"temperature": "x", "humidity": 1, "gas": 1}) is None
    assert normalize(["pas", "un", "dict"]) is None
    assert normalize({"temperature": 22, "humidity": 40, "gas": 300})["pir"] == 0


def test_topics_split():
    assert topics("a/+/b, c/d ,") == ["a/+/b", "c/d"]
