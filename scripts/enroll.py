"""Enregistre le visage d'un agent.

Depuis la webcam :   python scripts/enroll.py "Alice Martin"
Depuis des photos :  python scripts/enroll.py "Alice Martin" --images photos/alice/
Supprimer un agent : python scripts/enroll.py "Alice Martin" --remove
"""

import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from presence import config  # noqa: E402
from presence.faces import FaceDatabase, FaceRecognizer  # noqa: E402

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}


def from_images(recognizer: FaceRecognizer, folder: Path) -> list:
    embeddings = []
    for path in sorted(folder.iterdir()):
        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        image = cv2.imread(str(path))
        face = recognizer.largest_face(image) if image is not None else None
        if face is None:
            print(f"[!] aucun visage dans {path.name}")
            continue
        embeddings.append(recognizer.embedding(image, face))
        print(f"[ok] {path.name}")
    return embeddings


def from_webcam(recognizer: FaceRecognizer, camera: int, samples: int) -> list:
    cap = cv2.VideoCapture(camera)
    embeddings = []
    print(f"ESPACE = capturer ({samples} photos, bouge un peu la tete entre chaque), Q = annuler")
    while len(embeddings) < samples:
        ok, frame = cap.read()
        if not ok:
            break
        face = recognizer.largest_face(frame)
        view = frame.copy()
        if face is not None:
            x, y, w, h = (int(v) for v in face[:4])
            cv2.rectangle(view, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(view, f"{len(embeddings)}/{samples}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow("Enrolement", view)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key == ord(" ") and face is not None:
            embeddings.append(recognizer.embedding(frame, face))
    cap.release()
    cv2.destroyAllWindows()
    return embeddings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("name", help="nom de l'agent")
    parser.add_argument("--images", type=Path, help="dossier de photos de l'agent")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--remove", action="store_true", help="supprime l'agent de la base")
    args = parser.parse_args()

    db = FaceDatabase(config.FACES_DB)
    if args.remove:
        print("supprime" if db.remove(args.name) else "agent inconnu")
        db.save()
        return

    recognizer = FaceRecognizer(str(config.FACE_DETECTOR_MODEL), str(config.FACE_RECOGNIZER_MODEL), db)
    embeddings = from_images(recognizer, args.images) if args.images else from_webcam(
        recognizer, args.camera, args.samples)
    if not embeddings:
        sys.exit("Aucun visage capture, agent non enregistre.")
    db.add(args.name, embeddings)
    db.save()
    print(f"{args.name} enregistre ({len(embeddings)} images). Agents : {', '.join(sorted(db.embeddings))}")


if __name__ == "__main__":
    main()
