# Training the Image Model for Better Accuracy

You cannot make image prediction perfect with code alone. Accuracy mainly comes
from clean data: correct labels, enough images per species, and pictures that
look like the photos users will upload.

## Current Trained Model

This project now includes a strengthened 75-species combined Birds 525 image model:

```text
backend\models\BirdsModel_combined_75_best_plus.keras
backend\models\BirdsModel_combined_75_best_plus.labels.json
backend\models\BirdsModel_combined_75_best_plus.metadata.json
```

It was expanded from the 74-species model, adds `BLACK BAZA`, and was then
strengthened with extra real-world Black Baza images. The active dataset is:

```text
D:\AFYP\datasets\birds_combined_75_plus_black_baza
```

Dataset summary:

- 75 unique bird species
- 13,775 images total
- at least 140 images per species
- 275 images for `BLACK BAZA`
- MobileNetV2 transfer learning
- image size `224 x 224`
- held-out test accuracy: about `96.9%`
- held-out top-3 accuracy: about `99.2%`
- tested real-world Black Baza Google image: `BLACK BAZA` at about `98.8%`

The backend startup script now automatically uses this strengthened model when it exists.

This backend now supports three training paths:

- Best for accuracy: `train_realworld_image_model.py` can automatically download
  CUB-200-2011 through TensorFlow Datasets, use Kaggle Birds 525 through
  KaggleHub, or train from your own folder dataset.
- Recommended: `train_transfer_image_model.py` trains a stronger EfficientNet
  classifier from your class folders.
- Optional: `train_image_model.py` continues training the old
  `models/BirdsModel.h5` model for the existing 10 classes.

See `DATASETS.md` for dataset recommendations.

## Build a Cleaner 50 or 100 Species Dataset

Use `build_birds525_clean_dataset.py` when you want a larger, cleaner folder
dataset from the downloaded Birds 525 parquet mirror. It can:

- export 50 or 100 species
- balance the maximum images per class
- remove corrupt images
- remove very small images
- remove blurry images
- remove near-duplicate images
- merge your own mobile or web images from an extra folder

The current balanced 50-species dataset was built at:

```text
D:\AFYP\datasets\birds525_clean_50_balanced
```

It contains:

- 50 species
- 200 clean images per species
- 10,000 images total

Build a fresh 50-species candidate dataset like this:

```powershell
cd D:\AFYP\ggs\backend
.\venv\Scripts\python.exe build_birds525_clean_dataset.py `
  --parquet-dir D:\AFYP\datasets\birds525_hf_parquet\data `
  --output-dir D:\AFYP\datasets\birds525_clean_70candidates_200 `
  --species-count 70 `
  --images-per-class 200 `
  --select-by-count `
  --min-raw-images 190 `
  --clear-output
```

The candidate export gives you extra classes so you can keep only classes that
reach exactly 200 clean images.

For your own Google or mobile-camera photos, create folders like this:

```text
D:\AFYP\extra_bird_photos\
  BALD EAGLE\
    phone_001.jpg
    web_001.jpg
  RED-TAILED HAWK\
    phone_001.jpg
```

Then include them during export:

```powershell
.\venv\Scripts\python.exe build_birds525_clean_dataset.py `
  --parquet-dir D:\AFYP\datasets\birds525_hf_parquet\data `
  --output-dir D:\AFYP\datasets\birds525_with_extra `
  --species-count 100 `
  --images-per-class 200 `
  --extra-dir D:\AFYP\extra_bird_photos `
  --clear-output
```

For Google images, download only images you are allowed to use and put them in
the correct species folder. The script can reject blurry and duplicate files,
but wrong-species images still need human checking.

## Best Accuracy Pipeline

This command trains a real-world model with:

- transfer learning
- EfficientNet, MobileNetV2, or ResNet50
- rotation, zoom, horizontal flip, brightness, and contrast augmentation
- dropout and batch normalization
- early stopping
- train/validation/test evaluation
- saved labels and metadata for the FastAPI backend

Start with CUB-200-2011 because it downloads automatically:

```powershell
cd D:\AFYP\ggs\backend
.\venv\Scripts\python.exe train_realworld_image_model.py `
  --source tfds-cub2011 `
  --output-model models\BirdsModel_realworld.keras `
  --backbone efficientnetb0 `
  --epochs 15 `
  --fine-tune-epochs 10 `
  --batch-size 16
```

For the larger Kaggle Birds 525 dataset:

```powershell
.\venv\Scripts\python.exe train_realworld_image_model.py `
  --source kaggle-birds525 `
  --output-model models\BirdsModel_realworld.keras `
  --backbone efficientnetb0 `
  --epochs 15 `
  --fine-tune-epochs 10 `
  --batch-size 16
