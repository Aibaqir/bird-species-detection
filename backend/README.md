# Bird Species Prediction Backend

FastAPI service for loading `BirdsModel.h5` and predicting bird species from uploaded images.

## Run

```powershell
py -3.11 -m venv D:\bakirFNF_runtime\.venv
D:\bakirFNF_runtime\.venv\Scripts\python.exe -m pip install -r requirements-api.txt
D:\bakirFNF_runtime\.venv\Scripts\python.exe -m pip install -r requirements-ml.txt
D:\bakirFNF_runtime\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If `tensorflow-intel` downloads slowly, keep the API dependencies installed first. The backend will still start and `/health` will report that the model runtime is missing.

## Endpoints

- `GET /health`
- `POST /predict` with multipart form field `file`

## Training for Better Image Accuracy

Use `train_realworld_image_model.py` for the strongest training pipeline. It can
download CUB-200-2011 automatically through TensorFlow Datasets, train from
Kaggle Birds 525 through KaggleHub, or train from a local folder dataset.

The backend can automatically read the trained model's `.labels.json` and
`.metadata.json` sidecar files.

See `TRAINING.md` for commands and `DATASETS.md` for dataset recommendations.
