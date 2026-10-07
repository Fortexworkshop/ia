"""Plateforme web locale : enregistrer des agents (liste blanche) et tester une image.

GET    /                       page web
GET    /api/agents           agents enregistres
POST   /api/agents           enregistre un agent (champ "name" + fichiers "photos")
DELETE /api/agents/<nom>     supprime un agent (droit a l'effacement RGPD)
POST   /api/analyze            analyse une image (fichier "image") : personnes, visages reconnus, image annotee
POST   /api/checkin            pointage (fichier "image") : visage + geste du pouce -> heure enregistree
GET    /api/attendance?day=    feuille de presence du jour (JSON), /api/attendance.csv pour l'export

Gestes : pouce en haut = arrivee | pouce sur le cote = pause (aller puis retour) | pouce en bas = fin
"""

from __future__ import annotations

import base64
import tempfile
import threading
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

import cv2
import numpy as np

STATIC_DIR = Path(__file__).resolve().parent / "static"
MAX_SIDE = 1280  # les photos de telephone sont reduites avant analyse
GREEN, RED, ORANGE = (0, 190, 0), (0, 0, 230), (0, 140, 255)


def decode_image(data: bytes) -> np.ndarray | None:
    image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        return None
    scale = MAX_SIDE / max(image.shape[:2])
    if scale < 1:
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return image


def to_data_url(image: np.ndarray) -> str:
    ok, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return "data:image/jpeg;base64," + base64.b64encode(buffer.tobytes()).decode() if ok else ""


@dataclass
class FaceResult:
    name: str | None
    score: float
    box: tuple[int, int, int, int]  # x, y, largeur, hauteur


@dataclass
class Analysis:
    faces: list[FaceResult] = field(default_factory=list)
    persons: list[dict] = field(default_factory=list)  # {"box", "confidence", "authorized"}
    image: str = ""                                     # image annotee (data URL)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["intruders"] = sum(1 for p in self.persons if not p["authorized"])
        return data


