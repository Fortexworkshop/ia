from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"
DATA_DIR = ROOT / "data"

FACE_DETECTOR_MODEL = MODELS_DIR / "face_detection_yunet_2023mar.onnx"
FACE_RECOGNIZER_MODEL = MODELS_DIR / "face_recognition_sface_2021dec.onnx"
HAND_MODEL = MODELS_DIR / "hand_landmarker.task"

FACES_DB = DATA_DIR / "faces.npz"
ATTENDANCE_DB = DATA_DIR / "presence.db"

MODEL_URLS = {
    FACE_DETECTOR_MODEL: "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    FACE_RECOGNIZER_MODEL: "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
    HAND_MODEL: "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task",
}
