import argparse
from pathlib import Path

import tensorflow as tf

from train_realworld_image_model import (
    build_callbacks,
    build_class_weights,
    load_folder_dataset,
    prepare_dataset,
    save_artifacts,
    unfreeze_backbone,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Expand an existing Keras bird classifier to a new class set.")
    parser.add_argument("--base-model", required=True, type=Path)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output-model", required=True, type=Path)
    parser.add_argument("--image-size", default=224, type=int)
    parser.add_argument("--batch-size", default=8, type=int)
    parser.add_argument("--epochs", default=8, type=int)
    parser.add_argument("--fine-tune-epochs", default=4, type=int)
    parser.add_argument("--learning-rate", default=5e-4, type=float)
    parser.add_argument("--fine-tune-learning-rate", default=5e-6, type=float)
    parser.add_argument("--fine-tune-layers", default=30, type=int)
    parser.add_argument("--validation-split", default=0.15, type=float)
    parser.add_argument("--test-split", default=0.15, type=float)
    parser.add_argument("--seed", default=1337, type=int)
    parser.add_argument("--min-images-per-class", default=100, type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.backbone = "mobilenetv2_expanded_from_existing"
    args.dropout = None
    args.output_model.parent.mkdir(parents=True, exist_ok=True)

    train_ds, val_ds, test_ds, labels, class_counts, source_description = load_folder_dataset(
        args.data_dir,
        args,
        source_description=f"Expanded from {args.base_model} using local folder: {args.data_dir}",
    )
    train_ds = prepare_dataset(train_ds, training=True)
    val_ds = prepare_dataset(val_ds, training=False)
    test_ds = prepare_dataset(test_ds, training=False)

    class_weight = build_class_weights(labels, class_counts)
    model = expand_model(args.base_model, len(labels))
    metrics = [
        "accuracy",
        tf.keras.metrics.SparseTopKCategoricalAccuracy(k=min(3, len(labels)), name="top_3_accuracy"),
    ]

    for layer in model.layers[:-1]:
        layer.trainable = False
    model.layers[-1].trainable = True
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
        callbacks=build_callbacks(args.output_model),
        verbose=2,
    )

    for layer in model.layers:
        layer.trainable = True
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
        callbacks=build_callbacks(args.output_model),
        verbose=2,
    )

    test_metrics = model.evaluate(test_ds, return_dict=True, verbose=2)
    model.save(args.output_model)
    save_artifacts(
        output_model_path=args.output_model,
        args=args,
        labels=labels,
        class_counts=class_counts,
        source_description=source_description,
        head_history=head_history.history,
        fine_history=fine_history.history,
        test_metrics=test_metrics,
    )
    print(f"Saved model: {args.output_model}")
    print(f"Saved labels: {args.output_model.with_suffix('.labels.json')}")
    print(f"Test metrics: {test_metrics}")


def expand_model(base_model_path: Path, class_count: int) -> tf.keras.Model:
    base_model = tf.keras.models.load_model(base_model_path, compile=False)
    features = base_model.layers[-2].output
    outputs = tf.keras.layers.Dense(class_count, activation="softmax", name="species_75")(features)
    return tf.keras.Model(base_model.input, outputs, name="bird_species_expanded")


if __name__ == "__main__":
    main()