class FaceEngine:
    """Regroupe reconnaissance faciale (presence.faces) et detection de personnes (YOLO).

    Les modeles sont charges au premier usage ; un verrou evite les appels concurrents.
    """

    def __init__(self, faces_db_path: Path, detector_model: str, recognizer_model: str, yolo_model: str | None,
                 hand_model: str | None = None, attendance_db: Path | None = None):
        from presence.faces import FaceDatabase

        self.db = FaceDatabase(faces_db_path)
        self.detector_model = detector_model
        self.recognizer_model = recognizer_model
        self.yolo_model = yolo_model
        self.hand_model = hand_model
        self.attendance_db = attendance_db
        self._recognizer = None
        self._persons = None
        self._hands = None
        self._lock = threading.Lock()

    @property
    def hands(self):
        if self._hands is None:
            from presence.gestures import HandGestureDetector

            self._hands = HandGestureDetector(self.hand_model)
        return self._hands

    def _register(self):
        """Une connexion SQLite par appel : sqlite3 interdit de partager une connexion entre threads."""
        from presence.attendance import AttendanceRegister

        return AttendanceRegister(self.attendance_db)

    @property
    def recognizer(self):
        if self._recognizer is None:
            from presence.faces import FaceRecognizer

            self._recognizer = FaceRecognizer(self.detector_model, self.recognizer_model, self.db)
        return self._recognizer

    @property
    def persons(self):
        if self._persons is None and self.yolo_model:
            from .vision import PersonDetector

            self._persons = PersonDetector(self.yolo_model)
        return self._persons

    def agents(self) -> list[str]:
        return sorted(self.db.embeddings)

    def enroll(self, name: str, images: list[tuple[str, np.ndarray | None]]) -> dict:
        """images : [(nom du fichier, image ou None si illisible)]. Remplace l'agent s'il existe."""
        report, embeddings = [], []
        with self._lock:
            for filename, image in images:
                face = self.recognizer.largest_face(image) if image is not None else None
                if image is None:
                    report.append({"file": filename, "ok": False, "reason": "image illisible"})
                elif face is None:
                    report.append({"file": filename, "ok": False, "reason": "aucun visage detecte"})
                else:
                    embeddings.append(self.recognizer.embedding(image, face))
                    report.append({"file": filename, "ok": True})
            if embeddings:
                self.db.add(name, embeddings)
                self.db.save()
        return {"name": name, "enrolled": bool(embeddings), "used": len(embeddings), "files": report}

    def remove(self, name: str) -> bool:
        with self._lock:
            removed = self.db.remove(name)
            if removed:
                self.db.save()
        return removed

    def analyze(self, image: np.ndarray) -> Analysis:
        from .vision import mark_authorized

        with self._lock:
            result = Analysis()
            for face in self.recognizer.detect(image):
                name, score = self.db.best_match(self.recognizer.embedding(image, face), self.recognizer.threshold)
                result.faces.append(FaceResult(name, round(score, 3), tuple(int(v) for v in face[:4])))
            detections = self.persons.detect(image) if self.persons else []
        mark_authorized(detections, [(f.name, f.box) for f in result.faces if f.name])
        result.persons = [{"box": d.box, "confidence": round(d.confidence, 3), "authorized": d.authorized}
                          for d in detections]
        result.image = to_data_url(draw(image, result))
        return result


    def checkin(self, image: np.ndarray) -> dict:
        """Reconnait l'agent le plus proche et son geste, puis enregistre l'evenement."""
        from presence.gestures import Gesture

        with self._lock:
            match = self.recognizer.identify(image)
            gesture, points = self.hands.detect(image)
            result = {"agent": match.name if match else None,
                      "score": round(match.score, 3) if match else None,
                      "gesture": gesture.value, "accepted": False, "events": []}
            if match is None:
                result["message"] = "Aucun visage detecte : place-toi face a la camera"
            elif match.name is None:
                result["message"] = "Visage inconnu : enregistre d'abord l'agent"
            elif gesture is Gesture.NONE:
                result["message"] = (f"{match.name} reconnu, mais aucun geste lu : poing ferme, "
                                     "pouce bien tendu vers le haut, le cote ou le bas")
            else:
                register = self._register()
                try:
                    outcome = register.handle(match.name, gesture)
                finally:
                    register.close()
                result.update(accepted=outcome.accepted, message=outcome.message,
                              events=[e.value for e in outcome.events])
        result["image"] = to_data_url(draw_checkin(image, match, gesture, points))
        return result

    def attendance(self, day: date) -> list[dict]:
        register = self._register()
        try:
            rows = []
            for agent in register.agents_for(day):
                s = register.summary(agent, day)
                rows.append({
                    "agent": s.agent,
                    "arrival": s.arrival.strftime("%H:%M:%S") if s.arrival else None,
                    "departure": s.departure.strftime("%H:%M:%S") if s.departure else None,
                    "pauses": s.pauses,
                    "pause_minutes": s.pause_minutes,
                    "presence_minutes": s.presence_minutes,
                    "status": s.status.value,
                    "events": [{"event": e.value, "time": t.strftime("%H:%M:%S")}
                               for e, t in register.events_for(agent, day)],
                })
            return rows
        finally:
            register.close()

    def attendance_csv(self, day: date) -> str:
        register = self._register()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                return register.export_csv(day, Path(tmp) / "presence.csv").read_text(encoding="utf-8")
        finally:
            register.close()


GESTURE_LABELS = {
    "pouce_haut": "Pouce en haut : arrivee",
    "pouce_cote": "Pouce sur le cote : pause",
    "pouce_bas": "Pouce en bas : fin",
    "aucun": "Aucun geste",
}


def draw_checkin(image: np.ndarray, match, gesture, points) -> np.ndarray:
    view = image.copy()
    thickness = max(2, round(max(view.shape[:2]) / 400))
    font = max(0.5, max(view.shape[:2]) / 1300)
    if match:
        x, y, w, h = match.box
        color = GREEN if match.name else ORANGE
        cv2.rectangle(view, (x, y), (x + w, y + h), color, thickness)
        _label(view, f"{match.name or 'Inconnu'} ({match.score:.2f})", (x, y), color, font, thickness)
    if points:
        for px, py in points:
            cv2.circle(view, (int(px), int(py)), thickness + 2, ORANGE, -1)
        xs, ys = [pt[0] for pt in points], [pt[1] for pt in points]
        _label(view, GESTURE_LABELS[gesture.value], (int(min(xs)), int(max(ys))), ORANGE, font, thickness,
               below=True)
    return view


