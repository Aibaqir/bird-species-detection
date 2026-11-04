"use client";

import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  AlertTriangle,
  BarChart3,
  CalendarDays,
  Camera,
  Download,
  Eye,
  FileText,
  ImageIcon,
  Mic,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { findBirdProfile, getBirdProfile, type BirdProfile } from "@/lib/birds";
import {
  apiUrl,
  clearPredictionHistory,
  deletePredictionHistoryItem,
  fetchPredictionHistory,
  type Prediction,
} from "@/lib/api";
import { clearHistory, deleteHistoryItem, getHistory, saveHistoryItem, type HistoryItem } from "@/lib/history";

type ConfidenceStatus = "High Confidence" | "Medium Confidence" | "Needs Review";
type SortMode = "newest" | "oldest" | "highest" | "lowest";

const confidenceFilters: Array<"all" | ConfidenceStatus> = ["all", "High Confidence", "Medium Confidence", "Needs Review"];
const methodFilters: Array<"all" | HistoryItem["method"]> = ["all", "Image", "Camera", "Sound"];
const fallbackImage = "/images/sample-bird.jpg";

export default function HistoryPage() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [query, setQuery] = useState("");
  const [dateFilter, setDateFilter] = useState("");
  const [confidenceFilter, setConfidenceFilter] = useState<(typeof confidenceFilters)[number]>("all");
  const [methodFilter, setMethodFilter] = useState<(typeof methodFilters)[number]>("all");
  const [sortMode, setSortMode] = useState<SortMode>("newest");
  const [selectedItem, setSelectedItem] = useState<HistoryItem | null>(null);

  useEffect(() => {
    void loadHistory();
  }, []);

  async function loadHistory() {
    try {
      const databaseItems = (await fetchPredictionHistory()).map(predictionToHistoryItem);
      setItems(databaseItems);
      databaseItems.forEach(saveHistoryItem);
    } catch {
      setItems(getHistory());
    }
  }

  const filteredItems = useMemo(() => {
    return items
      .filter((item) => {
        const searchText = [item.species, item.filename, item.profile?.scientificName].join(" ").toLowerCase();
        const createdDate = toDateInputValue(item.createdAt);
        const status = getConfidenceStatus(item.confidence).label;
        return (
          searchText.includes(query.toLowerCase()) &&
          (!dateFilter || createdDate === dateFilter) &&
          (confidenceFilter === "all" || status === confidenceFilter) &&
          (methodFilter === "all" || item.method === methodFilter)
        );
      })
      .sort((a, b) => sortHistoryItems(a, b, sortMode));
  }, [items, query, dateFilter, confidenceFilter, methodFilter, sortMode]);

  const overview = useMemo(() => buildOverview(items), [items]);

  function refreshHistory() {
    void loadHistory();
  }

  async function handleDelete(id: string) {
    if (!window.confirm("Delete this history record?")) return;
    try {
      await deletePredictionHistoryItem(id);
    } catch {
      // Keep local deletion working if the backend is unavailable or the item is local-only.
    }
    deleteHistoryItem(id);
    if (selectedItem?.id === id) setSelectedItem(null);
    refreshHistory();
  }

  async function handleClear() {
    if (!items.length) return;
    if (!window.confirm("Clear all prediction history?")) return;
    try {
      await clearPredictionHistory();
    } catch {
      // Local fallback still clears records shown from browser storage.
    }
    clearHistory();
    setSelectedItem(null);
    setItems([]);
  }

  return (
    <main className="page">
      <div className="page-title">
        <div>
          <h1>History</h1>
          <p>View, filter, export, and manage your past bird identifications.</p>
        </div>
      </div>

      <section className="history-layout">
        <div className="panel history-panel">
          <div className="panel-head history-head">
            <div>
              <h2>Identification History</h2>
              <p>{filteredItems.length} of {items.length} predictions shown</p>
            </div>
            <div className="history-actions">
              <button type="button" onClick={() => exportCsv(filteredItems)}><Download size={16} /> CSV</button>
              <button type="button" onClick={() => void exportPdf(filteredItems)}><FileText size={16} /> PDF</button>
              <button className="danger-button" onClick={handleClear} type="button"><Trash2 size={17} /> Clear</button>
            </div>
          </div>

          <div className="history-controls">
            <label className="history-search">
              <Search size={17} />
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by bird or file..." />
            </label>
            <label>
              <span>Date</span>
              <input type="date" value={dateFilter} onChange={(event) => setDateFilter(event.target.value)} />
            </label>
            <label>
              <span>Status</span>
              <select value={confidenceFilter} onChange={(event) => setConfidenceFilter(event.target.value as typeof confidenceFilter)}>
                {confidenceFilters.map((filter) => <option key={filter} value={filter}>{filter === "all" ? "All confidence" : filter}</option>)}
              </select>
            </label>
            <label>
              <span>Type</span>
              <select value={methodFilter} onChange={(event) => setMethodFilter(event.target.value as typeof methodFilter)}>
                {methodFilters.map((filter) => <option key={filter} value={filter}>{filter === "all" ? "All types" : filter}</option>)}
              </select>
            </label>
            <label>
              <span>Sort</span>
              <select value={sortMode} onChange={(event) => setSortMode(event.target.value as SortMode)}>
                <option value="newest">Newest</option>
                <option value="oldest">Oldest</option>
                <option value="highest">Highest confidence</option>
                <option value="lowest">Lowest confidence</option>
              </select>
            </label>
          </div>

          <div className="history-list">
            {filteredItems.length ? filteredItems.map((item) => (
              <article className="history-row" key={item.id}>
                <HistoryThumbnail item={item} />
                <div className="history-main">
                  <div>
                    <strong>{item.species}</strong>
                    <small>{item.filename}</small>
                  </div>
                  <TopPredictions item={item} />
                </div>
                <div className="history-confidence">
                  <b>{formatPercent(item.confidence)}</b>
                  <StatusBadge status={getConfidenceStatus(item.confidence)} />
                </div>
                <div className="history-method">{methodIcon(item.method)}<span>{item.method}</span></div>
                <time>{formatDateTime(item.createdAt)}</time>
                <div className="history-row-actions">
                  <button type="button" onClick={() => setSelectedItem(item)}><Eye size={16} /> View</button>
                  <button className="icon-danger" type="button" onClick={() => void handleDelete(item.id)} aria-label={`Delete ${item.species}`}>
                    <Trash2 size={16} />
                  </button>
                </div>
              </article>
            )) : <p className="empty-copy">No matching history records. Your predictions will appear here.</p>}
          </div>
        </div>

        <aside className="panel history-summary">
          <h2>History Overview</h2>
          <div className="overview-grid">
            <OverviewStat icon={<BarChart3 size={20} />} label="Total" value={overview.total} />
            <OverviewStat icon={<ImageIcon size={20} />} label="Image" value={overview.image} />
            <OverviewStat icon={<Camera size={20} />} label="Camera" value={overview.camera} />
            <OverviewStat icon={<Mic size={20} />} label="Sound" value={overview.sound} />
            <OverviewStat label="High Confidence" value={overview.high} />
            <OverviewStat label="Medium Confidence" value={overview.medium} />
            <OverviewStat label="Needs Review" value={overview.review} />
            <OverviewStat label="Average Confidence" value={overview.averageConfidence} />
          </div>
          <div className="history-most">
            <strong>Most detected bird</strong>
            <p>{overview.mostDetected}</p>
          </div>
        </aside>
      </section>

      {selectedItem && (
        <HistoryDetailsModal
          item={selectedItem}
          onClose={() => setSelectedItem(null)}
          onDelete={() => void handleDelete(selectedItem.id)}
        />
      )}
    </main>
  );
}

