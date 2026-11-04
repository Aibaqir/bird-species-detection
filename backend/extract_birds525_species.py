import argparse
import io
import json
import shutil
from collections import defaultdict
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
from PIL import Image, ImageOps, UnidentifiedImageError


PARQUET_FILES = [
    "train-00000-of-00004.parquet",
    "train-00001-of-00004.parquet",
    "train-00002-of-00004.parquet",
    "train-00003-of-00004.parquet",
    "validation-00000-of-00001.parquet",
    "test-00000-of-00001.parquet",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract one or more species folders from the Birds 525 parquet mirror.")
    parser.add_argument("--parquet-dir", default=Path(r"D:\AFYP\datasets\birds525_hf_parquet\data"), type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--species", nargs="+", required=True, help="Birds 525 class names, e.g. BLACK BAZA")
    parser.add_argument("--max-images-per-class", default=200, type=int)
    parser.add_argument("--min-width", default=160, type=int)
    parser.add_argument("--min-height", default=160, type=int)
    parser.add_argument("--min-blur-score", default=40.0, type=float)
    parser.add_argument("--duplicate-distance", default=4, type=int)
    parser.add_argument("--clear-output", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.clear_output and args.output_dir.exists():
        shutil.rmtree(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    label_names = read_label_names(args.parquet_dir / first_existing_parquet(args.parquet_dir))
    requested = [name.strip().upper() for name in args.species]
    missing = [name for name in requested if name not in label_names]
    if missing:
        raise ValueError(f"Species not found in Birds 525 labels: {missing}")

    wanted_indexes = {label_names.index(name): name for name in requested}
    counts: dict[str, int] = defaultdict(int)
    rejected: dict[str, int] = defaultdict(int)
    hashes_by_class: dict[str, list[int]] = defaultdict(list)

    for parquet_name in PARQUET_FILES:
        parquet_path = args.parquet_dir / parquet_name
        if not parquet_path.exists():
            continue
        parquet = pq.ParquetFile(parquet_path)
        for batch in parquet.iter_batches(columns=["image", "label"], batch_size=512):
            images = batch.column(0).to_pylist()
            labels = batch.column(1).to_pylist()
            for image, label in zip(images, labels):
                class_name = wanted_indexes.get(int(label))
                if not class_name:
                    continue
                if counts[class_name] >= args.max_images_per_class:
                    continue
                image_bytes = image.get("bytes") if isinstance(image, dict) else None
                if not image_bytes:
                    rejected["missing_bytes"] += 1
                    continue
                accepted = prepare_image(image_bytes, class_name, args, hashes_by_class, rejected)
                if not accepted:
                    continue
                image_rgb, image_hash = accepted
                write_image(args.output_dir, class_name, counts[class_name] + 1, image_rgb)
                hashes_by_class[class_name].append(image_hash)
                counts[class_name] += 1
        if all(counts[name] >= args.max_images_per_class for name in requested):
            break

    manifest = {
        "source": "Birds 525 Hugging Face parquet mirror",
        "requested_species": requested,
        "max_images_per_class": args.max_images_per_class,
        "class_counts": dict(sorted(counts.items())),
        "rejected": dict(sorted(rejected.items())),
        "filters": {
            "min_width": args.min_width,
            "min_height": args.min_height,
            "min_blur_score": args.min_blur_score,
            "duplicate_distance": args.duplicate_distance,
        },
    }
    (args.output_dir / "dataset_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


def prepare_image(
    image_bytes: bytes,
    class_name: str,
    args: argparse.Namespace,
    hashes_by_class: dict[str, list[int]],
    rejected: dict[str, int],
) -> tuple[Image.Image, int] | None:
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image = ImageOps.exif_transpose(image).convert("RGB")
    except (UnidentifiedImageError, OSError):
        rejected["invalid_image"] += 1
        return None

    if image.width < args.min_width or image.height < args.min_height:
        rejected["too_small"] += 1
        return None

    if blur_score(image) < args.min_blur_score:
        rejected["blurry"] += 1
        return None

    image_hash = dhash(image)
    if any((image_hash ^ known_hash).bit_count() <= args.duplicate_distance for known_hash in hashes_by_class[class_name]):
        rejected["duplicate"] += 1
        return None

    return image, image_hash


def write_image(output_dir: Path, class_name: str, index: int, image: Image.Image) -> None:
    class_dir = output_dir / class_name
    class_dir.mkdir(parents=True, exist_ok=True)
    image.save(class_dir / f"{index:04d}.jpg", format="JPEG", quality=92, optimize=True)


def blur_score(image: Image.Image) -> float:
    gray = image.convert("L")
    gray.thumbnail((256, 256))
    pixels = np.asarray(gray, dtype=np.float32)
    return float(np.diff(pixels, axis=1).var() + np.diff(pixels, axis=0).var())


def dhash(image: Image.Image, hash_size: int = 8) -> int:
    gray = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = np.asarray(gray)
    difference = pixels[:, 1:] > pixels[:, :-1]
    value = 0
    for bit in difference.flatten():
        value = (value << 1) | int(bit)
    return value


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
