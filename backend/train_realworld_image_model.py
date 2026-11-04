import argparse
import json
import re
from pathlib import Path
import tensorflow as tf


AUTOTUNE = tf.data.AUTOTUNE
DEFAULT_KAGGLE_DATASET = "gpiosenka/100-bird-species"
TFDS_CUB2011 = "caltech_birds2011"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a real-world bird species classifier with transfer learning."
    )
    parser.add_argument(
        "--source",
        choices=["tfds-cub2011", "kaggle-birds525", "folder"],
        default="tfds-cub2011",
        help="Dataset source. tfds-cub2011 downloads CUB-200-2011 automatically.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        help=(
            "Local dataset folder for --source folder. For tfds-cub2011, this is the TFDS cache root. "
            "For Kaggle, this is the download output folder."
        ),
    )
    parser.add_argument(
        "--kaggle-dataset",
        default=DEFAULT_KAGGLE_DATASET,
        help="Kaggle dataset slug for --source kaggle-birds525.",
    )
    parser.add_argument(
        "--output-model",
        default=Path("models/BirdsModel_realworld.keras"),
        type=Path,
    )
    parser.add_argument(
        "--backbone",
        choices=["efficientnetb0", "mobilenetv2", "resnet50"],
        default="efficientnetb0",
    )
    parser.add_argument("--image-size", default=224, type=int)
    parser.add_argument("--batch-size", default=16, type=int)
    parser.add_argument("--epochs", default=15, type=int)
    parser.add_argument("--fine-tune-epochs", default=10, type=int)
    parser.add_argument("--learning-rate", default=1e-3, type=float)
    parser.add_argument("--fine-tune-learning-rate", default=1e-5, type=float)
    parser.add_argument("--fine-tune-layers", default=40, type=int)
    parser.add_argument("--dropout", default=0.35, type=float)
    parser.add_argument("--validation-split", default=0.15, type=float)
    parser.add_argument("--test-split", default=0.15, type=float)
    parser.add_argument("--seed", default=1337, type=int)
    parser.add_argument("--min-images-per-class", default=20, type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_model_path = args.output_model.resolve()
    output_model_path.parent.mkdir(parents=True, exist_ok=True)

    train_ds, val_ds, test_ds, labels, class_counts, source_description = load_source(args)
    train_ds = prepare_dataset(train_ds, training=True)
    val_ds = prepare_dataset(val_ds, training=False)
    test_ds = prepare_dataset(test_ds, training=False)

    class_weight = build_class_weights(labels, class_counts)
    model = build_model(args.backbone, len(labels), args.image_size, args.dropout)

    metrics = [
        "accuracy",
        tf.keras.metrics.SparseTopKCategoricalAccuracy(k=min(3, len(labels)), name="top_3_accuracy"),
    ]
    model.compile(
        optimizer=tf.keras.optimizers.Adam(args.learning_rate),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(),
        metrics=metrics,
    )

    head_history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=args.epochs,
        class_weight=class_weight,
        callbacks=build_callbacks(output_model_path),
    )

    unfreeze_backbone(model, args.fine_tune_layers)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(args.fine_tune_learning_rate),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(),
        metrics=metrics,
    )

    fine_history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=args.fine_tune_epochs,
        class_weight=class_weight,
        callbacks=build_callbacks(output_model_path),
    )

    test_metrics = model.evaluate(test_ds, return_dict=True)
    model.save(output_model_path)
    save_artifacts(
        output_model_path=output_model_path,
        args=args,
        labels=labels,
        class_counts=class_counts,
        source_description=source_description,
        head_history=head_history.history,
        fine_history=fine_history.history,
        test_metrics=test_metrics,
    )

    print(f"Saved model: {output_model_path}")
    print(f"Saved labels: {output_model_path.with_suffix('.labels.json')}")
    print(f"Test metrics: {test_metrics}")


