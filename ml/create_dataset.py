import os
import random
import shutil
from pathlib import Path
from PIL import Image

# =========================
# CONFIG
# =========================

# Carpeta raíz donde están las carpetas del Kaggle: Broken/, Cut/, Dry Cherry/, ...
KAGGLE_ROOT = r"C:\Users\ivanp\OneDrive\Escritorio\archive"

# Carpeta destino
OUT_ROOT = r"C:\Users\ivanp\OneDrive\Escritorio\dataset_yolo"

# Split
TRAIN_RATIO = 0.8  # 80% train, 20% valid
SEED = 42

# Caja automática (en proporción al tamaño de la imagen)
# Ej: 0.90 significa caja de 90% del ancho/alto, centrada.
BOX_SCALE = 0.90

# Tus clases
TARGET_NAMES = ['black', 'broken', 'foreign', 'fraghusk', 'green', 'husk', 'immature', 'infested', 'sour']
TARGET_ID = {name: i for i, name in enumerate(TARGET_NAMES)}

# =========================
# MAPE0 Kaggle(17) -> 9 clases
# =========================

MAP = {
    "Full Black": "black",
    "Partial Black": "black",

    "Broken": "broken",
    "Cut": "broken",

    "Husk": "husk",
    "Shell": "fraghusk",

    "Immature": "immature",
    "Withered": "green",

    "Severe Insect Damage": "infested",
    "Slight Insect Damage": "infested",
    "Fungus Damage": "infested",

    "Full Sour": "sour",
    "Partial Sour": "sour",

    "Dry Cherry": "foreign",
    "Parchment": "foreign",
    "Floater": None,                 # si no sirve, se salta
    "Fade": None                     # si no sirve, se salta
}

# =========================
# HELPERS
# =========================

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

def yolo_line(class_id: int, w: int, h: int, scale: float) -> str:
    bw = scale
    bh = scale
    xc = 0.5
    yc = 0.5
    return f"{class_id} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}\n"

def safe_mkdir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def is_image(p: Path) -> bool:
    return p.suffix.lower() in IMG_EXTS

# =========================
# MAIN
# =========================

def main():
    random.seed(SEED)

    kaggle_root = Path(KAGGLE_ROOT)
    out_root = Path(OUT_ROOT)

    if not kaggle_root.exists():
        raise FileNotFoundError(f"No existe KAGGLE_ROOT: {kaggle_root}")

    # Crear output dirs
    train_img = out_root / "train" / "images"
    train_lbl = out_root / "train" / "labels"
    val_img   = out_root / "valid" / "images"
    val_lbl   = out_root / "valid" / "labels"
    for p in [train_img, train_lbl, val_img, val_lbl]:
        safe_mkdir(p)

    # Recolectar todos los items
    items = []
    unknown_folders = []
    skipped = 0

    for class_dir in kaggle_root.iterdir():
        if not class_dir.is_dir():
            continue
        kaggle_class = class_dir.name.strip()

        if kaggle_class not in MAP:
            unknown_folders.append(kaggle_class)
            continue

        target = MAP[kaggle_class]
        if target is None:
            # skipped
            skipped += 1
            continue

        if target not in TARGET_ID:
            raise ValueError(f"MAP '{kaggle_class}' -> '{target}' pero '{target}' no está en TARGET_NAMES")

        for img_path in class_dir.rglob("*"):
            if img_path.is_file() and is_image(img_path):
                items.append((img_path, target))

    if unknown_folders:
        print("Carpetas Kaggle NO mapeadas:")
        for f in sorted(unknown_folders):
            print(" -", f)

    if not items:
        raise RuntimeError("No hay imágenes para procesar. Revisa rutas y extensiones.")

    random.shuffle(items)
    split_idx = int(len(items) * TRAIN_RATIO)
    train_items = items[:split_idx]
    val_items = items[split_idx:]

    print(f"Total imágenes usadas: {len(items)}")
    print(f"Train: {len(train_items)} | Valid: {len(val_items)}")
    print(f"Clases saltadas (None): {skipped}")

    def process(items_list, img_out: Path, lbl_out: Path, prefix: str):
        for idx, (src_img, target_name) in enumerate(items_list):
            # nombre único
            new_name = f"{prefix}_{idx:06d}{src_img.suffix.lower()}"
            dst_img = img_out / new_name
            dst_lbl = lbl_out / f"{Path(new_name).stem}.txt"

            shutil.copy2(src_img, dst_img)

            # leer tamaño
            with Image.open(dst_img) as im:
                w, h = im.size

            class_id = TARGET_ID[target_name]
            dst_lbl.write_text(yolo_line(class_id, w, h, BOX_SCALE), encoding="utf-8")

    process(train_items, train_img, train_lbl, "train")
    process(val_items, val_img, val_lbl, "val")

    # Crear data.yaml
    data_yaml = out_root / "data.yaml"
    data_yaml.write_text(
        f"path: {out_root.as_posix()}\n"
        f"train: train/images\n"
        f"val: valid/images\n"
        f"nc: {len(TARGET_NAMES)}\n"
        f"names: {TARGET_NAMES}\n",
        encoding="utf-8"
    )

    print("\nLISTO. Dataset YOLO creado en:", out_root)
    print("data.yaml:", data_yaml)

if __name__ == "__main__":
    main()