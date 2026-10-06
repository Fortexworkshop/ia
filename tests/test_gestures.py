import math

import pytest

from presence.gestures import Gesture, classify_thumb

# Poing ferme, pouce tendu vers le haut (pixels, y vers le bas, poignet en 0,0).
THUMB_UP_FIST = [
    (0, 0),
    (-5, -40), (-5, -75), (-5, -95), (-5, -115),      # pouce
    (5, -60), (35, -62), (38, -45), (25, -42),        # index replie
    (5, -45), (35, -47), (38, -30), (25, -28),        # majeur replie
    (5, -30), (33, -32), (35, -18), (24, -16),        # annulaire replie
    (5, -15), (28, -17), (30, -6), (20, -5),          # auriculaire replie
]


def rotate(points, degrees):
    """Rotation dans le sens horaire a l'ecran (repere image, y vers le bas)."""
    a = math.radians(degrees)
    return [(x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)) for x, y in points]


@pytest.mark.parametrize("angle, expected", [
    (0, Gesture.THUMB_UP),
    (15, Gesture.THUMB_UP),
    (-20, Gesture.THUMB_UP),
    (180, Gesture.THUMB_DOWN),
    (165, Gesture.THUMB_DOWN),
    (90, Gesture.THUMB_SIDE),
    (-90, Gesture.THUMB_SIDE),
    (100, Gesture.THUMB_SIDE),
    (45, Gesture.NONE),       # diagonale : ambigu
])
def test_thumb_direction(angle, expected):
    assert classify_thumb(rotate(THUMB_UP_FIST, angle)) is expected


def test_open_hand_is_not_a_gesture():
    open_hand = list(THUMB_UP_FIST)
    for mcp, pip, dip, tip in ((5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16), (17, 18, 19, 20)):
        x, y = open_hand[mcp]
        open_hand[pip], open_hand[dip], open_hand[tip] = (x + 30, y), (x + 50, y), (x + 70, y)
    assert classify_thumb(open_hand) is Gesture.NONE


def test_folded_thumb_is_not_a_gesture():
    fist = list(THUMB_UP_FIST)
    fist[3], fist[4] = (0, -60), (10, -55)
    assert classify_thumb(fist) is Gesture.NONE


def test_scale_and_translation_invariant():
    moved = [(x * 3 + 400, y * 3 + 300) for x, y in THUMB_UP_FIST]
    assert classify_thumb(moved) is Gesture.THUMB_UP


def test_wrong_number_of_points():
    with pytest.raises(ValueError):
        classify_thumb([(0, 0)] * 5)
