"""Mesure la latence de la vision sur la vraie webcam (exigence du sujet : < 100 ms par trame).

python scripts/bench_vision.py                 # webcam 0, tailles 640 / 480 / 416 / 320
python scripts/bench_vision.py --frames 100 --source 1

Latence mesuree = bridage 640x480 + inference YOLOv8n (comme dans sentinel_vision.py).
"""

import argparse
import statistics
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sentinel import config  # noqa: E402
from sentinel.vision import PersonDetector, prepare_frame  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", default="0")
    parser.add_argument("--frames", type=int, default=60)
    parser.add_argument("--sizes", default="640,480,416,320")
    args = parser.parse_args()

    cap = cv2.VideoCapture(int(args.source) if args.source.isdigit() else args.source)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_SIZE[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_SIZE[1])
    ok, frame = cap.read()
    if not ok:
        sys.exit("Webcam inaccessible (deja utilisee par un autre programme ?)")
    print(f"Webcam : {frame.shape[1]}x{frame.shape[0]}, {args.frames} images par taille\n")
    print(f"{'imgsz':<7}{'moyenne':>9}{'p95':>8}{'max':>8}{'fps':>7}  {'< 100 ms':<9}personnes")

    for size in (int(s) for s in args.sizes.split(",")):
        detector = PersonDetector(config.YOLO_MODEL, 0.5, size)
        latencies, persons = [], []
        for _ in range(args.frames):
            ok, frame = cap.read()
            if not ok:
                break
            start = time.perf_counter()
            detections = detector.detect(prepare_frame(frame, config.FRAME_SIZE))
            latencies.append((time.perf_counter() - start) * 1000)
            persons.append(len(detections))
        latencies.sort()
        mean = statistics.mean(latencies)
        p95 = latencies[int(0.95 * (len(latencies) - 1))]
        verdict = "oui" if p95 < 100 else "non"
        print(f"{size:<7}{mean:>7.0f}ms{p95:>6.0f}ms{latencies[-1]:>6.0f}ms{1000 / mean:>7.1f}  {verdict:<9}"
              f"{statistics.mean(persons):.1f} en moyenne")
    cap.release()


if __name__ == "__main__":
    main()
