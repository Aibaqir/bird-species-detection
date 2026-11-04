"use client";

import { ChangeEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  Camera,
  Check,
  Crosshair,
  ImageIcon,
  Loader2,
  Mic,
  UploadCloud,
} from "lucide-react";
import { predictAudio, predictBird } from "@/lib/api";
import { saveHistoryItem } from "@/lib/history";

type Mode = "image" | "sound" | "camera";

export default function IdentifyPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("image");
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioProcessorRef = useRef<ScriptProcessorNode | null>(null);
  const audioSourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const audioStreamRef = useRef<MediaStream | null>(null);
  const audioSamplesRef = useRef<Float32Array[]>([]);

  useEffect(() => {
    const requestedMode = new URLSearchParams(window.location.search).get("mode") as Mode | null;
    if (requestedMode && ["image", "sound", "camera"].includes(requestedMode)) {
      setMode(requestedMode);
    }

    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      if (audioUrl) URL.revokeObjectURL(audioUrl);
      stopCamera();
      stopAudioTracks();
    };
  }, []);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const nextFile = event.target.files?.[0] ?? null;
    setFile(nextFile);
    setError(null);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(nextFile ? URL.createObjectURL(nextFile) : null);
  }

  async function runImagePrediction(sourceFile = file, method: "Image" | "Camera" = "Image") {
    if (!sourceFile) {
      setError("Choose or capture a bird image first.");
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const result = await predictBird(sourceFile, method);
      const persistentPreview = await fileToHistoryPreview(sourceFile);
      const item = {
        ...result,
        id: result.id ?? crypto.randomUUID(),
        method: result.method ?? method,
        createdAt: result.createdAt ?? result.created_at ?? new Date().toISOString(),
        previewUrl: result.previewUrl ?? result.thumbnail_url ?? result.image_url ?? persistentPreview ?? previewUrl ?? undefined,
      };
      saveHistoryItem(item);
      router.push("/results");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Prediction failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }

  async function startCamera() {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setCameraReady(true);
      }
    } catch {
      setError("Camera access was blocked or no camera was found.");
    }
  }

  function stopCamera() {
    const stream = videoRef.current?.srcObject as MediaStream | null;
    stream?.getTracks().forEach((track) => track.stop());
    if (videoRef.current) videoRef.current.srcObject = null;
    setCameraReady(false);
  }

  async function captureFrame() {
    const video = videoRef.current;
    if (!video) return;

    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const context = canvas.getContext("2d");
    context?.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(async (blob) => {
      if (!blob) return;
      const capturedFile = new File([blob], "camera-capture.jpg", { type: "image/jpeg" });
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      const nextPreview = URL.createObjectURL(blob);
      setPreviewUrl(nextPreview);
      setFile(capturedFile);
      await runImagePrediction(capturedFile, "Camera");
    }, "image/jpeg", 0.92);
  }

  async function toggleRecording() {
    if (isRecording) {
      await stopRecordingAndPredict();
      return;
    }

    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const audioContext = new AudioContextClass();
      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);

      audioSamplesRef.current = [];
      processor.onaudioprocess = (event) => {
        audioSamplesRef.current.push(new Float32Array(event.inputBuffer.getChannelData(0)));
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      audioStreamRef.current = stream;
      audioContextRef.current = audioContext;
      audioSourceRef.current = source;
      audioProcessorRef.current = processor;
      setIsRecording(true);
    } catch {
      setError("Microphone access was blocked or no microphone was found.");
    }
  }

  async function stopRecordingAndPredict() {
    const audioContext = audioContextRef.current;
    const sampleRate = audioContext?.sampleRate ?? 44100;
    const samples = mergeAudioSamples(audioSamplesRef.current);

    setIsRecording(false);
    stopAudioTracks();

    if (samples.length < sampleRate) {
      setError("Record at least 2 to 5 seconds of a clear bird call.");
      return;
    }

    const audioBlob = encodeWav(samples, sampleRate);
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudioUrl(URL.createObjectURL(audioBlob));
    setIsLoading(true);
    setError(null);

    try {
      const audioFile = new File([audioBlob], "bird-sound.wav", { type: "audio/wav" });
      const result = await predictAudio(audioFile);
      saveHistoryItem({
        ...result,
        id: result.id ?? crypto.randomUUID(),
        method: result.method ?? "Sound",
        createdAt: result.createdAt ?? result.created_at ?? new Date().toISOString(),
      });
      router.push("/results");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Audio recognition failed. Please try a clearer recording.");
    } finally {
      setIsLoading(false);
    }
  }

  function stopAudioTracks() {
    audioProcessorRef.current?.disconnect();
    audioSourceRef.current?.disconnect();
    audioStreamRef.current?.getTracks().forEach((track) => track.stop());
    void audioContextRef.current?.close();

    audioProcessorRef.current = null;
    audioSourceRef.current = null;
    audioStreamRef.current = null;
    audioContextRef.current = null;
  }

  return (
    <main className="page">
      <div className="page-title">
        <div>
          <h1>Identify Bird</h1>
          <p>Choose one input method and let the AI predict the bird species.</p>
        </div>
      </div>

      <section className="identify-layout">
        <div className="identify-main panel">
          <div className="tabs">
            <button className={mode === "image" ? "active" : ""} onClick={() => setMode("image")} type="button">
              <ImageIcon size={18} /> Image
            </button>
            <button className={mode === "sound" ? "active" : ""} onClick={() => setMode("sound")} type="button">
              <Mic size={18} /> Sound
            </button>
            <button className={mode === "camera" ? "active" : ""} onClick={() => setMode("camera")} type="button">
              <Camera size={18} /> Camera
            </button>
          </div>

          {mode === "image" && (
            <>
              <label className="smart-drop" htmlFor="bird-image">
                <input id="bird-image" type="file" accept="image/png,image/jpeg,image/webp" onChange={handleFileChange} />
                {previewUrl ? <img src={previewUrl} alt="Selected bird preview" /> : <UploadCloud size={58} />}
                <strong>{file ? file.name : "Click to choose a bird image"}</strong>
                <span>Use a clear JPG, PNG, or WEBP photo</span>
              </label>
              <button className="full-button" onClick={() => runImagePrediction()} disabled={isLoading} type="button">
                {isLoading ? <Loader2 className="spin" size={18} /> : <Crosshair size={18} />}
                Identify Bird
              </button>
            </>
          )}

          {mode === "camera" && (
            <div className="camera-panel">
              <video ref={videoRef} autoPlay playsInline muted />
              <div className="button-row">
                <button type="button" onClick={cameraReady ? stopCamera : startCamera}>
                  <Camera size={18} /> {cameraReady ? "Stop Camera" : "Start Camera"}
                </button>
                <button type="button" onClick={captureFrame} disabled={!cameraReady || isLoading}>
                  {isLoading ? <Loader2 className="spin" size={18} /> : <Crosshair size={18} />}
                  Capture & Identify
                </button>
              </div>
            </div>
          )}

          {mode === "sound" && (
            <div className="sound-panel">
              <Mic size={54} />
              <h2>{isLoading ? "Analyzing sound..." : isRecording ? "Recording..." : "Record bird sound"}</h2>
              <p>Record a short, clear bird call with little background noise.</p>
              {audioUrl && <audio src={audioUrl} controls />}
              <button className="full-button" type="button" onClick={toggleRecording} disabled={isLoading}>
                {isLoading ? <Loader2 className="spin" size={18} /> : <Mic size={18} />}
                {isLoading ? "Analyzing sound..." : isRecording ? "Stop Recording" : "Start Recording"}
              </button>
            </div>
          )}

          {error && (
            <div className="notice error">
              <AlertCircle size={18} />
              {error}
            </div>
          )}

          <div className="tips-card">
            <h3>For best results</h3>
            <div>
              {["Use a clear photo", "Keep the bird in focus", "Show the full bird", "Avoid dark or blurry images"].map((tip) => (
                <span key={tip}><Check size={16} /> {tip}</span>
              ))}
            </div>
          </div>
        </div>

        <aside className="identify-side">
          <article className="panel">
            <h2>Demo Flow</h2>
            <ol className="steps">
              <li><b>1</b><span>Select image, camera, or sound</span></li>
              <li><b>2</b><span>Submit it to the AI model</span></li>
              <li><b>3</b><span>View prediction and confidence</span></li>
            </ol>
          </article>

          <article className="panel">
            <h2>What the result shows</h2>
            <ol className="steps">
              <li><b>1</b><span>Predicted bird name</span></li>
              <li><b>2</b><span>Confidence percentage</span></li>
              <li><b>3</b><span>Top matching species</span></li>
            </ol>
          </article>
        </aside>
      </section>
    </main>
  );
}