def load_source(args: argparse.Namespace):
    if args.source == "tfds-cub2011":
        return load_tfds_cub2011(args)
    if args.source == "kaggle-birds525":
        dataset_dir = download_kaggle_dataset(args.kaggle_dataset, args.data_dir)
        return load_folder_dataset(dataset_dir, args, source_description=f"Kaggle dataset: {args.kaggle_dataset}")
    if not args.data_dir:
        raise ValueError("--data-dir is required when --source folder is used.")
    return load_folder_dataset(args.data_dir, args, source_description=f"Local folder: {args.data_dir}")


def load_tfds_cub2011(args: argparse.Namespace):
    try:
        import tensorflow_datasets as tfds
    except ImportError as exc:
        raise ImportError("Install tensorflow-datasets: pip install tensorflow-datasets") from exc

    train_split = f"train[:{int((1 - args.validation_split) * 100)}%]"
    val_split = f"train[{int((1 - args.validation_split) * 100)}%:]"
    tfds_data_dir = str(args.data_dir.resolve()) if args.data_dir else None
    train_ds, val_ds, test_ds = tfds.load(
        TFDS_CUB2011,
        split=[train_split, val_split, "test"],
        as_supervised=True,
        data_dir=tfds_data_dir,
    )
    info = tfds.builder(TFDS_CUB2011, data_dir=tfds_data_dir).info
    labels = [clean_label(name) for name in info.features["label"].names]
    class_counts = {label: 1 for label in labels}
    return (
        batch_tfds(train_ds, args),
        batch_tfds(val_ds, args),
        batch_tfds(test_ds, args),
        labels,
        class_counts,
        "TensorFlow Datasets: Caltech-UCSD Birds 200-2011",
    )


def batch_tfds(dataset: tf.data.Dataset, args: argparse.Namespace) -> tf.data.Dataset:
    return dataset.shuffle(4096, seed=args.seed).batch(args.batch_size)


def download_kaggle_dataset(kaggle_dataset: str, data_dir: Path | None) -> Path:
    try:
        import kagglehub
    except ImportError as exc:
        raise ImportError("Install kagglehub: pip install kagglehub") from exc

    kwargs = {"output_dir": str(data_dir.resolve())} if data_dir else {}
    downloaded_path = kagglehub.dataset_download(kaggle_dataset, **kwargs)
    return Path(downloaded_path)


def load_folder_dataset(data_dir: Path, args: argparse.Namespace, source_description: str):
    data_dir = data_dir.resolve()
    if not data_dir.exists():
        raise FileNotFoundError(f"Dataset folder not found: {data_dir}")

    split_dirs = find_split_dirs(data_dir)
    if split_dirs:
        train_ds = image_dataset(split_dirs["train"], args, shuffle=True)
        val_ds = image_dataset(split_dirs["validation"], args, shuffle=False)
        test_ds = image_dataset(split_dirs["test"], args, shuffle=False)
        labels = [name.upper() for name in train_ds.class_names]
        class_counts = count_images_by_class(split_dirs["train"])
    else:
        train_ds, val_ds, test_ds = load_unsplit_folder(data_dir, args)
        labels = [name.upper() for name in train_ds.class_names]
        class_counts = count_images_by_class(data_dir)

    validate_dataset(class_counts, args.min_images_per_class)
    return train_ds, val_ds, test_ds, labels, normalize_count_keys(class_counts), source_description


def find_split_dirs(data_dir: Path) -> dict[str, Path] | None:
    candidates = {
        "train": ["train", "training"],
        "validation": ["valid", "val", "validation"],
        "test": ["test", "testing"],
    }
    resolved: dict[str, Path] = {}
    for split, names in candidates.items():
        for name in names:
            path = data_dir / name
            if path.exists() and path.is_dir():
                resolved[split] = path
                break
    return resolved if {"train", "validation", "test"}.issubset(resolved) else None


