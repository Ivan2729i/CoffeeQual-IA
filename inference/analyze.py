from collections import Counter
from inference.predictor import get_model
from inference.grading import grade_from_counts

PRIMARY = {"black", "foreign", "infested", "sour"}
SECONDARY = {"broken", "fraghusk", "green", "husk", "immature"}

def analyze_image(source, conf=0.25):
    """
    source puede ser:
    - str (ruta a imagen)
    - numpy array (frame BGR de OpenCV)  [cuando tengas cámaras]
    """
    model = get_model()
    results = model.predict(source=source, conf=conf, verbose=False)
    boxes = results[0].boxes
    cls_ids = boxes.cls.int().tolist()

    names = model.names
    cls_names = [names[i] for i in cls_ids]
    counts = dict(Counter(cls_names))

    grading = grade_from_counts(counts)
    return {
        "counts": counts,
        **grading,
    }
