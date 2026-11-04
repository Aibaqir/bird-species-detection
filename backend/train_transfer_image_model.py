import argparse
import json
from pathlib import Path

import tensorflow as tf


AUTOTUNE = tf.data.AUTOTUNE


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a stronger bird image classifier using EfficientNet transfer learning."
    )
    parser.add_argument(
        "--data-dir",
        required=True,
        type=Path,
        help="Dataset folder with one subfolder per bird species.",
    )
    parser.add_argument(
        "--output-model",
        default=Path("models/BirdsModel_transfer.keras"),
        type=Path,
        help="Where to save the trained model. .keras is recommended.",
    )
    parser.add_argument("--image-size", default=224, type=int)
    parser.add_argument("--batch-size", default=16, type=int)
    parser.add_argument("--epochs", default=12, type=int, help="Frozen-base training epochs.")
    parser.add_argument("--fine-tune-epochs", default=8, type=int, help="Fine-tuning epochs.")
    parser.add_argument("--validation-split", default=0.2, type=float)
    parser.add_argument("--seed", default=1337, type=int)
    parser.add_argument("--learning-rate", default=1e-3, type=float)
    parser.add_argument("--fine-tune-learning-rate", default=1e-5, type=float)
    parser.add_argument("--fine-tune-layers", default=40, type=int)
    parser.add_argument("--min-images-per-class", default=20, type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_dir = args.data_dir.resolve()
    output_model_path = args.output_model.resolve()

    if not data_dir.exists():
        raise FileNotFoundError(f"Dataset folder not found: {data_dir}")

    class_counts = count_images_by_class(data_dir)
    validate_dataset(class_counts, args.min_images_per_class)

    train_ds, val_ds, labels = load_datasets(args)
    train_ds = train_ds.prefetch(AUTOTUNE)
    val_ds = val_ds.prefetch(AUTOTUNE)

    class_weight = build_class_weights(labels, class_counts)
    model = build_model(len(labels), args.image_size)

    output_model_path.parent.mkdir(parents=True, exist_ok=True)

    model.compile(
        optimizer=tf.keras.optimizers.Adam(args.learning_rate),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(),
        metrics=[
            "accuracy",
            tf.keras.metrics.SparseTopKCategoricalAccuracy(k=min(3, len(labels)), name="top_3_accuracy"),
        ],
    )

    head_history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=args.epochs,
        class_weight=class_weight,
        callbacks=build_callbacks(output_model_path),
    )

    unfreeze_for_fine_tuning(model, args.fine_tune_layers)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(args.fine_tune_learning_rate),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(),
        metrics=[
            "accuracy",
            tf.keras.metrics.SparseTopKCategoricalAccuracy(k=min(3, len(labels)), name="top_3_accuracy"),
        ],
    )

    fine_history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=args.fine_tune_epochs,
        class_weight=class_weight,
        callbacks=build_callbacks(output_model_path),
    )

    model.save(output_model_path)
    save_labels_and_metadata(output_model_path, labels, class_counts, args, head_history.history, fine_history.history)
    print(f"Saved trained image model to: {output_model_path}")
    print(f"Saved labels to: {output_model_path.with_suffix('.labels.json')}")
    print(f"Saved metadata to: {output_model_path.with_suffix('.metadata.json')}")


def count_images_by_class(data_dir: Path) -> dict[str, int]:
    extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    counts: dict[str, int] = {}
    for class_dir in sorted(path for path in data_dir.iterdir() if path.is_dir()):
        counts[class_dir.name] = sum(
            1 for image_path in class_dir.rglob("*") if image_path.suffix.lower() in extensions
        )
    return counts


def validate_dataset(class_counts: dict[str, int], min_images_per_class: int) -> None:
    if len(class_counts) < 2:
        raise ValueError("Training needs at least two class folders.")

    weak_classes = {
        class_name: count for class_name, count in class_counts.items() if count < min_images_per_class
    }
    if weak_classes:
        raise ValueError(
            "Some classes do not have enough images. Add more images or lower --min-images-per-class.\n"
            f"Minimum required: {min_images_per_class}\n"
            f"Found: {weak_classes}"
        )