def load_unsplit_folder(data_dir: Path, args: argparse.Namespace):
    holdout_split = args.validation_split + args.test_split
    if holdout_split <= 0 or holdout_split >= 0.8:
        raise ValueError("validation-split + test-split must be greater than 0 and less than 0.8.")

    common_kwargs = {
        "directory": data_dir,
        "labels": "inferred",
        "label_mode": "int",
        "image_size": (args.image_size, args.image_size),
        "batch_size": None,
        "seed": args.seed,
        "validation_split": holdout_split,
    }
    train_ds = tf.keras.utils.image_dataset_from_directory(
        subset="training",
        shuffle=True,
        **common_kwargs,
    )
    holdout_ds = tf.keras.utils.image_dataset_from_directory(
        subset="validation",
        shuffle=False,
        **common_kwargs,
    )
    class_names = train_ds.class_names
    val_ratio = args.validation_split / holdout_split
    val_ds, test_ds = tf.keras.utils.split_dataset(holdout_ds, left_size=val_ratio, shuffle=False)
    train_ds = train_ds.batch(args.batch_size)
    val_ds = val_ds.batch(args.batch_size)
    test_ds = test_ds.batch(args.batch_size)
    val_ds.class_names = class_names
    test_ds.class_names = class_names
    train_ds.class_names = class_names
    return train_ds, val_ds, test_ds


def image_dataset(path: Path, args: argparse.Namespace, shuffle: bool):
    return tf.keras.utils.image_dataset_from_directory(
        path,
        labels="inferred",
        label_mode="int",
        image_size=(args.image_size, args.image_size),
        batch_size=args.batch_size,
        shuffle=shuffle,
        seed=args.seed,
    )


def prepare_dataset(dataset: tf.data.Dataset, training: bool) -> tf.data.Dataset:
    def normalize(images, labels):
        images = tf.cast(images, tf.float32)
        return images, labels

    dataset = dataset.map(normalize, num_parallel_calls=AUTOTUNE)
    if training:
        dataset = dataset.shuffle(2048)
    return dataset.prefetch(AUTOTUNE)


def build_model(backbone_name: str, class_count: int, image_size: int, dropout: float) -> tf.keras.Model:
    preprocessing_layer, backbone_factory = backbone_config(backbone_name)
    inputs = tf.keras.Input(shape=(image_size, image_size, 3), name="image")
    x = tf.keras.layers.RandomFlip("horizontal", name="augment_flip")(inputs)
    x = tf.keras.layers.RandomRotation(0.08, name="augment_rotation")(x)
    x = tf.keras.layers.RandomZoom(0.12, name="augment_zoom")(x)
    x = tf.keras.layers.RandomBrightness(0.15, name="augment_brightness")(x)
    x = tf.keras.layers.RandomContrast(0.12, name="augment_contrast")(x)
    x = preprocessing_layer(x)

    backbone = backbone_factory(
        include_top=False,
        weights="imagenet",
        input_shape=(image_size, image_size, 3),
        pooling="avg",
    )
    backbone.trainable = False

    x = backbone(x, training=False)
    x = tf.keras.layers.BatchNormalization(name="head_batch_norm")(x)
    x = tf.keras.layers.Dropout(dropout, name="head_dropout")(x)
    outputs = tf.keras.layers.Dense(class_count, activation="softmax", name="species")(x)
    return tf.keras.Model(inputs, outputs, name=f"bird_species_{backbone_name}")


def backbone_config(backbone_name: str):
    if backbone_name == "efficientnetb0":
        return (
            tf.keras.layers.Rescaling(1.0, name="efficientnet_raw_pixels"),
            tf.keras.applications.EfficientNetB0,
        )
    if backbone_name == "mobilenetv2":
        return (
            tf.keras.layers.Rescaling(1.0 / 127.5, offset=-1.0, name="mobilenetv2_rescale"),
            tf.keras.applications.MobileNetV2,
        )
    if backbone_name == "resnet50":
        normalization = tf.keras.layers.Normalization(
            mean=[123.68, 116.779, 103.939],
            variance=[1.0, 1.0, 1.0],
            name="resnet50_imagenet_normalization",
        )
        return (
            normalization,
            tf.keras.applications.ResNet50,
        )
    raise ValueError(f"Unsupported backbone: {backbone_name}")


