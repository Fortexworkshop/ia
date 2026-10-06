"""Plateforme web : enregistrer des eleves, pointer (geste du pouce) et tester une image.

python scripts/sentinel_admin.py                 # http://localhost:5000 (cette machine uniquement)
python scripts/sentinel_admin.py --host 0.0.0.0  # accessible depuis le reseau de la table
python scripts/sentinel_admin.py --no-yolo       # visages seulement (plus rapide)
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from presence import config as presence_config  # noqa: E402
from sentinel import config  # noqa: E402
from sentinel.admin import FaceEngine, create_app  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--no-yolo", action="store_true", help="ne pas detecter les personnes entieres")
    args = parser.parse_args()

    missing = [p.name for p in (presence_config.FACE_DETECTOR_MODEL, presence_config.FACE_RECOGNIZER_MODEL,
                                presence_config.HAND_MODEL) if not p.exists()]
    if missing:
        sys.exit(f"Modeles absents ({', '.join(missing)}) : lance python scripts/download_models.py")

    engine = FaceEngine(presence_config.FACES_DB, str(presence_config.FACE_DETECTOR_MODEL),
                        str(presence_config.FACE_RECOGNIZER_MODEL), None if args.no_yolo else config.YOLO_MODEL,
                        str(presence_config.HAND_MODEL), presence_config.ATTENDANCE_DB)
    print(f"Plateforme : http://{'localhost' if args.host == '127.0.0.1' else args.host}:{args.port}")
    create_app(engine).run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    main()