function HistoryThumbnail({ item }: { item: HistoryItem }) {
  return (
    <span className="thumb history-thumb">
      <img
        src={thumbnailFor(item)}
        alt={`${item.species} uploaded thumbnail`}
        onError={(event) => {
          const image = event.currentTarget;
          if (image.dataset.fallbackApplied) return;
          image.dataset.fallbackApplied = "true";
          image.src = fallbackImage;
        }}
      />
    </span>
  );
}

function TopPredictions({ item }: { item: HistoryItem }) {
  const topPredictions = getTopPredictions(item);
  return (
    <ol className="top-three">
      {topPredictions.map((prediction) => (
        <li key={`${item.id}-${prediction.species}`}>
          <span>{prediction.species}</span>
          <b>{formatPercent(prediction.confidence)}</b>
        </li>
      ))}
    </ol>
  );
}

function HistoryDetailsModal({ item, onClose, onDelete }: { item: HistoryItem; onClose: () => void; onDelete: () => void }) {
  const profile = getProfileForItem(item);
  const status = getConfidenceStatus(item.confidence);

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label={`${item.species} history details`}>
      <article className="history-modal panel">
        <div className="modal-head">
          <div>
            <span className={`status-badge ${status.className}`}>{status.label}</span>
            <h2>{item.species}</h2>
            <p>{profile.scientificName}</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close details"><X size={18} /></button>
        </div>

        <div className="history-detail-grid">
          <div className="history-detail-image">
            <img src={thumbnailFor(item)} alt={`${item.species} uploaded image`} onError={(event) => { event.currentTarget.src = fallbackImage; }} />
          </div>
          <div className="history-detail-content">
            {status.label === "Needs Review" && (
              <div className="notice warning">
                <AlertTriangle size={18} />
                Low confidence prediction. Compare the top matches before using this result.
              </div>
            )}
            <dl className="history-detail-facts">
              <div><dt>Confidence</dt><dd>{formatPercent(item.confidence)}</dd></div>
              <div><dt>Input Type</dt><dd>{item.method}</dd></div>
              <div><dt>Date & Time</dt><dd>{formatDateTime(item.createdAt)}</dd></div>
              <div><dt>Uploaded File</dt><dd>{item.filename}</dd></div>
              <div><dt>Family</dt><dd>{profile.family}</dd></div>
              <div><dt>Region</dt><dd>{profile.region}</dd></div>
              <div><dt>Habitat</dt><dd>{profile.habitat}</dd></div>
              <div><dt>Food</dt><dd>{profile.diet}</dd></div>
            </dl>
            <section>
              <h3>Top-3 Predictions</h3>
              <TopPredictions item={item} />
            </section>
            <section>
              <h3>Description</h3>
              <p>{profile.description}</p>
            </section>
          </div>
        </div>

        <div className="modal-actions">
          <button type="button" onClick={onClose}>Close</button>
          <button className="danger-button" type="button" onClick={onDelete}><Trash2 size={16} /> Delete Record</button>
        </div>
      </article>
    </div>
  );
}

