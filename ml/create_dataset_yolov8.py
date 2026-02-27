from pathlib import Path

# ========= CONFIG =========

DATASET_ROOT = Path(r"C:\Users\ivanp\OneDrive\Escritorio\My First Project.v1-nuevo_dataset4.yolov8")

# Orden original (17 clases)
ORIGINAL_NAMES = [
    'Broken', 'Cut', 'Dry cherry', 'Fade', 'Floater',
    'Full black', 'Full sour', 'Fungus damage',
    'Husk', 'Immature', 'Parchment',
    'Partial black', 'Partial sour',
    'Severe insect damage', 'Shell',
    'Slight insect damage', 'Withered'
]

# 9 clases
TARGET_NAMES = [
    'black','broken','foreign','fraghusk',
    'green','husk','immature','infested','sour'
]

TARGET_ID = {n:i for i,n in enumerate(TARGET_NAMES)}

# Mapeo 17 → 9
MAP = {
    'Broken': 'broken',
    'Cut': 'broken',

    'Full black': 'black',
    'Partial black': 'black',

    'Full sour': 'sour',
    'Partial sour': 'sour',

    'Husk': 'husk',
    'Shell': 'fraghusk',

    'Immature': 'immature',

    'Severe insect damage': 'infested',
    'Slight insect damage': 'infested',
    'Fungus damage': 'infested',

    'Dry cherry': 'foreign',
    'Parchment': 'foreign',
    'Floater': 'foreign',

    'Fade': 'green',
    'Withered': 'green'
}

ORIGINAL_ID = {name:i for i,name in enumerate(ORIGINAL_NAMES)}

def remap_file(label_path: Path):
    lines = label_path.read_text().strip().split("\n")
    new_lines = []

    for line in lines:
        parts = line.split()
        old_id = int(parts[0])
        original_class = ORIGINAL_NAMES[old_id]
        target_class = MAP[original_class]
        new_id = TARGET_ID[target_class]
        parts[0] = str(new_id)
        new_lines.append(" ".join(parts))

    label_path.write_text("\n".join(new_lines))

def main():
    for split in ["train", "valid", "test"]:
        label_dir = DATASET_ROOT / split / "labels"
        if not label_dir.exists():
            continue

        for txt in label_dir.glob("*.txt"):
            remap_file(txt)

    # actualizar data.yaml
    yaml_path = DATASET_ROOT / "data.yaml"
    yaml_text = f"""
path: {DATASET_ROOT.as_posix()}
train: train/images
val: valid/images
test: test/images
nc: 9
names: {TARGET_NAMES}
"""
    yaml_path.write_text(yaml_text.strip())

    print("Remapeo completado.")

if __name__ == "__main__":
    main()