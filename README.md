# Bird Species Identifier

Modern rebuild of the original Django bird species classifier.

## Structure

- `backend/` - FastAPI prediction API using the trained Keras bird model
- `frontend/` - Next.js app with image upload, preview, prediction result, About, and Contact pages

## Frontend

```powershell
cd C:\Users\MCS\Desktop\bakirFNF\frontend
npm install
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Open:

```text
http://127.0.0.1:3000
```

## Backend

The backend virtual environment can live on D: to avoid filling C:.

```powershell
py -3.11 -m venv D:\bakirFNF_runtime\.venv
D:\bakirFNF_runtime\.venv\Scripts\python.exe -m pip install -r C:\Users\MCS\Desktop\bakirFNF\backend\requirements.txt
cd C:\Users\MCS\Desktop\bakirFNF\backend
D:\bakirFNF_runtime\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

API:

```text
GET  http://127.0.0.1:8000/health
POST http://127.0.0.1:8000/predict
```

## Database

The backend now uses SQLite for prediction history:

```text
backend/data/bird_app.sqlite3
backend/data/uploads/
backend/data/thumbnails/
```

Prediction endpoints save successful image, camera, and sound predictions to
the database. The History page reads from:

```text
GET    /history
GET    /history/{id}
DELETE /history/{id}
DELETE /history
```

If port `8000` is already occupied by an older backend process, the frontend can
point to a new API port with `frontend/.env.local`:

```text
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8001
```

## Training

For better image accuracy, use the backend real-world transfer-learning
pipeline. It supports CUB-200-2011, Kaggle Birds 525, and local folder datasets.
Full instructions are in `backend/TRAINING.md`; dataset recommendations are in
`backend/DATASETS.md`.

Current trained model:

- `backend/models/BirdsModel_combined_75_best_plus.keras`
- trained on `D:\AFYP\datasets\birds_combined_75_plus_black_baza`
- 75 unique supported image species
- 13,775 clean images, including 275 Black Baza images
- about 96.9% held-out test accuracy
- about 99.2% held-out top-3 accuracy
- fixes the tested real-world Black Baza Google image case
