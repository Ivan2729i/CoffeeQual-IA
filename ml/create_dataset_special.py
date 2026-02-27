from pathlib import Path
import shutil
from PIL import Image

# ========= CONFIG =========

# Raíz del zip extraído
SRC_ROOT = Path(r"C:\Users\ivanp\OneDrive\Escritorio\coffee beans.v1-nuevo_dataset.folder")

# Destino YOLO
OUT_ROOT = Path(r"C:\Users\ivanp\OneDrive\Escritorio\coffee_beans_rf_yolo")

# Caja automática (centrada) 90% del ancho/alto
BOX_SCALE = 0.90

TARGET_NAMES = ['black','broken','foreign','fraghusk','green','husk','immature','infested','sour']
TARGET_ID = {n:i for i,n in enumerate(TARGET_NAMES)}

# Remapeo: carpeta original ->  clase (o None para ignorar)
MAP = {
    "Full_Black": "black",
    "Partial_Black": "black",

    "Broken": "broken",

    "Husk": "husk",
    "Shell": "fraghusk",

    "Immature": "immature",

    "Full_Sour": "sour",
    "Partial_Sour": "sour",

    "Severe_Insect_Damage": "infested",
    "Slight_Insect_Damage": "infested",
    "Fungus_Damage": "infested",

    "Dry_Cherry": "foreign",
    "Parchment": "foreign",
    "Floater": "foreign",

    "Withered": "green",

    "Unlabeled": None,
}

IMG_EXTS = {".jpg",".jpeg",".png",".bmp",".webp"}

def yolo_line(class_id: int, scale: float) -> str:
    return f"{class_id} 0.500000 0.500000 {scale:.6f} {scale:.6f}\n"

def ensure_dirs(root: Path):
    for split in ["train", "valid", "test"]:
        (root / split / "images").mkdir(parents=True, exist_ok=True)
        (root / split / "labels").mkdir(parents=True, exist_ok=True)

def is_image(p: Path) -> bool:
    return p.suffix.lower() in IMG_EXTS

def convert_split(split: str):
    src_split = SRC_ROOT / split
    if not src_split.exists():
        print(f"No existe split {split}, salto.")
        return

    out_img = OUT_ROOT / split / "images"
    out_lbl = OUT_ROOT / split / "labels"

    idx = 0
    for class_dir in src_split.iterdir():
        if not class_dir.is_dir():
            continue

        cls_name = class_dir.name.strip()
        if cls_name not in MAP:
            print(f"Clase no mapeada: {cls_name} ")
            continue

        target = MAP[cls_name]
        if target is None:
            continue

        class_id = TARGET_ID[target]

        for img in class_dir.rglob("*"):
            if not img.is_file() or not is_image(img):
                continue

            new_stem = f"{split}_{idx:07d}"
            dst_img = out_img / f"{new_stem}{img.suffix.lower()}"
            dst_lbl = out_lbl / f"{new_stem}.txt"

            shutil.copy2(img, dst_img)

            # forzar lectura para asegurar que la imagen no está corrupta
            with Image.open(dst_img) as im:
                im.verify()

            dst_lbl.write_text(yolo_line(class_id, BOX_SCALE), encoding="utf-8")
            idx += 1

    print(f" {split}: {idx} imágenes convertidas")

def main():
    if not SRC_ROOT.exists():
        raise FileNotFoundError(f"No existe SRC_ROOT: {SRC_ROOT}")

    if OUT_ROOT.exists():
        shutil.rmtree(OUT_ROOT)

    ensure_dirs(OUT_ROOT)

    for split in ["train", "valid", "test"]:
        convert_split(split)

    # data.yaml
    (OUT_ROOT / "data.yaml").write_text(
        f"path: {OUT_ROOT.as_posix()}\n"
        f"train: train/images\n"
        f"val: valid/images\n"
        f"test: test/images\n"
        f"nc: {len(TARGET_NAMES)}\n"
        f"names: {TARGET_NAMES}\n",
        encoding="utf-8"
    )

    print("\nListo dataset YOLO:", OUT_ROOT)
    print("data.yaml:", OUT_ROOT / "data.yaml")

if __name__ == "__main__":
    main()