def draw(image: np.ndarray, result: Analysis) -> np.ndarray:
    view = image.copy()
    thickness = max(2, round(max(view.shape[:2]) / 400))
    font = max(0.5, max(view.shape[:2]) / 1300)
    for person in result.persons:
        x1, y1, x2, y2 = person["box"]
        color = GREEN if person["authorized"] else RED
        cv2.rectangle(view, (x1, y1), (x2, y2), color, thickness)
        label = f"AUTORISE : {person['authorized']}" if person["authorized"] else f"INTRUS {person['confidence']:.0%}"
        _label(view, label, (x1, y2), color, font, thickness, below=True)
    for face in result.faces:
        x, y, w, h = face.box
        color = GREEN if face.name else ORANGE
        cv2.rectangle(view, (x, y), (x + w, y + h), color, thickness)
        _label(view, f"{face.name or 'Inconnu'} ({face.score:.2f})", (x, y), color, font, thickness)
    return view


def _label(view, text, origin, color, font, thickness, below=False):
    (tw, th), base = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font, 1)
    x = max(0, min(origin[0], view.shape[1] - tw - 6))
    y = origin[1] + th + 8 if below else origin[1] - 4
    y = min(max(th + 6, y), view.shape[0] - 4)
    cv2.rectangle(view, (x, y - th - 6), (x + tw + 6, y + base - 2), color, -1)
    cv2.putText(view, text, (x + 3, y - 3), cv2.FONT_HERSHEY_SIMPLEX, font, (255, 255, 255), max(1, thickness // 2))


def create_app(engine):
    from flask import Flask, Response, jsonify, request, send_from_directory

    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

    @app.get("/")
    def index():
        return send_from_directory(STATIC_DIR, "admin.html")

    @app.get("/api/agents")
    def agents():
        return jsonify(engine.agents())

    @app.post("/api/agents")
    def enroll():
        name = " ".join(request.form.get("name", "").split())
        if not name or len(name) > 60:
            return jsonify(error="Nom obligatoire (60 caracteres max)"), 400
        files = request.files.getlist("photos")
        if not files:
            return jsonify(error="Ajoute au moins une photo"), 400
        result = engine.enroll(name, [(f.filename, decode_image(f.read())) for f in files])
        return jsonify(result), (201 if result["enrolled"] else 422)

    @app.delete("/api/agents/<path:name>")
    def remove(name):
        if not engine.remove(name):
            return jsonify(error="Agent inconnu"), 404
        return "", 204

    @app.post("/api/analyze")
    def analyze():
        upload = request.files.get("image")
        image = decode_image(upload.read()) if upload else None
        if image is None:
            return jsonify(error="Image manquante ou illisible"), 400
        return jsonify(engine.analyze(image).to_dict())

    @app.post("/api/checkin")
    def checkin():
        upload = request.files.get("image")
        image = decode_image(upload.read()) if upload else None
        if image is None:
            return jsonify(error="Image manquante ou illisible"), 400
        return jsonify(engine.checkin(image))

    def requested_day():
        try:
            return date.fromisoformat(request.args["day"]) if request.args.get("day") else date.today()
        except ValueError:
            return None

    @app.get("/api/attendance")
    def attendance():
        day = requested_day()
        if day is None:
            return jsonify(error="Date invalide (AAAA-MM-JJ)"), 400
        return jsonify({"day": day.isoformat(), "agents": engine.attendance(day)})

    @app.get("/api/attendance.csv")
    def attendance_csv():
        day = requested_day()
        if day is None:
            return jsonify(error="Date invalide (AAAA-MM-JJ)"), 400
        return Response(engine.attendance_csv(day), mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment; filename=presence_{day.isoformat()}.csv"})

    @app.errorhandler(413)
    def too_large(_):
        return jsonify(error="Fichiers trop lourds (25 Mo max au total)"), 413

    return app
