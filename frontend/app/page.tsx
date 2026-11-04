"use client";

import Image from "next/image";
import Link from "next/link";
import { ArrowRight, Camera, ImageIcon, Mic, TrendingUp } from "lucide-react";
import { birdProfiles } from "@/lib/birds";
import { resolveSpecies } from "@/lib/api";
import { getHistory, updateHistoryItem, type HistoryItem } from "@/lib/history";
import { useEffect, useState } from "react";

export default function DashboardPage() {
  const [historyCount, setHistoryCount] = useState(0);

  useEffect(() => {
    setHistoryCount(getHistory().length);
  }, []);

  return (
    <main className="page">
      <div className="page-title">
        <div>
          <h1>Dashboard</h1>
          <p>A simple demo for identifying bird species from images, camera, and sound.</p>
        </div>
      </div>

      <section className="hero-card">
        <div>
          <h2>AI Bird Species Detection</h2>
          <p>
            Upload a bird image, capture from camera, or record a call. The system predicts the
            species, confidence score, and useful bird details.
          </p>
          <Link className="primary-link" href="/identify">
            Start Demo <ArrowRight size={18} />
          </Link>
        </div>
        <Image src="/images/bird-4.jpg" alt="Bird on a branch" width={320} height={210} priority />
      </section>

      <section className="stats-grid">
        <article>
          <span>Total Identifications</span>
          <strong>{historyCount || 0}</strong>
          <ImageIcon size={22} />
        </article>
        <article>
          <span>Guide Species</span>
          <strong>{birdProfiles.length}</strong>
          <TrendingUp size={22} />
        </article>
        <article>
          <span>Input Methods</span>
          <strong>3</strong>
          <Camera size={22} />
        </article>
        <article>
          <span>Reports</span>
          <strong>PDF</strong>
          <Mic size={22} />
        </article>
      </section>

      <section className="dashboard-grid">
        <article className="panel">
          <div className="panel-head">
            <h2>Recent Identifications</h2>
            <Link href="/history">View all</Link>
          </div>
          <RecentList />
        </article>

        <article className="panel">
          <div className="panel-head">
            <h2>Demo Steps</h2>
          </div>
          <div className="quick-actions">
            <Link href="/identify"><ImageIcon size={20} /> 1. Upload image</Link>
            <Link href="/identify?mode=camera"><Camera size={20} /> 2. Try camera</Link>
            <Link href="/identify?mode=sound"><Mic size={20} /> 3. Record sound</Link>
            <Link href="/guide"><ArrowRight size={20} /> 4. Show bird guide</Link>
          </div>
        </article>
      </section>
    </main>
  );
}

function RecentList() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [brokenImages, setBrokenImages] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const currentItems = getHistory().slice(0, 4);
    setItems(currentItems);

    currentItems
      .filter((item) => !item.profile && !item.previewUrl)
      .forEach((item) => {
        resolveSpecies(item.species)
          .then((profile) => {
            const updated = { ...item, profile };
            updateHistoryItem(updated);
            setItems((existing) => existing.map((entry) => (entry.id === item.id ? updated : entry)));
          })
          .catch(() => undefined);
      });
  }, []);

  if (!items.length) {
    return <p className="empty-copy">No identifications yet. Start with image upload or live camera.</p>;
  }

  return (
    <div className="recent-list">
      {items.map((item) => (
        <div key={item.id}>
          <div className="thumb">
            {getRecentImage(item, brokenImages[item.id]) ? (
              <img
                src={getRecentImage(item, brokenImages[item.id])}
                alt={item.species}
                onError={() => setBrokenImages((current) => ({ ...current, [item.id]: true }))}
              />
            ) : (
              <ImageIcon size={20} />
            )}
          </div>
          <span>
            <strong>{item.species}</strong>
            <small>{item.method} identification</small>
          </span>
          <b>{Math.round(item.confidence * 100)}%</b>
        </div>
      ))}
    </div>
  );
}

function getRecentImage(item: HistoryItem, isPreviewBroken?: boolean) {
  if (!isPreviewBroken && item.previewUrl) return item.previewUrl;
  return item.profile?.thumbnailUrl ?? item.profile?.imageUrl ?? "";
}
