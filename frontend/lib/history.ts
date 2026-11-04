import type { Prediction } from "./api";

export type HistoryItem = Prediction & {
  id: string;
  method: "Image" | "Camera" | "Sound";
  createdAt: string;
  previewUrl?: string;
};

const HISTORY_KEY = "bird-identification-history";
const LAST_RESULT_KEY = "bird-last-result";

export function getHistory(): HistoryItem[] {
  if (typeof window === "undefined") return [];
  const raw = window.localStorage.getItem(HISTORY_KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as HistoryItem[];
    const normalized = parsed.map(normalizeHistoryItem);
    const deduped = dedupeHistory(normalized);
    if (deduped.length !== parsed.length || JSON.stringify(deduped) !== JSON.stringify(parsed)) {
      window.localStorage.setItem(HISTORY_KEY, JSON.stringify(deduped));
    }
    return deduped;
  } catch {
    return [];
  }
}

export function saveHistoryItem(item: HistoryItem) {
  const normalized = normalizeHistoryItem(item);
  const history = dedupeHistory([normalized, ...getHistory()]).slice(0, 50);
  window.localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
  window.sessionStorage.setItem(LAST_RESULT_KEY, JSON.stringify(normalized));
}

export function updateHistoryItem(item: HistoryItem) {
  const history = dedupeHistory([normalizeHistoryItem(item), ...getHistory().filter((entry) => entry.id !== item.id)]).slice(0, 50);
  window.localStorage.setItem(HISTORY_KEY, JSON.stringify(history));

  const lastResult = getLastResult();
  if (lastResult?.id === item.id) {
    window.sessionStorage.setItem(LAST_RESULT_KEY, JSON.stringify(item));
  }
}

export function getLastResult(): HistoryItem | null {
  if (typeof window === "undefined") return null;
  const raw = window.sessionStorage.getItem(LAST_RESULT_KEY) ?? window.localStorage.getItem(HISTORY_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    const item = Array.isArray(parsed) ? parsed[0] ?? null : parsed;
    return item ? normalizeHistoryItem(item) : null;
  } catch {
    return null;
  }
}

export function deleteHistoryItem(id: string) {
  const history = getHistory().filter((entry) => entry.id !== id);
  window.localStorage.setItem(HISTORY_KEY, JSON.stringify(history));

  const lastResult = getLastResult();
  if (lastResult?.id === id) {
    window.sessionStorage.removeItem(LAST_RESULT_KEY);
  }
}

export function clearHistory() {
  window.localStorage.removeItem(HISTORY_KEY);
  window.sessionStorage.removeItem(LAST_RESULT_KEY);
}

function dedupeHistory(items: HistoryItem[]) {
  const seen = new Set<string>();
  return items.filter((item) => {
    if (seen.has(item.id)) return false;
    seen.add(item.id);
    return true;
  });
}

function normalizeHistoryItem(item: HistoryItem): HistoryItem {
  const topPredictions = Array.isArray(item.top_predictions) && item.top_predictions.length
    ? item.top_predictions
    : [{ species: item.species, confidence: item.confidence }];

  return {
    ...item,
    filename: item.filename || fallbackFilename(item.method),
    confidence: Number.isFinite(item.confidence) ? item.confidence : 0,
    top_predictions: topPredictions.slice(0, 5),
  };
}

function fallbackFilename(method: HistoryItem["method"]) {
  if (method === "Camera") return "camera-capture.jpg";
  if (method === "Sound") return "bird-sound.wav";
  return "uploaded-image.jpg";
}
