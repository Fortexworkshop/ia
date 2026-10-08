"""SENTINEL-X : detection d'intrus sur la webcam USB du PC Serveur Local.

python scripts/sentinel_vision.py                    # webcam 0, fenetre + flux http://<ip>:8081/video
python scripts/sentinel_vision.py --whitelist        # visages enregistres (scripts/enroll.py) = autorises
python scripts/sentinel_vision.py --no-window        # sans affichage (serveur, Docker)
python scripts/sentinel_vision.py --source video.mp4 # rejouer une video de test
python scripts/sentinel_vision.py --pointage   # + journal de presence : detection, pouce haut = entree, pouce bas = sortie

Touche Q pour quitter (mode fenetre).
"""

import argparse
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from presence import config as presence_config  # noqa: E402
from presence.gestures import Gesture, HandGestureDetector  # noqa: E402
from presence.stabilizer import GestureStabilizer  # noqa: E402
from sentinel import config  # noqa: E402
from sentinel.roles import RoleBook  # noqa: E402
from sentinel.whitelist import LiveWhitelist  # noqa: E402
from sentinel.alerts import AlertClient, PresenceClient, Severity, build_alert, build_presence  # noqa: E402
from sentinel.vision import (  # noqa: E402
    IntruderTimer, PersonDetector, StreamState, annotate, known_faces_in, mark_authorized, prepare_frame,
    start_stream_server,
)


def load_whitelist():
    from presence import config as presence_config
    from presence.faces import FaceDatabase, FaceRecognizer

    db = FaceDatabase(presence_config.FACES_DB)
    # Liste vide autorisee : tout le monde est inconnu, et les ajouts du dashboard sont pris a chaud
    print(f"Liste blanche : {', '.join(sorted(db.embeddings)) or '(vide : toute personne est inconnue)'}")
    return FaceRecognizer(str(presence_config.FACE_DETECTOR_MODEL),
                          str(presence_config.FACE_RECOGNIZER_MODEL), db)


