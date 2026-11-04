$ErrorActionPreference = "Stop"

# This looks for a .venv folder inside your current backend folder
$venvPython = ".\venv\Scripts\python.exe"
$combined75PlusModel = ".\models\BirdsModel_combined_75_best_plus.keras"
$combined75Model = ".\models\BirdsModel_combined_75_best.keras"
$combinedModel = ".\models\BirdsModel_combined_74.keras"
$birds525Model = ".\models\BirdsModel_birds525_subset.keras"
$largerModel = ".\models\BirdsModel_larger.keras"
$expandedModel = ".\models\BirdsModel_expanded.keras"
$realWorldModel = ".\models\BirdsModel_realworld.keras"
if (Test-Path $combined75PlusModel) {
    $env:BIRD_MODEL_PATH = $combined75PlusModel
} elseif (Test-Path $combined75Model) {
    $env:BIRD_MODEL_PATH = $combined75Model
} elseif (Test-Path $combinedModel) {
    $env:BIRD_MODEL_PATH = $combinedModel
} elseif (Test-Path $birds525Model) {
    $env:BIRD_MODEL_PATH = $birds525Model
} elseif (Test-Path $largerModel) {
    $env:BIRD_MODEL_PATH = $largerModel
} elseif (Test-Path $expandedModel) {
    $env:BIRD_MODEL_PATH = $expandedModel
} elseif (Test-Path $realWorldModel) {
    $env:BIRD_MODEL_PATH = $realWorldModel
}
$env:BIRDNET_CACHE_DIR = ".\birdnet_cache"
$env:KAGGLEHUB_CACHE = ".\birdnet_cache"

if (-not (Test-Path $venvPython)) {
    Write-Host "Virtual environment not found. Creating it now..."
    python -m venv venv
    Write-Host "Installing dependencies..."
    & $venvPython -m pip install -r requirements.txt
    & $venvPython -m pip install -r requirements-api.txt
    & $venvPython -m pip install -r requirements-ml.txt
}

Write-Host "Starting Uvicorn server..."
if ($env:BIRD_MODEL_PATH) {
    Write-Host "Using image model: $env:BIRD_MODEL_PATH"
}
& $venvPython -m uvicorn app.main:app --host 127.0.0.1 --port 8001
