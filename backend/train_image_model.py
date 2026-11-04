import argparse
import json
from pathlib import Path

import tensorflow as tf

from app.recommendations import CLASS_LABELS


IMAGE_SIZE = (224, 224)
AUTOTUNE = tf.data.AUTOTUNE


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fine-tune the existing bird image classifier on more images."
    )
    parser.add_argument(
        "--data-dir",
        required=True,
        type=Path,
        help="Dataset folder. It must contain one subfolder per class label.",
    )
    parser.add_argument(
        "--base-model",
        default=Path("models/BirdsModel.h5"),
        type=Path,
        help="Existing .h5 model to continue training.",
    )
    parser.add_argument(
        "--output-model",
        default=Path("models/BirdsModel_finetuned.h5"),
        type=Path,
        help="Where to save the fine-tuned model.",
    )
    parser.add_argument("--epochs", default=10, type=int)
    parser.add_argument("--batch-size", default=16, type=int)
    parser.add_argument("--validation-split", default=0.2, type=float)
    parser.add_argument("--seed", default=1337, type=int)
    parser.add_argument("--learning-rate", default=1e-5, type=float)
    parser.add_argument(
        "--fine-tune-layers",
        default=20,
        type=int,
        help="Number of layers from the end to keep trainable. Use 0 to train every layer.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_dir = args.data_dir.resolve()
    base_model_path = args.base_model.resolve()
    output_model_path = args.output_model.resolve()

    validate_paths(data_dir, base_model_path)

    train_ds, val_ds = load_datasets(args)
    class_names = train_ds.class_names
    validate_class_names(class_names)

    train_ds = prepare_dataset(train_ds, training=True)
    val_ds = prepare_dataset(val_ds, training=False)

    model = tf.keras.models.load_model(base_model_path, compile=False)
    validate_model_output(model)
    set_trainable_layers(model, args.fine_tune_layers)

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=args.learning_rate),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(),
        metrics=["accuracy"],
    )

    output_model_path.parent.mkdir(parents=True, exist_ok=True)
    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(
            filepath=str(output_model_path),
            monitor="val_accuracy",
            mode="max",
            save_best_only=True,
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_accuracy",
            mode="max",
            patience=4,
            restore_best_weights=True,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.3,
            patience=2,
            min_lr=1e-7,
        ),
    ]

    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=args.epochs,
        callbacks=callbacks,
    )

    model.save(output_model_path)
    save_training_metadata(output_model_path, history.history, args, class_names)
    print(f"Saved fine-tuned model to: {output_model_path}")


def validate_paths(data_dir: Path, base_model_path: Path) -> None:
    if not data_dir.exists():
        raise FileNotFoundError(f"Dataset folder not found: {data_dir}")
    if not base_model_path.exists():
        raise FileNotFoundError(f"Base model not found: {base_model_path}")


def load_datasets(args: argparse.Namespace):
    dataset_kwargs = {
        "directory": args.data_dir,
        "labels": "inferred",
        "label_mode": "int",
        "validation_split": args.validation_split,
        "seed": args.seed,
        "image_size": IMAGE_SIZE,
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
    return train_ds, val_ds


def validate_class_names(dataset_class_names: list[str]) -> None:
    expected = [label.upper() for label in CLASS_LABELS]
    actual = [label.upper() for label in dataset_class_names]
    if actual != expected:
        message = [
            "Dataset class folders must match the current model labels exactly.",
            f"Expected: {expected}",
            f"Found:    {actual}",
            "Rename your dataset folders or update app/recommendations.py and retrain a compatible model.",
        ]
        raise ValueError("\n".join(message))


def prepare_dataset(dataset: tf.data.Dataset, training: bool) -> tf.data.Dataset:
    augmentation = tf.keras.Sequential(
        [
            tf.keras.layers.RandomFlip("horizontal"),
            tf.keras.layers.RandomRotation(0.05),
            tf.keras.layers.RandomZoom(0.1),
            tf.keras.layers.RandomContrast(0.1),
        ],
        name="training_augmentation",
    )

    def normalize(images, labels):
        return tf.cast(images, tf.float32) / 255.0, labels

    def augment(images, labels):
        return augmentation(images, training=True), labels

    dataset = dataset.map(normalize, num_parallel_calls=AUTOTUNE)
    if training:
        dataset = dataset.map(augment, num_parallel_calls=AUTOTUNE)
    return dataset.prefetch(AUTOTUNE)


def validate_model_output(model: tf.keras.Model) -> None:
    output_shape = model.output_shape
    output_classes = output_shape[-1] if isinstance(output_shape, tuple) else None
    if output_classes != len(CLASS_LABELS):
        raise ValueError(
            f"Model output has {output_classes} classes, but app labels contain {len(CLASS_LABELS)} classes."
        )


def set_trainable_layers(model: tf.keras.Model, fine_tune_layers: int) -> None:
    if fine_tune_layers <= 0:
        model.trainable = True
        return

    for layer in model.layers[:-fine_tune_layers]:
        layer.trainable = False
    for layer in model.layers[-fine_tune_layers:]:
        layer.trainable = True


def save_training_metadata(
    output_model_path: Path,
    history: dict[str, list[float]],
    args: argparse.Namespace,
    dataset_class_names: list[str],
) -> None:
    labels = [label.upper() for label in dataset_class_names]
    labels_path = output_model_path.with_suffix(".labels.json")
    metadata_path = output_model_path.with_suffix(".training.json")
    labels_path.write_text(json.dumps(labels, indent=2), encoding="utf-8")
    metadata = {
        "base_model": str(args.base_model),
        "output_model": str(args.output_model),
        "data_dir": str(args.data_dir),
        "preprocessing": "zero_to_one",
        "image_size": [IMAGE_SIZE[0], IMAGE_SIZE[1]],
        "labels": labels,
        "classes": CLASS_LABELS,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "validation_split": args.validation_split,
        "learning_rate": args.learning_rate,
        "fine_tune_layers": args.fine_tune_layers,
        "history": history,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
