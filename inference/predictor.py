from pathlib import Path
from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "ml" / "weights" / "coffeequal_best.pt"

_model = None

def get_model():
    global _model
    if _model is None:
        _model = YOLO(str(MODEL_PATH))
    return _model

def predict(image_path: str, conf: float = 0.25):
    model = get_model()
    results = model.predict(source=image_path, conf=conf, verbose=False)
    return results