function mergeAudioSamples(chunks: Float32Array[]) {
  const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const merged = new Float32Array(totalLength);
  let offset = 0;

  for (const chunk of chunks) {
    merged.set(chunk, offset);
    offset += chunk.length;
  }

  return merged;
}

function encodeWav(samples: Float32Array, sampleRate: number) {
  const bytesPerSample = 2;
  const buffer = new ArrayBuffer(44 + samples.length * bytesPerSample);
  const view = new DataView(buffer);

  writeAscii(view, 0, "RIFF");
  view.setUint32(4, 36 + samples.length * bytesPerSample, true);
  writeAscii(view, 8, "WAVE");
  writeAscii(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * bytesPerSample, true);
  view.setUint16(32, bytesPerSample, true);
  view.setUint16(34, 16, true);
  writeAscii(view, 36, "data");
  view.setUint32(40, samples.length * bytesPerSample, true);

  let offset = 44;
  for (const sample of samples) {
    const clamped = Math.max(-1, Math.min(1, sample));
    view.setInt16(offset, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
    offset += bytesPerSample;
  }

  return new Blob([view], { type: "audio/wav" });
}

function writeAscii(view: DataView, offset: number, value: string) {
  for (let index = 0; index < value.length; index += 1) {
    view.setUint8(offset + index, value.charCodeAt(index));
  }
}

async function fileToHistoryPreview(file: File) {
  if (!file.type.startsWith("image/")) return undefined;

  try {
    const bitmap = await createImageBitmap(file);
    const maxSize = 420;
    const scale = Math.min(1, maxSize / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(bitmap.width * scale));
    canvas.height = Math.max(1, Math.round(bitmap.height * scale));
    const context = canvas.getContext("2d");
    context?.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close();
    return canvas.toDataURL("image/jpeg", 0.82);
  } catch {
    return new Promise<string | undefined>((resolve) => {
      const reader = new FileReader();
      reader.onload = () => resolve(typeof reader.result === "string" ? reader.result : undefined);
      reader.onerror = () => resolve(undefined);
      reader.readAsDataURL(file);
    });
  }
}
