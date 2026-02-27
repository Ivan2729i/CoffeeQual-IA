from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parent

DATASETS = [
    BASE / "datasets" / "coffee_defects",
    BASE / "datasets" / "coffee_kaggle_yolo",
    BASE / "datasets" / "coffee_beans_rf_yolo_v3",
    BASE / "datasets" / "coffee_green_v4",
]

OUT = BASE / "datasets" / "coffee_mega_merged"

NAMES = ['black','broken','foreign','fraghusk','green','husk','immature','infested','sour']


def ensure_dirs(root: Path):
    for split in ["train", "valid", "test"]:
        (root / split / "images").mkdir(parents=True, exist_ok=True)
        (root / split / "labels").mkdir(parents=True, exist_ok=True)

def copy_split(src: Path, dst: Path, split: str, prefix: str):
    src_i = src / split / "images"
    src_l = src / split / "labels"
    dst_i = dst / split / "images"
    dst_l = dst / split / "labels"

    if not src_i.exists() or not src_l.exists():
        return 0

    c = 0
    for img in src_i.glob("*.*"):
        lab = src_l / f"{img.stem}.txt"
        if not lab.exists():
            continue

        new_stem = f"{prefix}_{img.stem}"
        shutil.copy2(img, dst_i / f"{new_stem}{img.suffix.lower()}")
        shutil.copy2(lab, dst_l / f"{new_stem}.txt")
        c += 1
    return c

def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    ensure_dirs(OUT)

    total = {"train":0, "valid":0, "test":0}

    for i, ds in enumerate(DATASETS, start=1):
        prefix = f"ds{i}"
        for split in ["train", "valid", "test"]:
            total[split] += copy_split(ds, OUT, split, prefix)

    (OUT / "data.yaml").write_text(
        f"path: {OUT.as_posix()}\n"
        f"train: train/images\n"
        f"val: valid/images\n"
        f"test: test/images\n"
        f"nc: 9\n"
        f"names: {NAMES}\n",
        encoding="utf-8"
    )

    print("Mega dataset creado:", OUT)
    print("Train:", total["train"])
    print("Valid:", total["valid"])
    print("Test :", total["test"])
    print("data.yaml:", OUT / "data.yaml")

if __name__ == "__main__":
    main()