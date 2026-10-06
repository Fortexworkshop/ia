"""Borne de presence : l'eleve se place devant la camera et fait un geste.

Pouce en haut = arrivee | pouce de cote = pause pipi (aller / retour) | pouce en bas = fin.
Touche Q pour quitter.
"""

import argparse
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from presence import config  # noqa: E402
from presence.attendance import AttendanceRegister  # noqa: E402
from presence.faces import FaceDatabase, FaceRecognizer  # noqa: E402
from presence.gestures import Gesture, HandGestureDetector  # noqa: E402
from presence.stabilizer import GestureStabilizer  # noqa: E402

LABELS = {
    Gesture.THUMB_UP: "Pouce haut : arrivee",
    Gesture.THUMB_DOWN: "Pouce bas : fin",
    Gesture.THUMB_SIDE: "Pouce cote : pause",
    Gesture.NONE: "",
}
GREEN, RED, WHITE, ORANGE = (0, 200, 0), (0, 0, 220), (255, 255, 255), (0, 165, 255)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--frames", type=int, default=8, help="images consecutives pour valider un geste")
    parser.add_argument("--cooldown", type=float, default=5.0, help="secondes entre deux gestes d'un eleve")
    args = parser.parse_args()

    db = FaceDatabase(config.FACES_DB)
    if not db.embeddings:
        sys.exit("Aucun eleve enregistre. Lance d'abord scripts/enroll.py")

    faces = FaceRecognizer(str(config.FACE_DETECTOR_MODEL), str(config.FACE_RECOGNIZER_MODEL), db)
    hands = HandGestureDetector(str(config.HAND_MODEL))
    register = AttendanceRegister(config.ATTENDANCE_DB)
    stabilizer = GestureStabilizer(args.frames, args.cooldown)

    cap = cv2.VideoCapture(args.camera)
    message, message_color, message_until = "", WHITE, 0.0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.flip(frame, 1)  # effet miroir, plus naturel pour l'eleve
            now = time.time()

            match = faces.identify(frame)
            gesture, points = hands.detect(frame)
            student = match.name if match else None
            validated = stabilizer.update(student, gesture, now)

            if validated:
                outcome = register.handle(student, validated)
                print(outcome.message)
                message, message_until = outcome.message, now + 3
                message_color = GREEN if outcome.accepted else RED

            if match:
                x, y, w, h = match.box
                color = GREEN if match.name else RED
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                label = f"{match.name} ({match.score:.2f})" if match.name else "Inconnu"
                cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            if points:
                for px, py in points:
                    cv2.circle(frame, (int(px), int(py)), 3, ORANGE, -1)
            if gesture is not Gesture.NONE and student:
                cv2.putText(frame, LABELS[gesture], (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, ORANGE, 2)
                cv2.rectangle(frame, (10, 40), (10 + int(200 * stabilizer.progress()), 50), ORANGE, -1)
            if now < message_until:
                cv2.putText(frame, message, (10, frame.shape[0] - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, message_color, 2)

            cv2.imshow("Presence IA", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        hands.close()
        register.close()


if __name__ == "__main__":
    main()
