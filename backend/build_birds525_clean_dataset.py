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

SOURCE_TO_TARGET_LABELS = {
    "BLUE HERON": "GREAT BLUE HERON",
    "COMMON STARLING": "EUROPEAN STARLING",
    "MALLARD DUCK": "MALLARD",
    "RED TAILED HAWK": "RED-TAILED HAWK",
    "RED SHOULDERED HAWK": "RED-SHOULDERED HAWK",
    "ROCK DOVE": "ROCK PIGEON",
}

PRIORITY_LABELS = [
    "BALD EAGLE",
    "RED TAILED HAWK",
    "RED SHOULDERED HAWK",
    "GOLDEN EAGLE",
    "OSPREY",
    "AMERICAN KESTREL",
    "BLACK VULTURE",
    "CALIFORNIA CONDOR",
    "BARN OWL",
    "SNOWY OWL",
    "GREAT GRAY OWL",
    "AMERICAN ROBIN",
    "NORTHERN CARDINAL",
    "HOUSE SPARROW",
    "BARN SWALLOW",
    "MOURNING DOVE",
    "ROCK DOVE",
    "MALLARD DUCK",
    "BLUE HERON",
    "SNOWY EGRET",
    "COMMON STARLING",
    "BLUE JAY",
    "CROW",
    "COMMON RAVEN",
    "BLACK-CAPPED CHICKADEE",
    "CEDAR WAXWING",
    "BALTIMORE ORIOLE",
    "AMERICAN GOLDFINCH",
    "CHIPPING SPARROW",
    "DOWNY WOODPECKER",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a larger, balanced, quality-filtered dataset from the Birds 525 parquet mirror."
    )
    parser.add_argument("--parquet-dir", default=Path(r"D:\AFYP\datasets\birds525_hf_parquet\data"), type=Path)
    parser.add_argument("--output-dir", default=Path(r"D:\AFYP\datasets\birds525_clean_100"), type=Path)
    parser.add_argument("--species-count", default=100, type=int, help="Target number of species folders.")
    parser.add_argument("--images-per-class", default=250, type=int, help="Balanced accepted images per species.")
    parser.add_argument(
        "--select-by-count",
        action="store_true",
        help="Pick labels with the most raw images first. Best for strict balanced datasets.",
    )
    parser.add_argument(
        "--min-raw-images",
        default=0,
        type=int,
        help="When --select-by-count is used, skip classes with fewer raw images than this.",
    )
    parser.add_argument("--extra-dir", type=Path, help="Optional folder of mobile/Google images, one species per folder.")
    parser.add_argument("--min-width", default=160, type=int)
    parser.add_argument("--min-height", default=160, type=int)
    parser.add_argument(
        "--min-blur-score",
        default=40.0,
        type=float,
        help="Reject very blurry images. Higher is stricter.",
    )
    parser.add_argument(
        "--duplicate-distance",
        default=4,
        type=int,
        help="Reject near duplicates with dHash Hamming distance at or below this value.",
    )
    parser.add_argument("--clear-output", action="store_true", help="Delete the output directory before export.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.clear_output and args.output_dir.exists():
        shutil.rmtree(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    label_names = read_label_names(args.parquet_dir / first_existing_parquet(args.parquet_dir))
    raw_counts = count_source_labels(args.parquet_dir)
    selected_sources = select_source_labels(label_names, args.species_count, raw_counts, args)
    source_index_to_target = {
        index: target_label(label)
        for index, label in enumerate(label_names)
        if label in selected_sources
    }

    counts: dict[str, int] = defaultdict(int)
    hashes_by_class: dict[str, list[int]] = defaultdict(list)
    rejected: dict[str, int] = defaultdict(int)
    selected_targets = [target_label(label) for label in selected_sources]

    if args.extra_dir:
        import_extra_images(args, selected_targets, counts, hashes_by_class, rejected)

    for parquet_name in PARQUET_FILES:
        parquet_path = args.parquet_dir / parquet_name
        if not parquet_path.exists():
            continue

        table = pq.read_table(parquet_path, columns=["image", "label"])
        for image, label in zip(table["image"].to_pylist(), table["label"].to_pylist()):
            source_label_index = int(label)
            class_name = source_index_to_target.get(source_label_index)
            if not class_name:
                continue
            if counts[class_name] >= args.images_per_class:
                continue

            image_bytes = image.get("bytes") if isinstance(image, dict) else None
            if not image_bytes:
                rejected["missing_bytes"] += 1
                continue

            accepted = prepare_image(
                image_bytes=image_bytes,
                class_name=class_name,
                args=args,
                hashes_by_class=hashes_by_class,
                rejected=rejected,
            )
            if not accepted:
                continue

            image_rgb, image_hash = accepted
            write_image(args.output_dir, class_name, counts[class_name] + 1, image_rgb)
            hashes_by_class[class_name].append(image_hash)
            counts[class_name] += 1

        if all(counts[target] >= args.images_per_class for target in selected_targets):
            break

    manifest = {
        "source": "Hugging Face mirror of Birds 525",
        "output_dir": str(args.output_dir),
        "species_count_requested": args.species_count,
        "images_per_class_requested": args.images_per_class,
        "selected_source_labels": selected_sources,
        "selected_target_labels": selected_targets,
        "raw_class_counts": {target_label(label): raw_counts.get(label_names.index(label), 0) for label in selected_sources},
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

    for class_name in selected_targets:
        print(f"{class_name}: {counts[class_name]}")
    print(f"Accepted {sum(counts.values())} images across {len([c for c in counts.values() if c])} classes")
    print(f"Rejected: {dict(sorted(rejected.items()))}")
    print(f"Manifest: {args.output_dir / 'dataset_manifest.json'}")


def import_extra_images(
    args: argparse.Namespace,
    selected_targets: list[str],
    counts: dict[str, int],
    hashes_by_class: dict[str, list[int]],
    rejected: dict[str, int],
) -> None:
    if not args.extra_dir or not args.extra_dir.exists():
        return

    selected_set = set(selected_targets)
    for class_dir in sorted(path for path in args.extra_dir.iterdir() if path.is_dir()):
        class_name = class_dir.name.upper()
        if class_name not in selected_set:
            rejected["extra_unselected_class"] += 1
            continue
        for path in sorted(class_dir.iterdir()):
            if counts[class_name] >= args.images_per_class:
                break
            if not path.is_file():
                continue
            accepted = prepare_image(
                image_bytes=path.read_bytes(),
                class_name=class_name,
                args=args,
                hashes_by_class=hashes_by_class,
                rejected=rejected,
            )
            if not accepted:
                continue
            image_rgb, image_hash = accepted
            write_image(args.output_dir, class_name, counts[class_name] + 1, image_rgb)
            hashes_by_class[class_name].append(image_hash)
            counts[class_name] += 1


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

    blur = blur_score(image)
    if blur < args.min_blur_score:
        rejected["blurry"] += 1
        return None

    image_hash = dhash(image)
    if is_duplicate(image_hash, hashes_by_class[class_name], args.duplicate_distance):
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
    horizontal = np.diff(pixels, axis=1)
    vertical = np.diff(pixels, axis=0)
    return float(horizontal.var() + vertical.var())


def dhash(image: Image.Image, hash_size: int = 8) -> int:
    gray = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = np.asarray(gray)
    difference = pixels[:, 1:] > pixels[:, :-1]
    value = 0
    for bit in difference.flatten():
        value = (value << 1) | int(bit)
    return value


def is_duplicate(image_hash: int, known_hashes: list[int], max_distance: int) -> bool:
    return any((image_hash ^ known).bit_count() <= max_distance for known in known_hashes)


def count_source_labels(parquet_dir: Path) -> dict[int, int]:
    counts: dict[int, int] = defaultdict(int)
    for parquet_name in PARQUET_FILES:
        parquet_path = parquet_dir / parquet_name
        if not parquet_path.exists():
            continue
        table = pq.read_table(parquet_path, columns=["label"])
        for label in table["label"].to_pylist():
            counts[int(label)] += 1
    return counts


def select_source_labels(
    label_names: list[str],
    species_count: int,
    raw_counts: dict[int, int],
    args: argparse.Namespace,
) -> list[str]:
    if args.select_by_count:
        ranked = sorted(
            enumerate(label_names),
            key=lambda item: raw_counts.get(item[0], 0),
            reverse=True,
        )
        return [
            label
            for index, label in ranked
            if raw_counts.get(index, 0) >= args.min_raw_images
        ][:species_count]

    selected: list[str] = []
    available = set(label_names)
    for label in PRIORITY_LABELS:
        if label in available and label not in selected:
            selected.append(label)
    for label in label_names:
        if len(selected) >= species_count:
            break
        if label not in selected:
            selected.append(label)
    return selected[:species_count]


def target_label(source_label: str) -> str:
    return SOURCE_TO_TARGET_LABELS.get(source_label, source_label).upper()


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