GESTURE_LABELS = {Gesture.THUMB_UP: "pouce en haut : entree",
                  Gesture.THUMB_DOWN: "pouce en bas : sortie",
                  Gesture.THUMB_SIDE: "pouce de cote : pause"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", default="0", help="index webcam ou chemin video")
    parser.add_argument("--confidence", type=float, default=0.5)
    parser.add_argument("--imgsz", type=int, default=480, help="taille d'inference YOLO (320 = plus rapide, 640 = plus precis)")
    parser.add_argument("--intruder-delay", type=float, default=20.0,
                        help="secondes de presence NON reconnue avant l'alarme intrusion")
    parser.add_argument("--grace", type=float, default=2.0, help="perte breve toleree (s) sans remettre a zero")
    parser.add_argument("--realert", type=float, default=60.0, help="nouvelle alerte toutes les N s si l'intrus reste")
    parser.add_argument("--whitelist", action="store_true", help="ignorer les visages autorises")
    parser.add_argument("--pointage", action="store_true",
                        help="journal de presence : detection, pouce en haut = entree, pouce de cote = pause / reprise, pouce en bas = sortie")
    parser.add_argument("--gesture-frames", type=int, default=8, help="images consecutives pour valider un geste")
    parser.add_argument("--gesture-cooldown", type=float, default=10.0, help="secondes entre deux gestes")
    parser.add_argument("--gesture-every", type=int, default=2,
                        help="une detection de main toutes les N images (la main coute ~40 ms, exigence < 100 ms par trame)")
    parser.add_argument("--no-window", action="store_true")
    parser.add_argument("--host", default="0.0.0.0", help="interface du flux video")
    parser.add_argument("--port", type=int, default=config.STREAM_PORT)
    args = parser.parse_args()

    detector = PersonDetector(config.YOLO_MODEL, args.confidence, args.imgsz)
    whitelist = load_whitelist() if (args.whitelist or args.pointage) else None
    # rechargement a chaud de data/faces.npz : ajout / suppression dans « Individus » sans redemarrage
    live = LiveWhitelist(whitelist, presence_config.FACES_DB) if whitelist else None
    alerts = AlertClient(config.API_URL, config.API_TOKEN, config.API_CA_CERT)
    presence = PresenceClient(config.API_URL, config.API_TOKEN, config.API_CA_CERT)
    hands, stabilizer = None, None
    if args.pointage:
        if not presence_config.HAND_MODEL.exists():
            sys.exit(f"Modele de gestes absent ({presence_config.HAND_MODEL.name}) : "
                     "lance python scripts/download_models.py")
        hands = HandGestureDetector(str(presence_config.HAND_MODEL))
        stabilizer = GestureStabilizer(args.gesture_frames, args.gesture_cooldown)
    roles = RoleBook(config.DATA_DIR / "people.db")  # roles saisis dans la page « Individus »
    timer = IntruderTimer(args.intruder_delay, args.grace, args.realert)
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

    fps, last, was_present, gesture, gesture_tick = 0.0, time.perf_counter(), False, Gesture.NONE, 0
    paused: set[str] = set()  # personnes en pause (pouce de cote alterne pause / reprise)
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

            now = time.time()
            if live is not None and (names := live.refresh(now)) is not None:
                print(f"Liste blanche rechargee : {', '.join(names) or '(vide)'}")
            authorized = [d.authorized for d in detections if d.authorized]
            agent = authorized[0] if authorized else None

            # Journal de presence : une ligne par personne qui se presente (front montant).
            if detections and not was_present:
                presence.send(build_presence(config.NODE_ID, "detection", person=agent or ""))
            was_present = bool(detections)

            note = ""
            if stabilizer is not None:
                if gesture_tick % max(1, args.gesture_every) == 0:
                    gesture, _ = hands.detect(frame)
                gesture_tick += 1
                note = GESTURE_LABELS.get(gesture, "")
                validated = stabilizer.update(agent, gesture, now)
                if validated is Gesture.THUMB_SIDE:
                    # 1er pouce de cote = debut de pause, le suivant = retour (regle de presence/attendance.py)
                    kind = "reprise" if agent in paused else "pause"
                    paused.symmetric_difference_update({agent})
                    presence.send(build_presence(config.NODE_ID, kind, person=agent or ""))
                elif validated is not None:
                    paused.discard(agent)
                    presence.send(build_presence(
                        config.NODE_ID, "entree" if validated is Gesture.THUMB_UP else "sortie",
                        person=agent or ""))

            latency_ms = (time.perf_counter() - start) * 1000

            intruders = [d for d in detections if not d.authorized]
            if timer.update(bool(intruders), now):
                alerts.send(build_alert(
                    config.NODE_ID, "vision", "INTRUSION", Severity.CRITICAL,
                    f"Intrus : personne non reconnue depuis {timer.elapsed(now):.0f} s "
                    f"({len(intruders)} personne(s))",
                    {
                        "unrecognized_seconds": round(timer.elapsed(now)),
                        "persons": len(detections),
                        "intruders": len(intruders),
                        "authorized": [d.authorized for d in detections if d.authorized],
                        "max_confidence": round(max((d.confidence for d in intruders), default=0.0), 3),
                        "boxes": [d.box for d in intruders],
                        "latency_ms": round(latency_ms, 1),
                        "stream_port": args.port,  # image : http://<serveur>:<port>/snapshot.jpg
                    },
                ))

            tick = time.perf_counter()
            fps = 0.9 * fps + 0.1 * (1 / max(tick - last, 1e-6))
            last = tick
            if intruders and not timer.alarm and not note:
                note = f"Non reconnu : {timer.elapsed(now):.0f} / {args.intruder_delay:.0f} s"
            labels = {name: roles.label(name) for name in authorized}
            view = annotate(frame, detections, latency_ms, fps, timer.alarm, note, labels)
            state.publish(view, {
                "node_id": config.NODE_ID,
                "persons": len(detections),
                "intruders": len(intruders),
                "alarm": timer.alarm,
                "unrecognized_seconds": round(timer.elapsed(now), 1),
                "recognized": [{"name": n, "role": roles.roles().get(n, "")} for n in authorized],
                "gesture": note,
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
        presence.flush()


if __name__ == "__main__":
    main()
