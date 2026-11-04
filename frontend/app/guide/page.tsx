"use client";

import Image from "next/image";
import { useEffect, useMemo, useState } from "react";
import { Database, Filter, Heart, Search } from "lucide-react";
import { birdProfiles, guideDatasetSummary, type BirdProfile } from "@/lib/birds";
import type { SpeciesProfile } from "@/lib/api";
import { getHistory } from "@/lib/history";

type GuideProfile = {
  species: string;
  scientificName: string;
  family?: string;
  order?: string;
  status?: string;
  region?: string;
  image: string;
  description?: string;
  source: "Local model" | "Resolved profile";
  observationsCount?: number;
  datasetSource?: BirdProfile["datasetSource"];
  trainingImages?: number;
  supportedByCurrentModel?: boolean;
  supportedByCleanDataset?: boolean;
};

const sourceFilters = ["Current model", "Clean 50 dataset"] as const;
type SourceFilter = (typeof sourceFilters)[number];

export default function GuidePage() {
  const [query, setQuery] = useState("");
  const [historyProfiles, setHistoryProfiles] = useState<GuideProfile[]>([]);
  const [selectedSources, setSelectedSources] = useState<SourceFilter[]>([]);

  useEffect(() => {
    const profiles = getHistory()
      .map((item) => item.profile)
      .filter((profile): profile is SpeciesProfile => Boolean(profile))
      .map(profileToGuideProfile);
    setHistoryProfiles(profiles);
  }, []);

  const guideProfiles = useMemo(() => dedupeProfiles([...birdProfiles.map(localToGuideProfile), ...historyProfiles]), [historyProfiles]);
  const filtered = useMemo(
    () => guideProfiles.filter((bird) => {
      const searchText = [bird.species, bird.scientificName, bird.family, bird.order, bird.region].join(" ").toLowerCase();
      const matchesQuery = searchText.includes(query.toLowerCase());
      const matchesSource =
        selectedSources.length === 0 ||
        selectedSources.some((source) =>
          source === "Current model" ? bird.supportedByCurrentModel : bird.supportedByCleanDataset,
        );
      return matchesQuery && matchesSource;
    }),
    [guideProfiles, query, selectedSources],
  );

  return (
    <main className="page">
      <div className="page-title">
        <div>
          <h1>Bird Guide</h1>
          <p>Explore the current model classes and the clean 50-species training dataset.</p>
        </div>
      </div>

      <div className="guide-toolbar">
        <label>
          <Search size={18} />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search birds..." />
        </label>
        <button type="button" onClick={() => { setQuery(""); setSelectedSources([]); }}>
          <Filter size={18} /> All Categories
        </button>
      </div>

      <section className="guide-layout">
        <div className="bird-grid">
          {filtered.map((bird) => (
            <article className="bird-card" key={bird.species}>
              <div>
                {isNextImage(bird.image) ? <Image src={bird.image} alt={bird.species} fill sizes="220px" /> : <img src={bird.image} alt={bird.species} />}
                <Heart size={20} />
              </div>
              <h2>{bird.species}</h2>
              <em>{bird.scientificName}</em>
              <p>{bird.description}</p>
              <dl className="guide-facts">
                {bird.family && <div><dt>Family</dt><dd>{bird.family}</dd></div>}
                {bird.order && <div><dt>Order</dt><dd>{bird.order}</dd></div>}
                {bird.region && <div><dt>Region</dt><dd>{bird.region}</dd></div>}
                {bird.trainingImages ? <div><dt>Images</dt><dd>{bird.trainingImages.toLocaleString()}</dd></div> : null}
                {bird.observationsCount ? <div><dt>Records</dt><dd>{bird.observationsCount.toLocaleString()}</dd></div> : null}
              </dl>
              <span>{bird.datasetSource ?? bird.status ?? bird.source}</span>
            </article>
          ))}
        </div>

        <aside className="panel filters-panel">
          <h2>Filters</h2>
          <div className="guide-count">
            <Database size={20} />
            <b>{filtered.length}</b>
            <small>Showing of {guideProfiles.length} classes</small>
          </div>
          <div className="guide-count">
            <Database size={20} />
            <b>{guideDatasetSummary.currentModelClasses}</b>
            <small>Current model classes</small>
          </div>
          <div className="guide-count">
            <Database size={20} />
            <b>{guideDatasetSummary.cleanDatasetClasses}</b>
            <small>Clean dataset classes, {guideDatasetSummary.cleanDatasetImagesPerClass} images each</small>
          </div>
          {sourceFilters.map((source) => (
            <label key={source}>
              <input
                type="checkbox"
                checked={selectedSources.includes(source)}
                onChange={() => toggleSourceFilter(source, selectedSources, setSelectedSources)}
              />
              {source}
            </label>
          ))}
          <div className="did-you-know">
            <strong>Did you know?</strong>
            <p>The clean 50-species dataset is balanced at 200 accepted images per class.</p>
          </div>
        </aside>
      </section>
    </main>
  );
}

function localToGuideProfile(profile: BirdProfile): GuideProfile {
  return {
    species: profile.species,
    scientificName: profile.scientificName,
    family: profile.family,
    order: profile.order,
    status: profile.status,
    region: profile.region,
    image: profile.image,
    description: profile.description,
    source: "Local model",
    datasetSource: profile.datasetSource,
    trainingImages: profile.trainingImages,
    supportedByCurrentModel: profile.supportedByCurrentModel,
    supportedByCleanDataset: profile.supportedByCleanDataset,
  };
}

function profileToGuideProfile(profile: SpeciesProfile): GuideProfile {
  return {
    species: profile.species,
    scientificName: profile.scientificName,
    family: cleanUnknown(profile.family),
    order: cleanUnknown(profile.order),
    status: cleanUnknown(profile.status),
    region: cleanUnknown(profile.region),
    image: profile.thumbnailUrl ?? profile.imageUrl ?? "/images/sample-bird.jpg",
    description: profile.description,
    source: "Resolved profile",
    observationsCount: profile.observationsCount,
  };
}

function dedupeProfiles(profiles: GuideProfile[]) {
  const seen = new Set<string>();
  return profiles.filter((profile) => {
    const key = profile.species.toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function cleanUnknown(value?: string) {
  if (!value || value === "Unknown" || value === "Global records available") return undefined;
  return value;
}

function toggleSourceFilter(
  source: SourceFilter,
  selectedSources: SourceFilter[],
  setSelectedSources: (sources: SourceFilter[]) => void,
) {
  setSelectedSources(
    selectedSources.includes(source)
      ? selectedSources.filter((item) => item !== source)
      : [...selectedSources, source],
  );
}

function isNextImage(src: string) {
  return src.startsWith("/") && !src.endsWith(".svg");
}
