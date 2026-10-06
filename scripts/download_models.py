"""Telecharge les modeles pre-entraines (YuNet, SFace, MediaPipe Hand Landmarker, YOLOv8n)."""

import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from presence.config import MODEL_URLS, MODELS_DIR  # noqa: E402

YOLO_URL = "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8n.pt"


def main() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    for path, url in {**MODEL_URLS, MODELS_DIR / "yolov8n.pt": YOLO_URL}.items():
        if path.exists():
            print(f"[ok] {path.name} deja present")
            continue
        print(f"[..] telechargement de {path.name}")
        urllib.request.urlretrieve(url, path)
        print(f"[ok] {path.name} ({path.stat().st_size // 1024} Ko)")


if __name__ == "__main__":
    main()
