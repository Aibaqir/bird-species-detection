import os
import tempfile
import threading
from pathlib import Path

from .recommendations import RECOMMENDATIONS


class InvalidAudioError(ValueError):
    pass


class AudioModelNotReadyError(RuntimeError):
    pass


class BirdSoundClassifier:
    HUMAN_AUDIO_LABELS = {"HUMAN VOCAL", "HUMAN WHISTLE"}

    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir
        self._model = None
        self._lock = threading.Lock()
        self.load_error: str | None = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        if self._model is not None:
            return

        with self._lock:
            if self._model is not None:
                return

            self.cache_dir.mkdir(parents=True, exist_ok=True)
            os.environ.setdefault("KAGGLEHUB_CACHE", str(self.cache_dir))

            try:
                import birdnet

                self._model = birdnet.load("acoustic", "2.4", "tf", lang="en_us")
                self.load_error = None
            except Exception as exc:  # pragma: no cover - depends on local model cache.
                self.load_error = str(exc)
                raise AudioModelNotReadyError(str(exc)) from exc

    def predict(self, audio_bytes: bytes, suffix: str = ".wav") -> dict[str, object]:
        if not audio_bytes:
            raise InvalidAudioError("The uploaded audio is empty.")

        self.load()
        assert self._model is not None

        suffix = suffix if suffix.lower() in {".wav", ".ogg", ".flac", ".mp3", ".m4a"} else ".wav"
        temp_path: Path | None = None

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(audio_bytes)
                temp_path = Path(temp_file.name)

            with self._lock:
                prediction = self._model.predict(
                    str(temp_path),
                    top_k=5,
                    default_confidence_threshold=0.03,
                    max_audio_duration_min=0.5,
                    n_workers=1,
                    batch_size=1,
                )

            rows = prediction.to_structured_array()
            top_predictions = self._aggregate_predictions(rows)

            if not top_predictions:
                return {
                    "species": "NO CONFIDENT BIRD CALL DETECTED",
                    "confidence": 0,
                    "recommendation": (
                        "Record a clearer 5 to 15 second bird call with low background noise, "
                        "then try again."
                    ),
                    "top_predictions": [],
                }

            best = top_predictions[0]
            species = best["species"]
            if species in self.HUMAN_AUDIO_LABELS:
                return {
                    "species": species,
                    "confidence": best["confidence"],
                    "recommendation": (
                        "This recording is likely a human voice or whistle, not a bird call. "
                        "Please record a natural bird call with less speech, whistling, or background noise."
                    ),
                    "top_predictions": top_predictions,
                }

            return {
                "species": species,
                "confidence": best["confidence"],
                "recommendation": RECOMMENDATIONS.get(
                    species,
                    (
                        "Audio-based BirdNET result. Confirm the species visually when possible "
                        "and use a longer, clearer recording for stronger confidence."
                    ),
                ),
                "top_predictions": top_predictions,
            }
        except AudioModelNotReadyError:
            raise
        except Exception as exc:
            raise InvalidAudioError(f"Could not analyze this audio file: {exc}") from exc
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink(missing_ok=True)

    @staticmethod
    def _aggregate_predictions(rows) -> list[dict[str, object]]:
        scores: dict[str, float] = {}

        for row in rows:
            species = BirdSoundClassifier._format_species(str(row["species_name"]))
            confidence = float(row["confidence"])
            scores[species] = max(scores.get(species, 0.0), confidence)

        return [
            {"species": species, "confidence": round(confidence, 4)}
            for species, confidence in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:5]
        ]

    @staticmethod
    def _format_species(label: str) -> str:
        if "_" in label:
            _, common_name = label.split("_", 1)
            return common_name.upper()
        return label.upper()
