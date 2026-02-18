from pathlib import Path
from inference.analyze import analyze_image

BASE = Path(__file__).resolve().parent.parent
img_dir = BASE / "ml" / "datasets" / "coffee_defects" / "test" / "images"
first = next(img_dir.glob("*.*"))

res = analyze_image(str(first), conf=0.25)
print(first.name)
print(res)
