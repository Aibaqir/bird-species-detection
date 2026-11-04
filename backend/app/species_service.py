import json
import re
import threading
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


class SpeciesResolver:
    HUMAN_AUDIO_LABELS = {"human vocal", "human whistle"}

    def __init__(self, cache_path: Path) -> None:
        self.cache_path = cache_path
        self._lock = threading.Lock()
        self._cache: dict[str, dict[str, object]] | None = None

    def resolve(self, species: str) -> dict[str, object] | None:
        key = self._normalize_key(species)
        if not key or key.startswith("no confident"):
            return None
        if key in self.HUMAN_AUDIO_LABELS:
            return self._human_audio_profile(species)

        cache = self._load_cache()
        if key in cache:
            return cache[key]

        with self._lock:
            cache = self._load_cache()
            if key in cache:
                return cache[key]

            profile = self._fetch_profile(species)
            if profile:
                cache[key] = profile
                self._save_cache(cache)
            return profile

    def _fetch_profile(self, species: str) -> dict[str, object] | None:
        query = urllib.parse.quote(species.title())
        search_url = f"https://api.inaturalist.org/v1/taxa?q={query}&rank=species&taxon_id=3&per_page=5"
        search_payload = self._get_json(search_url)
        candidates = search_payload.get("results", [])
        if not candidates:
            return None

        taxon = self._choose_taxon(species, candidates)
        taxon_id = taxon.get("id")
        if not taxon_id:
            return None

        detail_payload = self._get_json(f"https://api.inaturalist.org/v1/taxa/{taxon_id}")
        details = (detail_payload.get("results") or [taxon])[0]
        return self._to_profile(details)

    def _to_profile(self, taxon: dict[str, Any]) -> dict[str, object]:
        ancestors = taxon.get("ancestors") or []
        family = self._ancestor_name(ancestors, "family")
        order = self._ancestor_name(ancestors, "order")
        photo = taxon.get("default_photo") or {}
        listed_taxa = taxon.get("listed_taxa") or []

        common_name = taxon.get("preferred_common_name") or taxon.get("matched_term") or taxon.get("name") or "Unknown bird"
        summary = self._clean_summary(taxon.get("wikipedia_summary")) or (
            f"{common_name} is a bird species recorded by iNaturalist. Use visual and audio evidence together for the best identification."
        )

        return {
            "source": "iNaturalist",
            "taxonId": taxon.get("id"),
            "species": str(common_name).upper(),
            "commonName": common_name,
            "scientificName": taxon.get("name") or "Unknown",
            "family": family,
            "order": order,
            "status": self._conservation_status(taxon),
            "region": self._region(listed_taxa),
            "imageUrl": photo.get("large_url") or photo.get("medium_url") or photo.get("url"),
            "thumbnailUrl": photo.get("square_url") or photo.get("medium_url") or photo.get("url"),
            "photoAttribution": photo.get("attribution"),
            "description": summary,
            "wikipediaUrl": taxon.get("wikipedia_url"),
            "observationsCount": taxon.get("observations_count"),
        }

    @staticmethod
    def _choose_taxon(species: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        requested = species.casefold()
        for taxon in candidates:
            names = [
                str(taxon.get("preferred_common_name") or "").casefold(),
                str(taxon.get("matched_term") or "").casefold(),
                str(taxon.get("name") or "").casefold(),
            ]
            if requested in names:
                return taxon
        return max(candidates, key=lambda item: int(item.get("observations_count") or 0))

    @staticmethod
    def _ancestor_name(ancestors: list[dict[str, Any]], rank: str) -> str:
        for ancestor in ancestors:
            if ancestor.get("rank") == rank:
                return ancestor.get("preferred_common_name") or ancestor.get("name") or "Unknown"
        return "Unknown"

    @staticmethod
    def _conservation_status(taxon: dict[str, Any]) -> str:
        status = taxon.get("conservation_status") or {}
        label = status.get("status_name") or status.get("iucn")
        if label:
            return str(label).replace("_", " ").title()
        return "Not listed"

    @staticmethod
    def _region(listed_taxa: list[dict[str, Any]]) -> str:
        regions = []
        for item in listed_taxa:
            place = item.get("place") or {}
            name = place.get("display_name") or place.get("name")
            if name and name not in regions:
                regions.append(name)
            if len(regions) == 3:
                break
        return ", ".join(regions) if regions else "Global records available"

    @staticmethod
    def _clean_summary(summary: str | None) -> str:
        if not summary:
            return ""
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", summary)).strip()

    @staticmethod
    def _human_audio_profile(species: str) -> dict[str, object]:
        label = species.strip().upper()
        return {
            "source": "BirdNET non-bird label",
            "taxonId": None,
            "species": label,
            "commonName": label.title(),
            "scientificName": "Homo sapiens",
            "family": "Humans",
            "order": "Primates",
            "status": "Not applicable",
            "region": "Recorded audio source",
            "imageUrl": "/images/human-audio.svg",
            "thumbnailUrl": "/images/human-audio.svg",
            "photoAttribution": "Generated interface placeholder",
            "description": (
                "The submitted audio appears to contain a human voice or whistle rather "
                "than a bird call. Record a natural bird sound with minimal speech or "
                "background noise for bird identification."
            ),
            "wikipediaUrl": None,
            "observationsCount": None,
        }

    def _load_cache(self) -> dict[str, dict[str, object]]:
        if self._cache is not None:
            return self._cache

        if self.cache_path.exists():
            try:
                self._cache = json.loads(self.cache_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._cache = {}
        else:
            self._cache = {}

        return self._cache

    def _save_cache(self, cache: dict[str, dict[str, object]]) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _get_json(url: str) -> dict[str, Any]:
        request = urllib.request.Request(url, headers={"User-Agent": "bakirFNF-bird-fyp/1.0"})
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _normalize_key(species: str) -> str:
        return re.sub(r"\s+", " ", species.strip().casefold())
