"""Vision intelligente : detection de presence humaine sur la webcam USB du PC Serveur Local.

webcam ─► bridage 640x480 ─► YOLOv8n (classe "person") ─► [option] liste blanche visages
       ─► IntruderTimer (non reconnu pendant 20 s) ─► alerte POST /api/v1/alerts (buzzer + LED)
       └► flux MJPEG annote pour le dashboard (http://<serveur>:8081/video)
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2
import numpy as np

PERSON_CLASS = 0  # index COCO de "person"


@dataclass
class Detection:
    box: tuple[int, int, int, int]  # x1, y1, x2, y2
    confidence: float
    authorized: str | None = None   # nom si le visage est dans la liste blanche


def prepare_frame(frame: np.ndarray, size: tuple[int, int] = (640, 480)) -> np.ndarray:
    """Bridage systematique de la resolution avant inference (exigence < 100 ms par trame)."""
    if (frame.shape[1], frame.shape[0]) == size:
        return frame
    return cv2.resize(frame, size, interpolation=cv2.INTER_AREA)


class PersonDetector:
    """YOLOv8 (Ultralytics) limite a la classe personne."""

    def __init__(self, model_path: str, confidence: float = 0.5, imgsz: int = 640):
        from ultralytics import YOLO

        self.model = YOLO(model_path)
        self.confidence = confidence
        self.imgsz = imgsz
        self.detect(np.zeros((480, 640, 3), np.uint8))  # prechauffage : la 1re inference est lente

    def detect(self, frame_bgr: np.ndarray) -> list[Detection]:
        result = self.model.predict(frame_bgr, classes=[PERSON_CLASS], conf=self.confidence,
                                    imgsz=self.imgsz, verbose=False)[0]
        detections = []
        for box, conf in zip(result.boxes.xyxy.tolist(), result.boxes.conf.tolist()):
            x1, y1, x2, y2 = (int(v) for v in box)
            detections.append(Detection((x1, y1, x2, y2), float(conf)))
        return detections


def mark_authorized(detections: list[Detection], known_faces: list[tuple[str, tuple[int, int, int, int]]]) -> None:
    """Une personne est autorisee si le centre d'un visage reconnu tombe dans sa boite.

    known_faces : [(nom, (x, y, largeur, hauteur))] issus de presence.faces.
    """
    for name, (fx, fy, fw, fh) in known_faces:
        cx, cy = fx + fw / 2, fy + fh / 2
        for det in detections:
            x1, y1, x2, y2 = det.box
            if det.authorized is None and x1 <= cx <= x2 and y1 <= cy <= y2:
                det.authorized = name
                break


def known_faces_in(recognizer, frame_bgr: np.ndarray) -> list[tuple[str, tuple[int, int, int, int]]]:
    """Tous les visages reconnus de la liste blanche (recognizer = presence.faces.FaceRecognizer)."""
    found = []
    for face in recognizer.detect(frame_bgr):
        name, _ = recognizer.db.best_match(recognizer.embedding(frame_bgr, face), recognizer.threshold)
        if name:
            found.append((name, tuple(int(v) for v in face[:4])))
    return found


GREEN, RED, WHITE = (0, 200, 0), (0, 0, 230), (255, 255, 255)


class IntruderTimer:
    """Alarme quand une personne NON reconnue reste `delay` secondes devant la camera.

    - une personne reconnue (liste blanche) ne fait jamais avancer le compteur ;
    - une perte breve (< `grace` s : visage tourne, detection manquee) ne remet pas a zero ;
    - l'alarme reste active tant que l'inconnu est la, avec une nouvelle alerte toutes les `realert` s.
    """

    def __init__(self, delay: float = 20.0, grace: float = 2.0, realert: float = 60.0):
        self.delay, self.grace, self.realert = delay, grace, realert
        self.since: float | None = None      # debut de la presence non reconnue
        self.last_seen = float("-inf")
        self.last_alert: float | None = None

    def update(self, unknown_present: bool, now: float) -> bool:
        """Renvoie True quand une alerte doit partir."""
        if unknown_present:
            if self.since is None:
                self.since = now
            self.last_seen = now
        elif self.since is not None and now - self.last_seen > self.grace:
            self.since, self.last_alert = None, None  # l'inconnu est parti : tout repart de zero
        if self.since is None or now - self.since < self.delay:
            return False
        if self.last_alert is None or now - self.last_alert >= self.realert:
            self.last_alert = now
            return True
        return False

    def elapsed(self, now: float) -> float:
        return 0.0 if self.since is None else now - self.since

    @property
    def alarm(self) -> bool:
        return self.last_alert is not None


ORANGE = (0, 140, 255)


def annotate(frame: np.ndarray, detections: list[Detection], latency_ms: float, fps: float,
             alarm: bool, note: str = "", labels: dict[str, str] | None = None) -> np.ndarray:
    view = frame.copy()
    for det in detections:
        x1, y1, x2, y2 = det.box
        # vert = reconnu ; orange = non reconnu (compte a rebours) ; rouge = intrus (alarme)
        color = GREEN if det.authorized else (RED if alarm else ORANGE)
        if det.authorized:
            label = (labels or {}).get(det.authorized, det.authorized)  # « Nom - role »
        else:
            label = f"INTRUS {det.confidence:.0%}" if alarm else "Non reconnu"
        cv2.rectangle(view, (x1, y1), (x2, y2), color, 2)
        cv2.putText(view, label, (x1, max(15, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    cv2.putText(view, f"{latency_ms:.0f} ms | {fps:.1f} fps", (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, GREEN if latency_ms < 100 else RED, 2)
    if note:
        cv2.putText(view, note, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, WHITE, 2)
    if alarm:
        cv2.rectangle(view, (0, 0), (view.shape[1] - 1, view.shape[0] - 1), RED, 6)
        cv2.putText(view, "DETECTION INTRUS", (10, view.shape[0] - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, RED, 2)
    return view


@dataclass
class StreamState:
    jpeg: bytes = b""
    status: dict = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)
    new_frame: threading.Condition = field(default_factory=threading.Condition)

    def publish(self, frame: np.ndarray, status: dict) -> None:
        ok, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        with self.lock:
            if ok:
                self.jpeg = buffer.tobytes()
            self.status = status
        with self.new_frame:
            self.new_frame.notify_all()


def start_stream_server(state: StreamState, host: str, port: int) -> ThreadingHTTPServer:
    """Flux pour le dashboard : /video (MJPEG), /snapshot.jpg, /status (JSON)."""

    class Handler(BaseHTTPRequestHandler):
        def _headers(self, content_type: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

        def do_GET(self):  # noqa: N802 (nom impose par http.server)
            if self.path.startswith("/video"):
                self._headers("multipart/x-mixed-replace; boundary=frame")
                try:
                    while True:
                        with state.new_frame:
                            state.new_frame.wait(timeout=2)
                        with state.lock:
                            jpeg = state.jpeg
                        self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n")
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    return
            elif self.path.startswith("/snapshot"):
                with state.lock:
                    jpeg = state.jpeg
                self._headers("image/jpeg")
                self.wfile.write(jpeg)
            elif self.path.startswith("/status"):
                with state.lock:
                    body = json.dumps(state.status).encode()
                self._headers("application/json")
                self.wfile.write(body)
            else:
                self.send_error(404)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
