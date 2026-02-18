from pathlib import Path
from collections import Counter
from inference.predictor import predict, get_model

BASE = Path(__file__).resolve().parent.parent
img_dir = BASE / "ml" / "datasets" / "coffee_defects" / "test" / "images"

first = next(img_dir.glob("*.*"))

model = get_model()
names = model.names  # dict: {id: "nombre"}

results = predict(str(first), conf=0.25)
boxes = results[0].boxes

cls_ids = boxes.cls.int().tolist()
confs = boxes.conf.tolist()

print("Imagen:", first)
print("Detecciones:", len(cls_ids))

# lista detallada
for cid, cf in zip(cls_ids, confs):
    print(f"- {names[cid]} ({cid}) conf={cf:.3f}")

# conteo por clase
counts = Counter(cls_ids)
print("\nConteo por clase:")
for cid, n in counts.items():
    print(f"  {names[cid]}: {n}")
