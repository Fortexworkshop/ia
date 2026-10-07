"""Reconnaissance faciale avec OpenCV : YuNet (detection) + SFace (empreinte 128 dimensions)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

# Seuil cosinus recommande par OpenCV pour SFace (au-dessus = meme personne).
DEFAULT_THRESHOLD = 0.363


@dataclass
class FaceMatch:
    name: str | None   # None = visage inconnu
    score: float
    box: tuple[int, int, int, int]  # x, y, largeur, hauteur


class FaceDatabase:
    """Empreintes faciales des agents, stockees dans un fichier .npz."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.embeddings: dict[str, np.ndarray] = {}
        if self.path.exists():
            with np.load(self.path) as data:
                self.embeddings = {name: data[name] for name in data.files}

    def add(self, name: str, embeddings: list[np.ndarray]) -> None:
        mean = np.mean([_normalize(e) for e in embeddings], axis=0)
        self.embeddings[name] = _normalize(mean)

    def remove(self, name: str) -> bool:
        return self.embeddings.pop(name, None) is not None

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(self.path, **self.embeddings)

    def best_match(self, embedding: np.ndarray, threshold: float = DEFAULT_THRESHOLD) -> tuple[str | None, float]:
        if not self.embeddings:
            return None, 0.0
        query = _normalize(embedding)
        name, score = max(
            ((n, float(np.dot(query, e))) for n, e in self.embeddings.items()), key=lambda item: item[1]
        )
        return (name if score >= threshold else None), score


class FaceRecognizer:
    def __init__(self, detector_model: str, recognizer_model: str, db: FaceDatabase,
                 threshold: float = DEFAULT_THRESHOLD):
        self.detector = cv2.FaceDetectorYN.create(detector_model, "", (320, 320), 0.8, 0.3, 5000)
        self.recognizer = cv2.FaceRecognizerSF.create(recognizer_model, "")
        self.db = db
        self.threshold = threshold

    def detect(self, frame_bgr) -> np.ndarray:
        height, width = frame_bgr.shape[:2]
        self.detector.setInputSize((width, height))
        _, faces = self.detector.detect(frame_bgr)
        return faces if faces is not None else np.empty((0, 15), dtype=np.float32)

    def embedding(self, frame_bgr, face: np.ndarray) -> np.ndarray:
        aligned = self.recognizer.alignCrop(frame_bgr, face)
        return self.recognizer.feature(aligned).flatten()

    def largest_face(self, frame_bgr) -> np.ndarray | None:
        """Le plus grand visage = la personne la plus proche de la camera."""
        faces = self.detect(frame_bgr)
        if len(faces) == 0:
            return None
        return max(faces, key=lambda f: f[2] * f[3])

    def identify(self, frame_bgr) -> FaceMatch | None:
        face = self.largest_face(frame_bgr)
        if face is None:
            return None
        name, score = self.db.best_match(self.embedding(frame_bgr, face), self.threshold)
        x, y, w, h = (int(v) for v in face[:4])
        return FaceMatch(name, score, (x, y, w, h))


def _normalize(vector: np.ndarray) -> np.ndarray:
    vector = np.asarray(vector, dtype=np.float32).flatten()
    norm = np.linalg.norm(vector)
    return vector / norm if norm else vector