function OverviewStat({ icon, label, value }: { icon?: ReactNode; label: string; value: string | number }) {
  return (
    <span>
      {icon}
      <b>{value}</b>
      <small>{label}</small>
    </span>
  );
}

function methodIcon(method: HistoryItem["method"]) {
  if (method === "Camera") return <Camera size={16} />;
  if (method === "Sound") return <Mic size={16} />;
  return <ImageIcon size={16} />;
}

function getConfidenceStatus(confidence: number): { label: ConfidenceStatus; className: string } {
  if (confidence >= 0.8) return { label: "High Confidence", className: "status-high" };
  if (confidence >= 0.55) return { label: "Medium Confidence", className: "status-medium" };
  return { label: "Needs Review", className: "status-review" };
}

function StatusBadge({ status }: { status: ReturnType<typeof getConfidenceStatus> }) {
  return <span className={`status-badge ${status.className}`}>{status.label}</span>;
}

function getTopPredictions(item: HistoryItem) {
  const predictions = Array.isArray(item.top_predictions) && item.top_predictions.length
    ? item.top_predictions
    : [{ species: item.species, confidence: item.confidence }];
  return predictions.slice(0, 3);
}

function thumbnailFor(item: HistoryItem) {
  if (item.previewUrl && !item.previewUrl.startsWith("blob:")) return resolveHistoryImageUrl(item.previewUrl);
  if (item.profile?.thumbnailUrl) return item.profile.thumbnailUrl;
  if (item.profile?.imageUrl) return item.profile.imageUrl;
  const profile = findBirdProfile(item.species);
  return profile?.image ?? fallbackImage;
}

function resolveHistoryImageUrl(path: string) {
  if (path.startsWith("/data/")) return apiUrl(path) ?? path;
  return path;
}

function getProfileForItem(item: HistoryItem): BirdProfile {
  const localProfile = findBirdProfile(item.species) ?? getBirdProfile(item.species);
  return {
    ...localProfile,
    scientificName: item.profile?.scientificName ?? localProfile.scientificName,
    family: cleanProfileValue(item.profile?.family) ?? localProfile.family,
    order: cleanProfileValue(item.profile?.order) ?? localProfile.order,
    status: cleanProfileValue(item.profile?.status) ?? localProfile.status,
    region: cleanProfileValue(item.profile?.region) ?? localProfile.region,
    description: item.profile?.description ?? localProfile.description,
  };
}

function cleanProfileValue(value?: string) {
  if (!value || value === "Unknown" || value === "Global records available") return undefined;
  return value;
}

