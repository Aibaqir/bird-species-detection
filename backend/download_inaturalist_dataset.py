import argparse
import json
import time
import urllib.parse
import urllib.request
from http.client import RemoteDisconnected
from pathlib import Path
from urllib.error import HTTPError, URLError


DEFAULT_SPECIES = [
    "American Robin",
    "Bald Eagle",
    "Barn Swallow",
    "Blue Jay",
    "Canada Goose",
    "Common Raven",
    "European Starling",
    "Great Blue Heron",
    "House Sparrow",
    "Mallard",
    "Mourning Dove",
    "Northern Cardinal",
    "Red-tailed Hawk",
    "Rock Pigeon",
    "Snowy Egret",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download a bird image dataset from public iNaturalist observations."
    )
    parser.add_argument("--output-dir", default=Path(r"D:\AFYP\datasets\inaturalist_birds"), type=Path)
    parser.add_argument("--images-per-species", default=40, type=int)
    parser.add_argument("--species", nargs="*", default=DEFAULT_SPECIES)
    parser.add_argument("--sleep", default=0.25, type=float, help="Delay between image downloads.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "source": "iNaturalist public observations",
        "images_per_species": args.images_per_species,
        "species": {},
    }

    for species in args.species:
        print(f"Downloading {species}...")
        target_dir = args.output_dir / normalize_species(species)
        target_dir.mkdir(parents=True, exist_ok=True)
        try:
            urls = get_photo_urls(species, args.images_per_species)
            downloaded = download_species_images(target_dir, urls, args.sleep)
        except Exception as exc:
            print(f"  failed {species}: {exc}")
            downloaded = count_existing_images(target_dir)
        manifest["species"][normalize_species(species)] = {
            "requested": args.images_per_species,
            "downloaded": downloaded,
            "source_name": species,
        }
        print(f"  saved {downloaded} images")

    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Dataset saved to {args.output_dir}")


def get_photo_urls(species: str, limit: int) -> list[str]:
    urls: list[str] = []
    page = 1

    while len(urls) < limit and page <= 5:
        query = urllib.parse.urlencode(
            {
                "taxon_name": species,
                "taxon_id": 3,
                "photos": "true",
                "quality_grade": "research",
                "order_by": "votes",
                "per_page": 100,
                "page": page,
            }
        )
        payload = get_json(f"https://api.inaturalist.org/v1/observations?{query}")
        for observation in payload.get("results", []):
            for photo in observation.get("photos", []):
                url = photo.get("url")
                if not url:
                    continue
                medium_url = url.replace("square.", "medium.").replace("small.", "medium.")
                if medium_url not in urls:
                    urls.append(medium_url)
                if len(urls) == limit:
                    break
            if len(urls) == limit:
                break
        page += 1

    return urls


def download_species_images(target_dir: Path, urls: list[str], sleep_seconds: float) -> int:
    downloaded = 0
    for index, url in enumerate(urls, start=1):
        extension = Path(urllib.parse.urlparse(url).path).suffix or ".jpg"
        target_path = target_dir / f"{index:04d}{extension}"
        if target_path.exists() and target_path.stat().st_size > 0:
            downloaded += 1
            continue

        try:
            request = urllib.request.Request(url, headers={"User-Agent": "bird-fyp-dataset-builder/1.0"})
            with urllib.request.urlopen(request, timeout=30) as response:
                target_path.write_bytes(response.read())
            downloaded += 1
            time.sleep(sleep_seconds)
        except Exception as exc:
            print(f"  skipped {url}: {exc}")

    return downloaded


def get_json(url: str) -> dict:
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "bird-fyp-dataset-builder/1.0"})
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, RemoteDisconnected) as exc:
            last_error = exc
            time.sleep(attempt * 2)
    raise RuntimeError(f"Could not fetch JSON after retries: {last_error}")


def count_existing_images(target_dir: Path) -> int:
    extensions = {".jpg", ".jpeg", ".png", ".webp"}
    return sum(1 for path in target_dir.glob("*") if path.suffix.lower() in extensions and path.stat().st_size > 0)


def normalize_species(species: str) -> str:
    return " ".join(species.strip().upper().split())


if __name__ == "__main__":
    main()