```

For your own dataset folder:

```powershell
.\venv\Scripts\python.exe train_realworld_image_model.py `
  --source folder `
  --data-dir D:\AFYP\bird_dataset `
  --output-model models\BirdsModel_realworld.keras
```

For the new 50-species balanced dataset:

```powershell
.\venv\Scripts\python.exe train_realworld_image_model.py `
  --source folder `
  --data-dir D:\AFYP\datasets\birds525_clean_50_balanced `
  --output-model models\BirdsModel_50species_clean.keras `
  --backbone mobilenetv2 `
  --epochs 10 `
  --fine-tune-epochs 6 `
  --batch-size 16 `
  --min-images-per-class 200
```

For the current combined 74-species model:

```powershell
.\venv\Scripts\python.exe train_realworld_image_model.py `
  --source folder `
  --data-dir D:\AFYP\datasets\birds_combined_74 `
  --output-model models\BirdsModel_combined_74.keras `
  --backbone mobilenetv2 `
  --epochs 10 `
  --fine-tune-epochs 6 `
  --batch-size 16 `
  --min-images-per-class 100 `
  --dropout 0.4
```

For the current deployed 75-species model, first expand from the 74-species
base:

```powershell
.\venv\Scripts\python.exe train_expand_image_model.py `
  --base-model models\BirdsModel_combined_74.keras `
  --data-dir D:\AFYP\datasets\birds_combined_75 `
  --output-model models\BirdsModel_combined_75_best.keras `
  --epochs 8 `
  --fine-tune-epochs 4 `
  --batch-size 8 `
  --min-images-per-class 100 `
  --fine-tune-layers 40
```

Then strengthen Black Baza with the cleaned extra real-world images:

```powershell
.\venv\Scripts\python.exe train_expand_image_model.py `
  --base-model models\BirdsModel_combined_75_best.keras `
  --data-dir D:\AFYP\datasets\birds_combined_75_plus_black_baza `
  --output-model models\BirdsModel_combined_75_best_plus.keras `
  --epochs 4 `
  --fine-tune-epochs 3 `
  --batch-size 8 `
  --min-images-per-class 100 `
  --fine-tune-layers 35 `
  --learning-rate 2e-4 `
  --fine-tune-learning-rate 3e-6
```

After training, start the API with:

```powershell
$env:BIRD_MODEL_PATH="D:\AFYP\ggs\backend\models\BirdsModel_realworld.keras"
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Recommended Dataset Layout

Create one folder per bird species:

```text
D:\AFYP\bird_dataset\
  ABBOTTS BABBLER\
    image001.jpg
    image002.jpg
  ABBOTTS BOOBY\
    image001.jpg
    image002.jpg
  ALEXANDRINE PARAKEET\
    image001.jpg
```

Folder names become the model labels. You can include more than the old 10
species when using `train_transfer_image_model.py`.

For good accuracy, aim for:

- at least 100 to 300 images per species
- different angles, lighting, backgrounds, ages, and poses
- no wrong species inside a folder
- no duplicate or almost duplicate images
- validation images that are not copied from training images

## Install ML Dependencies

From `backend`:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements-api.txt
.\venv\Scripts\python.exe -m pip install -r requirements-ml.txt
```

## Train a Better Transfer-Learning Model

From `backend`:

```powershell
.\venv\Scripts\python.exe train_transfer_image_model.py `
  --data-dir D:\AFYP\bird_dataset `
  --output-model models\BirdsModel_transfer.keras `
  --epochs 12 `
  --fine-tune-epochs 8 `
  --batch-size 16
```

The script will:

- train an EfficientNetB0 image classifier
- use ImageNet pretrained weights
- apply image augmentation while training
- handle imbalanced datasets with class weights
- save labels to `models\BirdsModel_transfer.labels.json`
- save metadata to `models\BirdsModel_transfer.metadata.json`

The backend reads the labels and metadata automatically when the model path
points to this trained file.

## Run the API with the New Model

```powershell
$env:BIRD_MODEL_PATH="D:\AFYP\ggs\backend\models\BirdsModel_transfer.keras"
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then check:

```text
GET http://127.0.0.1:8000/health
POST http://127.0.0.1:8000/predict
```

`/health` should show your trained class list.

## Optional: Fine-Tune the Existing 10-Class Model

Use this only when your dataset folders exactly match the current 10 labels in
`app/recommendations.py`.

```powershell
.\venv\Scripts\python.exe train_image_model.py `
  --data-dir D:\AFYP\bird_dataset `
  --base-model models\BirdsModel.h5 `
  --output-model models\BirdsModel_finetuned.h5 `
  --epochs 10 `
  --batch-size 16
```

## Prediction Safety

The API now returns `needs_review: true` when image confidence is below the
configured threshold. Set the threshold like this:

```powershell
$env:IMAGE_CONFIDENCE_THRESHOLD="0.55"
```

A higher value is stricter and will flag more predictions for review.
