from presence.gestures import Gesture
from presence.stabilizer import GestureStabilizer


def feed(stab, student, gesture, frames, start=0.0):
    return [stab.update(student, gesture, start + i * 0.03) for i in range(frames)]


def test_fires_once_after_enough_frames():
    stab = GestureStabilizer(frames_required=5, cooldown_seconds=5)
    results = feed(stab, "alice", Gesture.THUMB_UP, 10)
    assert results[:4] == [None] * 4
    assert results[4] is Gesture.THUMB_UP
    assert results[5:] == [None] * 5  # cooldown


def test_interruption_resets_counter():
    stab = GestureStabilizer(frames_required=3)
    stab.update("alice", Gesture.THUMB_UP, 0)
    stab.update("alice", Gesture.THUMB_UP, 0.1)
    stab.update("alice", Gesture.NONE, 0.2)
    assert stab.update("alice", Gesture.THUMB_UP, 0.3) is None


def test_unknown_face_never_fires():
    stab = GestureStabilizer(frames_required=1)
    assert stab.update(None, Gesture.THUMB_UP, 0) is None


def test_fires_again_after_cooldown():
    stab = GestureStabilizer(frames_required=1, cooldown_seconds=5)
    assert stab.update("alice", Gesture.THUMB_SIDE, 0) is Gesture.THUMB_SIDE
    assert stab.update("alice", Gesture.THUMB_SIDE, 2) is None
    assert stab.update("alice", Gesture.THUMB_SIDE, 6) is Gesture.THUMB_SIDE
