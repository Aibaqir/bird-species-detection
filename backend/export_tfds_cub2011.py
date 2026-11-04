import argparse
import re
from pathlib import Path

import tensorflow as tf
import tensorflow_datasets as tfds


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export CUB-200-2011 TFDS images to class folders.")
    parser.add_argument("--data-dir", default=Path(r"D:\AFYP\datasets\tfds"), type=Path)
    parser.add_argument("--output-dir", default=Path(r"D:\AFYP\datasets\cub2011_folders"), type=Path)
    parser.add_argument("--max-images-per-class", default=80, type=int)
    parser.add_argument("--split", default="train+test")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    dataset = tfds.load(
        "caltech_birds2011",
        split=args.split,
        data_dir=str(args.data_dir),
        shuffle_files=False,
    )

    counts: dict[str, int] = {}
    for example in tfds.as_numpy(dataset):
        label_name = example["label_name"].decode("utf-8")
        class_name = clean_label(label_name)
        current = counts.get(class_name, 0)
        if current >= args.max_images_per_class:
            continue

        target_dir = args.output_dir / class_name
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{current + 1:04d}.jpg"
        image = tf.io.encode_jpeg(example["image"], quality=95).numpy()
        target_path.write_bytes(image)
        counts[class_name] = current + 1

    for class_name, count in sorted(counts.items()):
        print(f"{class_name}: {count}")
    print(f"Exported {sum(counts.values())} images across {len(counts)} classes to {args.output_dir}")


def clean_label(label: str) -> str:
    label = re.sub(r"^\d+\.", "", label)
    return label.replace("_", " ").replace("-", " ").strip().upper()


if __name__ == "__main__":
    main()
