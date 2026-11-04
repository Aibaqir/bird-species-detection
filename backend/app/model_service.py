import json
import os
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from .recommendations import CLASS_LABELS, RECOMMENDATIONS


class ModelNotReadyError(RuntimeError):
    pass


class InvalidImageError(ValueError):
    pass


class BirdClassifier:
    def __init__(
        self,
        model_path: Path,
        labels_path: Path | None = None,
        confidence_threshold: float | None = None,
    ):
        self.model_path = model_path
        self.labels_path = labels_path
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else float(os.getenv("IMAGE_CONFIDENCE_THRESHOLD", "0.45"))
        )
        self.model: Any | None = None
        self.load_error: str | None = None
        self.labels = CLASS_LABELS
        self.preprocessing = "zero_to_one"
        self.image_size = (224, 224)

    @property
    def is_loaded(self) -> bool:
        return self.model is not None

    def load(self) -> None:
        if self.model is not None:
            return

        if not self.model_path.exists():
            self.load_error = f"Model file not found: {self.model_path}"
            return

        try:
            from tensorflow.keras.models import load_model

            self._load_metadata()
            self.model = load_model(self.model_path, compile=False)
            self._validate_label_count()
            self.load_error = None
        except Exception as exc:
            self.load_error = str(exc)
            self.model = None

    def predict(self, image_bytes: bytes) -> dict[str, Any]:
        self.load()
        if self.model is None:
            detail = self.load_error or "Model is not loaded."
            raise ModelNotReadyError(detail)

        image = self._prepare_image(image_bytes)
        raw_predictions = self.model.predict(image, verbose=0)[0]
        scores = self._to_probabilities(raw_predictions)

        class_index = int(np.argmax(scores))
        confidence = float(scores[class_index])
        species = self.labels[class_index]

        top_indices = np.argsort(scores)[::-1][:5]
        top_predictions = [
            {
                "species": self.labels[int(index)],
                "confidence": round(float(scores[int(index)]), 4),
            }
            for index in top_indices
        ]
        needs_review = confidence < self.confidence_threshold

        return {
            "species": species,
            "recommendation": RECOMMENDATIONS.get(species, "No recommendation is available for this species."),
            "confidence": round(confidence, 4),
            "top_predictions": top_predictions,
            "needs_review": needs_review,
            "message": (
                "The model is not very confident. Use a clearer image or compare the top matches."
                if needs_review
                else "Prediction confidence is above the configured review threshold."
            ),
        }

    def _prepare_image(self, image_bytes: bytes) -> np.ndarray:
        try:
            image = Image.open(BytesIO(image_bytes))
            image = ImageOps.exif_transpose(image).convert("RGB")
        except UnidentifiedImageError as exc:
            raise InvalidImageError("The uploaded file is not a valid image.") from exc

        if image.width < 96 or image.height < 96:
            raise InvalidImageError("The uploaded image is too small. Use a clearer image at least 96 x 96 pixels.")

        image = image.resize(self.image_size, Image.Resampling.LANCZOS)
        image_array = np.asarray(image, dtype=np.float32)
        if self.preprocessing == "zero_to_one":
            image_array = image_array / 255.0
        return np.expand_dims(image_array, axis=0)

    def _load_metadata(self) -> None:
        labels = self._read_labels()
        if labels:
            self.labels = labels

        metadata = self._read_json(self.model_path.with_suffix(".metadata.json"))
        if isinstance(metadata, dict):
            preprocessing = str(metadata.get("preprocessing") or self.preprocessing)
            if preprocessing in {"zero_to_one", "raw"}:
                self.preprocessing = preprocessing

            image_size = metadata.get("image_size")
            if (
                isinstance(image_size, list)
                and len(image_size) == 2
                and all(isinstance(value, int) for value in image_size)
            ):
                self.image_size = (image_size[0], image_size[1])

    def _read_labels(self) -> list[str] | None:
        candidates = [
            self.labels_path,
            self.model_path.with_suffix(".labels.json"),
            self.model_path.with_suffix(".metadata.json"),
        ]
        for path in candidates:
            if not path:
                continue
            payload = self._read_json(path)
            if isinstance(payload, list):
                return [str(label).upper() for label in payload]
            if isinstance(payload, dict):
                labels = payload.get("labels") or payload.get("classes") or payload.get("class_names")
                if isinstance(labels, list):
                    return [str(label).upper() for label in labels]
        return None

    @staticmethod
    def _read_json(path: Path) -> object | None:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def _validate_label_count(self) -> None:
        output_shape = getattr(self.model, "output_shape", None)
        output_classes = output_shape[-1] if isinstance(output_shape, tuple) else None
        if output_classes and output_classes != len(self.labels):
            raise ModelNotReadyError(
                f"Model outputs {output_classes} classes, but {len(self.labels)} labels are configured."
            )

    @staticmethod
    def _to_probabilities(raw_predictions: Any) -> np.ndarray:
        scores = np.asarray(raw_predictions, dtype=float)
        if scores.ndim != 1:
            scores = scores.reshape(-1)

        total = float(np.sum(scores))
        has_negative = bool(np.any(scores < 0))
        if has_negative or total <= 0 or not np.isclose(total, 1.0, atol=1e-3):
            scores = scores - np.max(scores)
            exp_scores = np.exp(scores)
            scores = exp_scores / np.sum(exp_scores)

        return scores