def build_callbacks(output_model_path: Path) -> list[tf.keras.callbacks.Callback]:
    return [
        tf.keras.callbacks.ModelCheckpoint(
            filepath=str(output_model_path),
            monitor="val_accuracy",
            mode="max",
            save_best_only=True,
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_accuracy",
            mode="max",
            patience=5,
            restore_best_weights=True,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.3,
            patience=2,
            min_lr=1e-7,
        ),
    ]


def unfreeze_backbone(model: tf.keras.Model, fine_tune_layers: int) -> None:
    backbone = next(layer for layer in model.layers if isinstance(layer, tf.keras.Model))
    backbone.trainable = True
    for layer in backbone.layers[:-fine_tune_layers]:
        layer.trainable = False
    for layer in backbone.layers[-fine_tune_layers:]:
        layer.trainable = not isinstance(layer, tf.keras.layers.BatchNormalization)


def count_images_by_class(data_dir: Path) -> dict[str, int]:
    extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    return {
        class_dir.name: sum(1 for path in class_dir.rglob("*") if path.suffix.lower() in extensions)
        for class_dir in sorted(path for path in data_dir.iterdir() if path.is_dir())
    }


def validate_dataset(class_counts: dict[str, int], min_images_per_class: int) -> None:
    if len(class_counts) < 2:
        raise ValueError("Training needs at least two bird species folders.")
    weak_classes = {
        class_name: count for class_name, count in class_counts.items() if count < min_images_per_class
    }
    if weak_classes:
        raise ValueError(
            f"Some species have fewer than {min_images_per_class} images: {weak_classes}"
        )


def build_class_weights(labels: list[str], class_counts: dict[str, int]) -> dict[int, float]:
    normalized_counts = normalize_count_keys(class_counts)
    total = sum(normalized_counts.values())
    return {
        index: total / (len(labels) * max(normalized_counts.get(label, 1), 1))
        for index, label in enumerate(labels)
    }


def normalize_count_keys(class_counts: dict[str, int]) -> dict[str, int]:
    return {class_name.upper(): count for class_name, count in class_counts.items()}


def clean_label(label: str) -> str:
    label = re.sub(r"^\d+\.", "", label)
    return label.replace("_", " ").replace("-", " ").strip().upper()


def save_artifacts(
    output_model_path: Path,
    args: argparse.Namespace,
    labels: list[str],
    class_counts: dict[str, int],
    source_description: str,
    head_history: dict[str, list[float]],
    fine_history: dict[str, list[float]],
    test_metrics: dict[str, float],
) -> None:
    output_model_path.with_suffix(".labels.json").write_text(
        json.dumps(labels, indent=2),
        encoding="utf-8",
    )
    metadata = {
        "architecture": f"{args.backbone} transfer learning",
        "source": source_description,
        "preprocessing": "raw",
        "image_size": [args.image_size, args.image_size],
        "labels": labels,
        "class_counts": class_counts,
        "augmentation": [
            "rotation",
            "zoom",
            "horizontal_flip",
            "brightness",
            "contrast",
        ],
        "regularization": [
            "dropout",
            "batch_normalization",
            "early_stopping",
            "reduce_lr_on_plateau",
            "class_weights",
        ],
        "splits": {
            "train": "training",
            "validation": "validation",
            "test": "held-out test",
        },
        "training_args": vars(args),
        "history": {
            "frozen_backbone": head_history,
            "fine_tuning": fine_history,
        },
        "test_metrics": test_metrics,
    }
    output_model_path.with_suffix(".metadata.json").write_text(
        json.dumps(metadata, indent=2, default=str),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
