import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
THUMBNAIL_DIR = DATA_DIR / "thumbnails"
DATABASE_PATH = DATA_DIR / "bird_app.sqlite3"


def init_database() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)

    with connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                species TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                confidence REAL NOT NULL,
                method TEXT NOT NULL,
                created_at TEXT NOT NULL,
                image_path TEXT,
                thumbnail_path TEXT,
                needs_review INTEGER NOT NULL DEFAULT 0,
                message TEXT,
                top_predictions_json TEXT NOT NULL,
                profile_json TEXT
            )
            """
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_predictions_created_at ON predictions(created_at DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_predictions_species ON predictions(species)")


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def save_prediction(
    *,
    filename: str,
    method: str,
    result: dict[str, Any],
    upload_bytes: bytes | None = None,
    upload_suffix: str = ".jpg",
) -> dict[str, Any]:
    init_database()
    record_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    image_path: str | None = None
    thumbnail_path: str | None = None

    if upload_bytes:
        image_path, thumbnail_path = save_upload_images(record_id, upload_bytes, upload_suffix)

    top_predictions = result.get("top_predictions") if isinstance(result.get("top_predictions"), list) else []
    if not top_predictions:
        top_predictions = [{"species": result.get("species"), "confidence": result.get("confidence", 0)}]

    profile = result.get("profile")
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO predictions (
                id, filename, species, recommendation, confidence, method, created_at,
                image_path, thumbnail_path, needs_review, message, top_predictions_json, profile_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                filename,
                str(result.get("species") or ""),
                str(result.get("recommendation") or ""),
                float(result.get("confidence") or 0),
                method,
                created_at,
                image_path,
                thumbnail_path,
                1 if result.get("needs_review") else 0,
                result.get("message"),
                json.dumps(top_predictions),
                json.dumps(profile) if isinstance(profile, dict) else None,
            ),
        )

    saved = get_prediction(record_id)
    if not saved:
        raise RuntimeError("Prediction was saved but could not be loaded.")
    return saved


def save_upload_images(record_id: str, upload_bytes: bytes, upload_suffix: str) -> tuple[str | None, str | None]:
    suffix = normalize_suffix(upload_suffix)
    original_path = UPLOAD_DIR / f"{record_id}{suffix}"
    thumbnail_path = THUMBNAIL_DIR / f"{record_id}.jpg"
    original_path.write_bytes(upload_bytes)

    try:
        image = Image.open(original_path)
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail((480, 480), Image.Resampling.LANCZOS)
        image.save(thumbnail_path, format="JPEG", quality=84, optimize=True)
    except (OSError, UnidentifiedImageError):
        return relative_data_path(original_path), None

    return relative_data_path(original_path), relative_data_path(thumbnail_path)


def list_predictions() -> list[dict[str, Any]]:
    init_database()
    with connect() as connection:
        rows = connection.execute("SELECT * FROM predictions ORDER BY datetime(created_at) DESC").fetchall()
    return [row_to_prediction(row) for row in rows]


def get_prediction(record_id: str) -> dict[str, Any] | None:
    init_database()
    with connect() as connection:
        row = connection.execute("SELECT * FROM predictions WHERE id = ?", (record_id,)).fetchone()
    return row_to_prediction(row) if row else None


def delete_prediction(record_id: str) -> bool:
    init_database()
    record = get_prediction(record_id)
    if not record:
        return False

    with connect() as connection:
        deleted = connection.execute("DELETE FROM predictions WHERE id = ?", (record_id,)).rowcount

    remove_file(record.get("image_path"))
    remove_file(record.get("thumbnail_path"))
    return deleted > 0


def clear_predictions() -> int:
    records = list_predictions()
    with connect() as connection:
        deleted = connection.execute("DELETE FROM predictions").rowcount

    for record in records:
        remove_file(record.get("image_path"))
        remove_file(record.get("thumbnail_path"))
    return deleted


def row_to_prediction(row: sqlite3.Row) -> dict[str, Any]:
    profile = parse_json(row["profile_json"], default=None)
    thumbnail_url = url_for_data_path(row["thumbnail_path"])
    image_url = url_for_data_path(row["image_path"])
    return {
        "id": row["id"],
        "filename": row["filename"],
        "species": row["species"],
        "recommendation": row["recommendation"],
        "confidence": row["confidence"],
        "method": row["method"],
        "createdAt": row["created_at"],
        "created_at": row["created_at"],
        "image_path": row["image_path"],
        "thumbnail_path": row["thumbnail_path"],
        "image_url": image_url,
        "thumbnail_url": thumbnail_url,
        "previewUrl": thumbnail_url or image_url,
        "needs_review": bool(row["needs_review"]),
        "message": row["message"],
        "top_predictions": parse_json(row["top_predictions_json"], default=[]),
        "profile": profile,
    }


def parse_json(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def normalize_suffix(suffix: str) -> str:
    suffix = suffix.lower().strip()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        return ".jpg"
    return suffix


def relative_data_path(path: Path) -> str:
    return str(path.relative_to(DATA_DIR)).replace("\\", "/")


def url_for_data_path(path: str | None) -> str | None:
    if not path:
        return None
    return f"/data/{path}"


def remove_file(path: object) -> None:
    if not isinstance(path, str) or not path:
        return
    target = (DATA_DIR / path).resolve()
    try:
        target.relative_to(DATA_DIR.resolve())
    except ValueError:
        return
    target.unlink(missing_ok=True)
