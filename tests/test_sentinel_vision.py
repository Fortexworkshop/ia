import json
import urllib.request

import numpy as np

from sentinel.vision import Detection, StreamState, annotate, mark_authorized, prepare_frame, start_stream_server


def test_prepare_frame_resizes_to_640x480():
    assert prepare_frame(np.zeros((1080, 1920, 3), np.uint8)).shape == (480, 640, 3)
    frame = np.zeros((480, 640, 3), np.uint8)
    assert prepare_frame(frame) is frame


def test_known_face_inside_person_box_is_authorized():
    person = Detection((100, 50, 300, 450), 0.9)
    stranger = Detection((400, 50, 600, 450), 0.8)
    mark_authorized([person, stranger], [("Alice", (160, 80, 60, 60))])
    assert person.authorized == "Alice"
    assert stranger.authorized is None


def test_one_face_authorizes_only_one_person():
    a, b = Detection((0, 0, 300, 300), 0.9), Detection((0, 0, 300, 300), 0.9)
    mark_authorized([a, b], [("Alice", (100, 100, 50, 50))])
    assert [a.authorized, b.authorized] == ["Alice", None]


def test_annotate_keeps_frame_size():
    frame = np.zeros((480, 640, 3), np.uint8)
    view = annotate(frame, [Detection((10, 10, 100, 200), 0.7)], 42.0, 20.0, alarm=True)
    assert view.shape == frame.shape
    assert view.any() and not frame.any()  # l'original n'est pas modifie


def test_stream_server_serves_status_and_snapshot():
    state = StreamState()
    server = start_stream_server(state, "127.0.0.1", 0)
    port = server.server_port
    state.publish(np.zeros((480, 640, 3), np.uint8), {"persons": 2, "alarm": True})
    try:
        status = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/status", timeout=2).read())
        assert status == {"persons": 2, "alarm": True}
        jpeg = urllib.request.urlopen(f"http://127.0.0.1:{port}/snapshot.jpg", timeout=2).read()
        assert jpeg[:2] == b"\xff\xd8"
    finally:
        server.shutdown()


def test_ascii_text_for_video_labels():
    from sentinel.vision import ascii_text

    assert ascii_text("Chloé Lefèvre") == "Chloe Lefevre"  # OpenCV n'affiche pas les accents
