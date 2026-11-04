"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AlertTriangle, ArrowLeft, Bookmark, Download, RotateCcw, Share2, Star } from "lucide-react";
import { findBirdProfile, getBirdProfile, type BirdProfile } from "@/lib/birds";
import { apiUrl, resolveSpecies, type SpeciesProfile } from "@/lib/api";
import { getLastResult, type HistoryItem } from "@/lib/history";

export default function ResultsPage() {
  const [result, setResult] = useState<HistoryItem | null>(null);
  const [liveProfile, setLiveProfile] = useState<SpeciesProfile | null>(null);

  useEffect(() => {
    setResult(getLastResult());
  }, []);

  useEffect(() => {
    if (!result || result.profile) return;
    resolveSpecies(result.species).then(setLiveProfile).catch(() => setLiveProfile(null));
  }, [result]);

  if (!result) {
    return (
      <main className="page">
        <div className="panel empty-results">
          <h1>No result found</h1>
          <p>Start a bird identification to see the prediction result here.</p>
          <Link className="primary-link" href="/identify">Start Identification</Link>
        </div>
      </main>
    );
  }

  const exactProfile = findBirdProfile(result.species);
  const profile = exactProfile ?? getBirdProfile(result.species);
  const resolvedProfile = result.profile ?? liveProfile;
  const confidence = Math.round(result.confidence * 100);
  const resultImage = resolveResultImage(result.previewUrl ?? resolvedProfile?.imageUrl ?? profile.image);
  const facts = buildFacts(resolvedProfile, exactProfile);
  const details = buildDetails(result, resolvedProfile, exactProfile);
  const ResultBadgeIcon = result.needs_review ? AlertTriangle : Star;
  const resultBadgeLabel = result.needs_review ? "Possible Match" : "Best Match";

  return (
    <main className="page">
      <div className="page-title inline-title">
        <Link href="/identify"><ArrowLeft size={18} /> New Search</Link>
        <div>
          <h1>Results</h1>
          <p>Prediction result with confidence, bird details, and top matches.</p>
        </div>
      </div>

      <section className="results-layout">
        <div className="panel result-detail">
          <div className="result-main">
            <div className="result-image">
              <img
                src={resultImage}
                alt={result.species}
                onError={(event) => {
                  const image = event.currentTarget;
                  if (image.dataset.fallbackApplied) return;
                  image.dataset.fallbackApplied = "true";
                  image.src = profile.image;
                }}
              />
            </div>
            <div>
              <span className={`badge ${result.needs_review ? "warning-badge" : ""}`}>
                <ResultBadgeIcon size={15} /> {resultBadgeLabel}
              </span>
              <h2>{result.species}</h2>
              <em>{resolvedProfile?.scientificName ?? profile.scientificName}</em>
              <span className="confidence-pill">{confidence}% Confidence</span>
              {result.needs_review && (
                <div className="notice warning">
                  <AlertTriangle size={18} />
                  {result.message ?? "Confidence is low. Compare the top matches before using this result."}
                </div>
              )}
              <p>{resolvedProfile?.description ?? profile.description}</p>
              {facts.length > 0 && (
                <dl className="fact-list">
                  {facts.map(([label, value]) => (
                    <div key={label}><dt>{label}</dt><dd>{value}</dd></div>
                  ))}
                </dl>
              )}
            </div>
          </div>

          <div className="button-row report-actions">
            <button type="button"><Bookmark size={18} /> Save Result</button>
            <button type="button"><Share2 size={18} /> Share</button>
            <button type="button" onClick={() => downloadReportPdf(result, resolvedProfile, exactProfile)}>
              <Download size={18} /> Download Report
            </button>
          </div>

          <div className="detail-grid">
            {details.map((item) => (
              <article className="detail-item" key={item.label}>
                <b>{item.label}</b>
                <p>{item.value}</p>
              </article>
            ))}
          </div>
        </div>

        <aside className="results-side">
          <article className="panel">
            <div className="panel-head">
              <h2>Top Matches</h2>
              <Link href="/guide">View all</Link>
            </div>
            <div className="match-list">
              {result.top_predictions.map((item, index) => (
                <article className="match-item" key={item.species}>
                  <b>{index + 1}</b>
                  <span>
                    <strong>{item.species}</strong>
                    <small>{getTopMatchScientificName(item.species, result.species, resolvedProfile)}</small>
                  </span>
                  <div className="match-confidence">
                    <div className="mini-bar"><i style={{ width: `${Math.round(item.confidence * 100)}%` }} /></div>
                    <em>{Math.round(item.confidence * 100)}%</em>
                  </div>
                </article>
              ))}
            </div>
          </article>

          <article className="panel observation-card">
            <h2>Observation Info</h2>
            <p><b>Date & Time:</b> {new Date(result.createdAt).toLocaleString()}</p>
            <p><b>Method:</b> {result.method}</p>
            <p><b>Tip:</b> {result.method === "Sound" ? "Use low background noise" : "Use a clear bird image"}</p>
          </article>

          <Link className="primary-link full-width" href="/identify">
            <RotateCcw size={17} /> New Search
          </Link>
        </aside>
      </section>
    </main>
  );
}

