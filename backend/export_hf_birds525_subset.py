import argparse
import json
from pathlib import Path
from urllib.request import urlretrieve

import pyarrow.parquet as pq


DATASET_BASE = "https://huggingface.co/datasets/yashikota/birds-525-species-image-classification/resolve/main/data"
PARQUET_FILES = [
    "train-00000-of-00004.parquet",
    "train-00001-of-00004.parquet",
    "train-00002-of-00004.parquet",
    "train-00003-of-00004.parquet",
    "validation-00000-of-00001.parquet",
    "test-00000-of-00001.parquet",
]

LABEL_MAP = {
    "ABBOTTS BABBLER": "ABBOTTS BABBLER",
    "ABBOTTS BOOBY": "ABBOTTS BOOBY",
    "ABYSSINIAN GROUND HORNBILL": "ABYSSINIAN GROUND HORNBILL",
    "AFRICAN CROWNED CRANE": "AFRICAN CROWNED CRANE",
    "AFRICAN EMERALD CUCKOO": "AFRICAN EMERALD CUCKOO",
    "AFRICAN FIREFINCH": "AFRICAN FIREFINCH",
    "OYSTER CATCHER": "AFRICAN OYSTER CATCHER",
    "ALBATROSS": "ALBATROSS",
    "ALBERTS TOWHEE": "ALBERTS TOWHEE",
    "ALEXANDRINE PARAKEET": "ALEXANDRINE PARAKEET",
    "AMERICAN ROBIN": "AMERICAN ROBIN",
    "BALD EAGLE": "BALD EAGLE",
    "BARN SWALLOW": "BARN SWALLOW",
    "BLUE JAY": "BLUE JAY",
    "COMMON RAVEN": "COMMON RAVEN",
    "COMMON STARLING": "EUROPEAN STARLING",
    "BLUE HERON": "GREAT BLUE HERON",
    "HOUSE SPARROW": "HOUSE SPARROW",
    "MALLARD DUCK": "MALLARD",
    "MOURNING DOVE": "MOURNING DOVE",
    "NORTHERN CARDINAL": "NORTHERN CARDINAL",
    "RED TAILED HAWK": "RED-TAILED HAWK",
    "ROCK DOVE": "ROCK PIGEON",
    "SNOWY EGRET": "SNOWY EGRET",
    "GOLDEN EAGLE": "GOLDEN EAGLE",
    "RED SHOULDERED HAWK": "RED-SHOULDERED HAWK",
    "OSPREY": "OSPREY",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a Birds 525 subset from Hugging Face parquet files.")
    parser.add_argument("--parquet-dir", default=Path(r"D:\AFYP\datasets\birds525_hf_parquet\data"), type=Path)
    parser.add_argument("--output-dir", default=Path(r"D:\AFYP\datasets\birds525_subset"), type=Path)
    parser.add_argument("--max-images-per-class", default=140, type=int)
    parser.add_argument("--download", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.parquet_dir.mkdir(parents=True, exist_ok=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.download:
        download_parquets(args.parquet_dir)

    label_names = read_label_names(args.parquet_dir / first_existing_parquet(args.parquet_dir))
    source_to_target = {
        index: LABEL_MAP[name]
        for index, name in enumerate(label_names)
        if name in LABEL_MAP
    }
    if not source_to_target:
        raise RuntimeError("No mapped labels found in Birds 525 parquet metadata.")

    counts: dict[str, int] = {}
    for parquet_name in PARQUET_FILES:
        parquet_path = args.parquet_dir / parquet_name
        if not parquet_path.exists():
            continue
        table = pq.read_table(parquet_path, columns=["image", "label"])
        labels = table["label"].to_pylist()
        images = table["image"].to_pylist()
        for image, label in zip(images, labels):
            target_label = source_to_target.get(int(label))
            if not target_label:
                continue
            current = counts.get(target_label, 0)
            if current >= args.max_images_per_class:
                continue
            target_dir = args.output_dir / target_label
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / f"{current + 1:04d}.jpg"
            image_bytes = image.get("bytes") if isinstance(image, dict) else None
            if not image_bytes:
                continue
            target_path.write_bytes(image_bytes)
            counts[target_label] = current + 1

    (args.output_dir / "export_manifest.json").write_text(
        json.dumps(
            {
                "source": "Hugging Face mirror of Kaggle Birds 525",
                "label_map": LABEL_MAP,
                "class_counts": counts,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    for class_name, count in sorted(counts.items()):
        print(f"{class_name}: {count}")
    print(f"Exported {sum(counts.values())} images across {len(counts)} classes to {args.output_dir}")


def download_parquets(parquet_dir: Path) -> None:
    for parquet_name in PARQUET_FILES:
        target = parquet_dir / parquet_name
        if target.exists() and target.stat().st_size > 0:
            print(f"Already downloaded: {target}")
            continue
        url = f"{DATASET_BASE}/{parquet_name}"
        print(f"Downloading {url}")
        urlretrieve(url, target)


def first_existing_parquet(parquet_dir: Path) -> str:
    for parquet_name in PARQUET_FILES:
        if (parquet_dir / parquet_name).exists():
            return parquet_name
    raise FileNotFoundError(f"No parquet files found in {parquet_dir}")


def read_label_names(parquet_path: Path) -> list[str]:
    metadata = pq.ParquetFile(parquet_path).metadata.metadata or {}
    payload = json.loads(metadata[b"huggingface"].decode("utf-8"))
    return payload["info"]["features"]["label"]["names"]


if __name__ == "__main__":
    main()
