import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .audio_service import AudioModelNotReadyError, BirdSoundClassifier, InvalidAudioError
from .database import DATA_DIR, clear_predictions, delete_prediction, get_prediction, init_database, list_predictions, save_prediction
from .model_service import BirdClassifier, InvalidImageError, ModelNotReadyError
from .species_service import SpeciesResolver

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = Path(os.getenv("BIRD_MODEL_PATH", BASE_DIR / "models" / "BirdsModel.h5"))
LABELS_PATH = os.getenv("BIRD_LABELS_PATH")
BIRDNET_CACHE_DIR = Path(os.getenv("BIRDNET_CACHE_DIR", r"D:\bakirFNF_runtime\birdnet_cache"))
SPECIES_CACHE_PATH = Path(os.getenv("SPECIES_CACHE_PATH", r"D:\bakirFNF_runtime\species_cache.json"))

classifier = BirdClassifier(MODEL_PATH, labels_path=Path(LABELS_PATH) if LABELS_PATH else None)
sound_classifier = BirdSoundClassifier(BIRDNET_CACHE_DIR)
species_resolver = SpeciesResolver(SPECIES_CACHE_PATH)

app = FastAPI(
    title="Bird Species Prediction API",
    description="Predicts bird species from uploaded images and returns feeding recommendations.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
init_database()
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")


@app.on_event("startup")
def load_model_on_startup() -> None:
    init_database()
    classifier.load()


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "model_loaded": classifier.is_loaded,
        "model_path": str(MODEL_PATH),
        "load_error": classifier.load_error,
        "classes": classifier.labels,
        "class_count": len(classifier.labels),
        "image_confidence_threshold": classifier.confidence_threshold,
        "audio_model_loaded": sound_classifier.is_loaded,
        "audio_model_cache": str(BIRDNET_CACHE_DIR),
        "audio_load_error": sound_classifier.load_error,
        "species_cache": str(SPECIES_CACHE_PATH),
        "database": str(DATA_DIR / "bird_app.sqlite3"),
    }


@app.post("/predict")
async def predict(file: UploadFile = File(...), method: str = Form("Image")) -> dict[str, object]:
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=400, detail="Please upload a JPG, PNG, or WEBP image.")
    if method not in {"Image", "Camera"}:
        raise HTTPException(status_code=400, detail="Prediction method must be Image or Camera.")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="The uploaded image is empty.")

    try:
        result = classifier.predict(image_bytes)
    except InvalidImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ModelNotReadyError as exc:
        raise HTTPException(status_code=503, detail=f"Prediction model is not ready: {exc}") from exc

    payload = {
        "filename": file.filename,
        **_with_species_profile(result),
    }
    return save_prediction(
        filename=file.filename or "uploaded-image.jpg",
        method=method,
        result=payload,
        upload_bytes=image_bytes,
        upload_suffix=Path(file.filename or "uploaded-image.jpg").suffix,
    )


@app.post("/predict-audio")
async def predict_audio(file: UploadFile = File(...)) -> dict[str, object]:
    if file.content_type not in {"audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp4", "audio/ogg", "audio/flac"}:
        raise HTTPException(status_code=400, detail="Please upload or record a WAV, MP3, OGG, FLAC, or M4A audio file.")

    audio_bytes = await file.read()
    suffix = Path(file.filename or "bird-sound.wav").suffix or ".wav"

    try:
        result = sound_classifier.predict(audio_bytes, suffix=suffix)
    except InvalidAudioError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AudioModelNotReadyError as exc:
        raise HTTPException(status_code=503, detail=f"Bird sound model is not ready: {exc}") from exc

    payload = {
        "filename": file.filename,
        **_with_species_profile(result),
    }
    return save_prediction(
        filename=file.filename or "bird-sound.wav",
        method="Sound",
        result=payload,
        upload_bytes=None,
        upload_suffix=suffix,
    )


@app.get("/history")
def prediction_history() -> list[dict[str, object]]:
    return list_predictions()


@app.get("/history/{record_id}")
def prediction_history_item(record_id: str) -> dict[str, object]:
    record = get_prediction(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="History record not found.")
    return record


@app.delete("/history/{record_id}")
def delete_prediction_history_item(record_id: str) -> dict[str, object]:
    deleted = delete_prediction(record_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="History record not found.")
    return {"deleted": True, "id": record_id}


@app.delete("/history")
def clear_prediction_history() -> dict[str, object]:
    deleted = clear_predictions()
    return {"deleted": deleted}


@app.get("/species/resolve")
def resolve_species(name: str) -> dict[str, object]:
    profile = species_resolver.resolve(name)
    if not profile:
        raise HTTPException(status_code=404, detail=f"No bird profile found for {name}.")
    return profile


def _with_species_profile(result: dict[str, object]) -> dict[str, object]:
    species = str(result.get("species") or "")
    try:
        profile = species_resolver.resolve(species)
    except Exception:
        profile = None
    if profile:
        return {**result, "profile": profile}
    return result