function buildFacts(resolvedProfile: SpeciesProfile | null | undefined, exactProfile: BirdProfile | undefined) {
  return [
    ["Family", resolvedProfile?.family ?? exactProfile?.family],
    ["Order", resolvedProfile?.order ?? exactProfile?.order],
    ["Size", exactProfile?.size],
    ["Status", resolvedProfile?.status ?? exactProfile?.status],
  ].filter((item): item is [string, string] => Boolean(item[1] && item[1] !== "Unknown"));
}

function buildDetails(result: HistoryItem, resolvedProfile: SpeciesProfile | null | undefined, exactProfile: BirdProfile | undefined) {
  const details = [
    ["Details", result.recommendation || resolvedProfile?.description || exactProfile?.description],
    ["Habitat", exactProfile?.habitat],
    ["Diet", exactProfile?.diet],
    ["Distribution", resolvedProfile?.region ?? exactProfile?.region],
    ["Photo", resolvedProfile?.photoAttribution],
  ];

  return details
    .filter((item): item is [string, string] => Boolean(item[1] && item[1] !== "Global records available"))
    .map(([label, value]) => ({ label, value }));
}

function getTopMatchScientificName(species: string, bestSpecies: string, resolvedProfile: SpeciesProfile | null | undefined) {
  if (species === bestSpecies && resolvedProfile?.scientificName) return resolvedProfile.scientificName;
  return findBirdProfile(species)?.scientificName ?? "";
}

function resolveResultImage(src: string) {
  if (src.startsWith("/data/")) return apiUrl(src) ?? src;
  return src;
}

async function downloadReportPdf(result: HistoryItem, resolvedProfile: SpeciesProfile | null | undefined, exactProfile: BirdProfile | undefined) {
  const { jsPDF } = await import("jspdf");
  const pdf = new jsPDF();
  const confidence = Math.round(result.confidence * 100);
  const details = buildDetails(result, resolvedProfile, exactProfile);
  const facts = buildFacts(resolvedProfile, exactProfile);
  const fileName = `${result.species.toLowerCase().replace(/[^a-z0-9]+/g, "-") || "bird"}-report.pdf`;

  pdf.setFont("helvetica", "bold");
  pdf.setFontSize(20);
  pdf.text("Bird Identification Report", 14, 18);

  pdf.setFontSize(15);
  pdf.text(result.species, 14, 34);
  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(11);
  pdf.text(`Scientific Name: ${resolvedProfile?.scientificName ?? exactProfile?.scientificName ?? "Not available"}`, 14, 43);
  pdf.text(`Confidence: ${confidence}%`, 14, 51);
  pdf.text(`Method: ${result.method}`, 14, 59);
  pdf.text(`Date & Time: ${new Date(result.createdAt).toLocaleString()}`, 14, 67);

  let y = 80;
  if (facts.length) {
    pdf.setFont("helvetica", "bold");
    pdf.text("Facts", 14, y);
    y += 8;
    pdf.setFont("helvetica", "normal");
    for (const [label, value] of facts) {
      pdf.text(`${label}: ${value}`, 14, y);
      y += 7;
    }
  }

  y += 4;
  for (const item of details) {
    if (y > 260) {
      pdf.addPage();
      y = 18;
    }
    pdf.setFont("helvetica", "bold");
    pdf.text(item.label, 14, y);
    y += 7;
    pdf.setFont("helvetica", "normal");
    const lines = pdf.splitTextToSize(item.value, 180);
    pdf.text(lines, 14, y);
    y += lines.length * 6 + 6;
  }

  if (result.top_predictions.length) {
    if (y > 230) {
      pdf.addPage();
      y = 18;
    }
    pdf.setFont("helvetica", "bold");
    pdf.text("Top Matches", 14, y);
    y += 8;
    pdf.setFont("helvetica", "normal");
    result.top_predictions.forEach((item, index) => {
      pdf.text(`${index + 1}. ${item.species} - ${Math.round(item.confidence * 100)}%`, 14, y);
      y += 7;
    });
  }

  pdf.save(fileName);
}
