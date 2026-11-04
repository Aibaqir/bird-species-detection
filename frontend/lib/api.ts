export type Prediction = {
  id?: string;
  filename: string;
  species: string;
  recommendation: string;
  confidence: number;
  method?: "Image" | "Camera" | "Sound";
  createdAt?: string;
  created_at?: string;
  image_path?: string;
  thumbnail_path?: string;
  image_url?: string;
  thumbnail_url?: string;
  previewUrl?: string;
  needs_review?: boolean;
  message?: string;
  profile?: SpeciesProfile;
  top_predictions: Array<{
    species: string;
    confidence: number;
  }>;
};

export type SpeciesProfile = {
  source: string;
  taxonId?: number;
  species: string;
  commonName: string;
  scientificName: string;
  family: string;
  order: string;
  status: string;
  region: string;
  imageUrl?: string;
  thumbnailUrl?: string;
  photoAttribution?: string;
  description: string;
  wikipediaUrl?: string;
  observationsCount?: number;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export function apiUrl(path?: string | null) {
  if (!path) return undefined;
  if (path.startsWith("http://") || path.startsWith("https://") || path.startsWith("data:")) return path;
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

export async function predictBird(file: File, method: "Image" | "Camera" = "Image"): Promise<Prediction> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("method", method);

  const response = await fetch(`${API_BASE_URL}/predict`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let message = "Prediction failed. Please try another image.";
    try {
      const payload = await response.json();
      message = payload.detail ?? message;
    } catch {
      // Keep the friendly fallback message.
    }
    throw new Error(message);
  }

  return response.json();
}

export async function predictAudio(file: File): Promise<Prediction> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/predict-audio`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let message = "Audio recognition is not configured yet. Add a trained bird-sound model to enable this feature.";
    try {
      const payload = await response.json();
      message = payload.detail ?? message;
    } catch {
      // Keep the fallback message.
    }
    throw new Error(message);
  }

  return response.json();
}

export async function resolveSpecies(name: string): Promise<SpeciesProfile> {
  const response = await fetch(`${API_BASE_URL}/species/resolve?name=${encodeURIComponent(name)}`);

  if (!response.ok) {
    throw new Error("Could not load this bird profile.");
  }

  return response.json();
}

export async function fetchPredictionHistory(): Promise<Prediction[]> {
  const response = await fetch(`${API_BASE_URL}/history`);
  if (!response.ok) {
    throw new Error("Could not load prediction history.");
  }
  return response.json();
}

export async function deletePredictionHistoryItem(id: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/history/${encodeURIComponent(id)}`, { method: "DELETE" });
  if (!response.ok) {
    throw new Error("Could not delete this history record.");
  }
}

export async function clearPredictionHistory(): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/history`, { method: "DELETE" });
  if (!response.ok) {
    throw new Error("Could not clear prediction history.");
  }
}
