"""SENTINEL-X : detection d'intrus sur la webcam USB du PC Serveur Local.

python scripts/sentinel_vision.py                    # webcam 0, fenetre + flux http://<ip>:8081/video
python scripts/sentinel_vision.py --whitelist        # visages enregistres (scripts/enroll.py) = autorises
python scripts/sentinel_vision.py --no-window        # sans affichage (serveur, Docker)
python scripts/sentinel_vision.py --source video.mp4 # rejouer une video de test

Touche Q pour quitter (mode fenetre).
"""

import argparse
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sentinel import config  # noqa: E402
from sentinel.alerts import AlertClient, Severity, build_alert  # noqa: E402
from sentinel.debounce import Debouncer  # noqa: E402
from sentinel.vision import (  # noqa: E402
    PersonDetector, StreamState, annotate, known_faces_in, mark_authorized, prepare_frame,
    start_stream_server,
)


def load_whitelist():
    from presence import config as presence_config
    from presence.faces import FaceDatabase, FaceRecognizer

    db = FaceDatabase(presence_config.FACES_DB)
    if not db.embeddings:
        sys.exit("Liste blanche vide : enregistre d'abord les personnes autorisees avec scripts/enroll.py")
    print(f"Liste blanche : {', '.join(sorted(db.embeddings))}")
    return FaceRecognizer(str(presence_config.FACE_DETECTOR_MODEL),
                          str(presence_config.FACE_RECOGNIZER_MODEL), db)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", default="0", help="index webcam ou chemin video")
    parser.add_argument("--confidence", type=float, default=0.5)
    parser.add_argument("--imgsz", type=int, default=480, help="taille d'inference YOLO (320 = plus rapide, 640 = plus precis)")
    parser.add_argument("--frames", type=int, default=5, help="images consecutives avant alerte")
    parser.add_argument("--cooldown", type=float, default=10.0, help="secondes entre deux alertes")
    parser.add_argument("--whitelist", action="store_true", help="ignorer les visages autorises")
    parser.add_argument("--no-window", action="store_true")
    parser.add_argument("--host", default="0.0.0.0", help="interface du flux video")
    parser.add_argument("--port", type=int, default=config.STREAM_PORT)
    args = parser.parse_args()

    detector = PersonDetector(config.YOLO_MODEL, args.confidence, args.imgsz)
    whitelist = load_whitelist() if args.whitelist else None
    alerts = AlertClient(config.API_URL, config.API_TOKEN, config.API_CA_CERT)
    debouncer = Debouncer(args.frames, args.cooldown)
    state = StreamState()
    start_stream_server(state, args.host, args.port)
    print(f"Flux video : http://<ip-serveur>:{args.port}/video  (statut : /status)")
    if not config.API_URL:
        print("[i] SENTINEL_API_URL non defini : alertes affichees en console uniquement")

    source = int(args.source) if args.source.isdigit() else args.source
    cap = cv2.VideoCapture(source)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_SIZE[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_SIZE[1])
    if not cap.isOpened():
        sys.exit(f"Impossible d'ouvrir la source video {args.source}")

    fps, last = 0.0, time.perf_counter()
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            start = time.perf_counter()
            frame = prepare_frame(frame, config.FRAME_SIZE)
            detections = detector.detect(frame)
            if whitelist and detections:
                mark_authorized(detections, known_faces_in(whitelist, frame))
            latency_ms = (time.perf_counter() - start) * 1000

            intruders = [d for d in detections if not d.authorized]
            now = time.time()
            if debouncer.update(bool(intruders), now):
                alerts.send(build_alert(
                    config.NODE_ID, "vision", "INTRUSION", Severity.CRITICAL,
                    f"Presence humaine suspecte detectee ({len(intruders)} personne(s))",
                    {
                        "persons": len(detections),
                        "intruders": len(intruders),
                        "authorized": [d.authorized for d in detections if d.authorized],
                        "max_confidence": round(max(d.confidence for d in intruders), 3),
                        "boxes": [d.box for d in intruders],
                        "latency_ms": round(latency_ms, 1),
                        "stream_port": args.port,  # image : http://<serveur>:<port>/snapshot.jpg
                    },
                ))

            tick = time.perf_counter()
            fps = 0.9 * fps + 0.1 * (1 / max(tick - last, 1e-6))
            last = tick
            view = annotate(frame, detections, latency_ms, fps, debouncer.active)
            state.publish(view, {
                "node_id": config.NODE_ID,
                "persons": len(detections),
                "intruders": len(intruders),
                "alarm": debouncer.active,
                "latency_ms": round(latency_ms, 1),
                "fps": round(fps, 1),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            })

            if not args.no_window:
                cv2.imshow("SENTINEL-X Vision", view)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        cv2.destroyAllWindows()
        alerts.flush()


if __name__ == "__main__":
    main()
