import { BrainCircuit, ImageIcon, Server } from "lucide-react";

const items = [
  {
    icon: ImageIcon,
    title: "Image input",
    text: "The frontend previews the selected image immediately before sending it to the API.",
  },
  {
    icon: Server,
    title: "FastAPI service",
    text: "The backend exposes a focused prediction endpoint and returns structured JSON.",
  },
  {
    icon: BrainCircuit,
    title: "Keras model",
    text: "The saved bird classifier runs on 224 x 224 RGB images and maps results to known classes.",
  },
];

export default function AboutPage() {
  return (
    <main className="content-page">
      <section className="page-hero">
        <p className="eyebrow">About the project</p>
        <h1>A cleaner rebuild of the original Django bird classifier.</h1>
        <p>
          This version separates the user experience from the machine learning service, making the app
          easier to polish, test, and extend.
        </p>
      </section>

      <section className="feature-grid">
        {items.map((item) => (
          <article key={item.title} className="feature-card">
            <item.icon size={28} />
            <h2>{item.title}</h2>
            <p>{item.text}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
