"""Classification du geste du pouce a partir des 21 points de la main (MediaPipe).

Convention des points (MediaPipe Hand Landmarker) :
0 poignet | 1-4 pouce | 5-8 index | 9-12 majeur | 13-16 annulaire | 17-20 auriculaire.
Les coordonnees sont en pixels, axe y vers le bas (repere image).
"""

from __future__ import annotations

import math
from enum import Enum
from typing import Sequence

Point = tuple[float, float]


class Gesture(str, Enum):
    THUMB_UP = "pouce_haut"      # arrivee
    THUMB_DOWN = "pouce_bas"     # depart / fin
    THUMB_SIDE = "pouce_cote"    # pause (debut ou retour)
    NONE = "aucun"


WRIST = 0
THUMB_MCP, THUMB_IP, THUMB_TIP = 2, 3, 4
INDEX_MCP = 5
MIDDLE_MCP = 9
# (pip, tip) pour index, majeur, annulaire, auriculaire
FINGERS = ((6, 8), (10, 12), (14, 16), (18, 20))

# Tolerances angulaires (degres) autour des directions cibles.
VERTICAL_TOLERANCE = 35.0
HORIZONTAL_TOLERANCE = 35.0


def _dist(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def fingers_folded(points: Sequence[Point]) -> bool:
    """Vrai si les quatre doigts (hors pouce) sont replies : poing ferme."""
    wrist = points[WRIST]
    return all(_dist(points[tip], wrist) < _dist(points[pip], wrist) for pip, tip in FINGERS)


def thumb_extended(points: Sequence[Point]) -> bool:
    hand_size = _dist(points[WRIST], points[MIDDLE_MCP])
    if hand_size == 0:
        return False
    tip, ip = points[THUMB_TIP], points[THUMB_IP]
    far_from_palm = _dist(tip, points[INDEX_MCP]) > 0.6 * hand_size
    straight = _dist(tip, points[WRIST]) > _dist(ip, points[WRIST])
    return far_from_palm and straight


def thumb_angle(points: Sequence[Point]) -> float:
    """Angle du pouce en degres : 90 = haut, -90 = bas, 0 / 180 = cote."""
    dx = points[THUMB_TIP][0] - points[THUMB_MCP][0]
    dy = points[THUMB_TIP][1] - points[THUMB_MCP][1]
    return math.degrees(math.atan2(-dy, dx))  # -dy : l'axe y image pointe vers le bas


def classify_thumb(points: Sequence[Point]) -> Gesture:
    if len(points) != 21:
        raise ValueError(f"21 points attendus, {len(points)} recus")
    if not (fingers_folded(points) and thumb_extended(points)):
        return Gesture.NONE

    angle = thumb_angle(points)
    if abs(angle - 90) <= VERTICAL_TOLERANCE:
        return Gesture.THUMB_UP
    if abs(angle + 90) <= VERTICAL_TOLERANCE:
        return Gesture.THUMB_DOWN
    if abs(angle) <= HORIZONTAL_TOLERANCE or abs(angle) >= 180 - HORIZONTAL_TOLERANCE:
        return Gesture.THUMB_SIDE
    return Gesture.NONE  # direction ambigue (diagonale) : on ne decide pas


class HandGestureDetector:
    """Detecte la main dans une image BGR et renvoie le geste du pouce."""

    def __init__(self, model_path: str, min_confidence: float = 0.6):
        from mediapipe.tasks.python import BaseOptions
        from mediapipe.tasks.python import vision

        options = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            num_hands=1,
            min_hand_detection_confidence=min_confidence,
            min_hand_presence_confidence=min_confidence,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)

    def detect(self, frame_bgr) -> tuple[Gesture, list[Point] | None]:
        import cv2
        import mediapipe as mp

        height, width = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        result = self._landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
        if not result.hand_landmarks:
            return Gesture.NONE, None
        points = [(lm.x * width, lm.y * height) for lm in result.hand_landmarks[0]]
        return classify_thumb(points), points

    def close(self) -> None:
        self._landmarker.close()
