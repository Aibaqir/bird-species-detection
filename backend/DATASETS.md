# Recommended Public Bird Datasets

Use these datasets to improve real-world bird species prediction. The best
results usually come from combining a large public dataset with your own local
test photos from the kind of images users will upload.

## Best Practical Choice: Kaggle Birds 525

Dataset: `gpiosenka/100-bird-species`

Why use it:

- 525 bird species
- around 89k images in prepared train/validation/test folders
- images are already resized to `224 x 224 x 3`
- good for a broad demo because it covers many species

Training command:

```powershell
cd D:\AFYP\ggs\backend
.\venv\Scripts\python.exe train_realworld_image_model.py `
  --source kaggle-birds525 `
  --output-model models\BirdsModel_realworld.keras `
  --backbone efficientnetb0 `
  --epochs 15 `
  --fine-tune-epochs 10 `
  --batch-size 16
```

Kaggle downloads may require Kaggle login/API setup on your machine.

## Local Birds 525 Mirror Workflow

Kaggle may require login or dataset terms approval. This project also supports
the downloaded Hugging Face parquet mirror of Birds 525:

```text
D:\AFYP\datasets\birds525_hf_parquet\data
```

Use the cleaner/exporter to build balanced folder datasets:

```powershell
cd D:\AFYP\ggs\backend
.\venv\Scripts\python.exe build_birds525_clean_dataset.py `
  --parquet-dir D:\AFYP\datasets\birds525_hf_parquet\data `
  --output-dir D:\AFYP\datasets\birds525_clean_50_balanced `
  --species-count 50 `
  --images-per-class 200 `
  --select-by-count `
  --min-raw-images 200
```

The cleaner filters invalid, very small, blurry, and duplicate images. It also
accepts `--extra-dir` for your own mobile-camera or manually downloaded web
photos arranged by species folder.

## Best Automatic Starter: CUB-200-2011 Through TensorFlow Datasets

Dataset: `caltech_birds2011`

Why use it:

- downloads automatically through TensorFlow Datasets
- 200 bird species
- 11,788 images
- official train/test split
- useful for fine-grained species classification

Training command:

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

This is the easiest dataset to start with because the script can download it
without manually arranging folders.

## Strong Regional Choice: Indian Birds Dataset

Dataset: `ichhadhari/indian-birds`

Why use it:

- 25 Indian bird species
- about 37,000 images
- useful if your demo focuses on South Asian birds
- high image count per class

Download it from Kaggle, then train with:

```powershell
.\venv\Scripts\python.exe train_realworld_image_model.py `
  --source folder `
  --data-dir D:\AFYP\indian-birds `
  --output-model models\BirdsModel_realworld.keras
```

## Research-Grade Option: iNaturalist / Aves

iNaturalist-style datasets are useful for real-world generalization because
they contain community photos with varied lighting, angles, backgrounds, and
camera quality. They are usually larger and more complex, so they are better
for advanced training after the project demo pipeline is stable.

## Dataset Quality Checklist

Before training, check:

- each species folder has enough images
- labels are correct
- duplicate images are removed
- images include flying and sitting birds
- images include different lighting, angles, backgrounds, and distances
- test images are not copied from training images

Bad labels hurt accuracy more than a small model does.