function buildOverview(items: HistoryItem[]) {
  const statusCounts = items.reduce(
    (counts, item) => {
      const status = getConfidenceStatus(item.confidence).label;
      if (status === "High Confidence") counts.high += 1;
      if (status === "Medium Confidence") counts.medium += 1;
      if (status === "Needs Review") counts.review += 1;
      return counts;
    },
    { high: 0, medium: 0, review: 0 },
  );

  const average = items.length ? items.reduce((sum, item) => sum + item.confidence, 0) / items.length : 0;
  const mostDetected = getMostDetectedBird(items);

  return {
    total: items.length,
    image: items.filter((item) => item.method === "Image").length,
    camera: items.filter((item) => item.method === "Camera").length,
    sound: items.filter((item) => item.method === "Sound").length,
    high: statusCounts.high,
    medium: statusCounts.medium,
    review: statusCounts.review,
    averageConfidence: formatPercent(average),
    mostDetected,
  };
}

function getMostDetectedBird(items: HistoryItem[]) {
  if (!items.length) return "No predictions yet";
  const counts = new Map<string, number>();
  for (const item of items) {
    counts.set(item.species, (counts.get(item.species) ?? 0) + 1);
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] ?? "No predictions yet";
}

function sortHistoryItems(a: HistoryItem, b: HistoryItem, sortMode: SortMode) {
  if (sortMode === "oldest") return new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
  if (sortMode === "highest") return b.confidence - a.confidence;
  if (sortMode === "lowest") return a.confidence - b.confidence;
  return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
}

function exportCsv(items: HistoryItem[]) {
  const rows = [
    ["Bird name", "Confidence score", "Top-3 predictions", "Prediction type", "Date/time", "Uploaded image path", "Needs review status"],
    ...items.map((item) => [
      item.species,
      formatPercent(item.confidence),
      getTopPredictions(item).map((prediction) => `${prediction.species} - ${formatPercent(prediction.confidence)}`).join(" | "),
      item.method,
      formatDateTime(item.createdAt),
      item.image_path ?? item.previewUrl ?? thumbnailFor(item),
      getConfidenceStatus(item.confidence).label,
    ]),
  ];
  const csv = rows.map((row) => row.map(escapeCsv).join(",")).join("\n");
  downloadBlob(csv, "bird-history.csv", "text/csv;charset=utf-8");
}

function predictionToHistoryItem(prediction: Prediction): HistoryItem {
  return {
    ...prediction,
    id: prediction.id ?? crypto.randomUUID(),
    method: prediction.method ?? "Image",
    createdAt: prediction.createdAt ?? prediction.created_at ?? new Date().toISOString(),
    previewUrl: prediction.previewUrl ?? prediction.thumbnail_url ?? prediction.image_url,
    filename: prediction.filename || "uploaded-file",
    top_predictions: prediction.top_predictions?.length
      ? prediction.top_predictions
      : [{ species: prediction.species, confidence: prediction.confidence }],
  };
}

async function exportPdf(items: HistoryItem[]) {
  const { jsPDF } = await import("jspdf");
  const pdf = new jsPDF();
  let y = 18;

  pdf.setFont("helvetica", "bold");
  pdf.setFontSize(18);
  pdf.text("Bird Identification History", 14, y);
  y += 12;
  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(10);

  for (const item of items) {
    if (y > 250) {
      pdf.addPage();
      y = 18;
    }
    const lines = [
      `Bird: ${item.species}`,
      `Confidence: ${formatPercent(item.confidence)} (${getConfidenceStatus(item.confidence).label})`,
      `Top-3: ${getTopPredictions(item).map((prediction) => `${prediction.species} - ${formatPercent(prediction.confidence)}`).join("; ")}`,
      `Type: ${item.method}`,
      `Date/time: ${formatDateTime(item.createdAt)}`,
      `Uploaded image path: ${thumbnailFor(item)}`,
    ];
    pdf.setFont("helvetica", "bold");
    pdf.text(item.species, 14, y);
    y += 6;
    pdf.setFont("helvetica", "normal");
    for (const line of lines.slice(1)) {
      const wrapped = pdf.splitTextToSize(line, 180);
      pdf.text(wrapped, 14, y);
      y += wrapped.length * 5 + 1;
    }
    y += 4;
  }

  pdf.save("bird-history.pdf");
}

function escapeCsv(value: string) {
  return `"${value.replace(/"/g, '""')}"`;
}

function downloadBlob(content: string, filename: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function toDateInputValue(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toISOString().slice(0, 10);
}

function formatDateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown date";
  return date.toLocaleString();
}

function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`;
}