def load_datasets(args: argparse.Namespace):
    dataset_kwargs = {
        "directory": args.data_dir,
        "labels": "inferred",
        "label_mode": "int",
        "validation_split": args.validation_split,
        "seed": args.seed,
        "image_size": (args.image_size, args.image_size),
        "batch_size": args.batch_size,
    }
    train_ds = tf.keras.utils.image_dataset_from_directory(
        subset="training",
        shuffle=True,
        **dataset_kwargs,
    )
    val_ds = tf.keras.utils.image_dataset_from_directory(
        subset="validation",
        shuffle=False,
        **dataset_kwargs,
    )
    labels = [class_name.upper() for class_name in train_ds.class_names]
    return train_ds, val_ds, labels


def build_class_weights(labels: list[str], class_counts: dict[str, int]) -> dict[int, float]:
    normalized_counts = {class_name.upper(): count for class_name, count in class_counts.items()}
    total = sum(normalized_counts.values())
    return {
        index: total / (len(labels) * normalized_counts[label])
        for index, label in enumerate(labels)
    }


def build_model(class_count: int, image_size: int) -> tf.keras.Model:
    inputs = tf.keras.Input(shape=(image_size, image_size, 3), name="image")
    x = tf.keras.layers.RandomFlip("horizontal")(inputs)
    x = tf.keras.layers.RandomRotation(0.08)(x)
    x = tf.keras.layers.RandomZoom(0.12)(x)
    x = tf.keras.layers.RandomContrast(0.12)(x)

    base_model = tf.keras.applications.EfficientNetB0(
        include_top=False,
        weights="imagenet",
        input_shape=(image_size, image_size, 3),
        pooling="avg",
    )
    base_model.trainable = False

    x = base_model(x, training=False)
    x = tf.keras.layers.Dropout(0.35)(x)
    outputs = tf.keras.layers.Dense(class_count, activation="softmax", name="species")(x)
    return tf.keras.Model(inputs, outputs, name="bird_species_efficientnet")


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


def unfreeze_for_fine_tuning(model: tf.keras.Model, fine_tune_layers: int) -> None:
    base_model = next(
        layer for layer in model.layers if isinstance(layer, tf.keras.Model) and layer.name.startswith("efficientnet")
    )
    base_model.trainable = True

    for layer in base_model.layers[:-fine_tune_layers]:
        layer.trainable = False
    for layer in base_model.layers[-fine_tune_layers:]:
        if isinstance(layer, tf.keras.layers.BatchNormalization):
            layer.trainable = False
        else:
            layer.trainable = True


def save_labels_and_metadata(
    output_model_path: Path,
    labels: list[str],
    class_counts: dict[str, int],
    args: argparse.Namespace,
    head_history: dict[str, list[float]],
    fine_history: dict[str, list[float]],
) -> None:
    labels_path = output_model_path.with_suffix(".labels.json")
    metadata_path = output_model_path.with_suffix(".metadata.json")
    labels_path.write_text(json.dumps(labels, indent=2), encoding="utf-8")
    metadata = {
        "architecture": "EfficientNetB0 transfer learning",
        "preprocessing": "raw",
        "image_size": [args.image_size, args.image_size],
        "labels": labels,
        "class_counts": class_counts,
        "data_dir": str(args.data_dir),
        "output_model": str(args.output_model),
        "epochs": args.epochs,
        "fine_tune_epochs": args.fine_tune_epochs,
        "batch_size": args.batch_size,
        "validation_split": args.validation_split,
        "learning_rate": args.learning_rate,
        "fine_tune_learning_rate": args.fine_tune_learning_rate,
        "fine_tune_layers": args.fine_tune_layers,
        "history": {
            "head_training": head_history,
            "fine_tuning": fine_history,
        },
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
