export default function ObservationsPage() {
  return <Placeholder title="My Observations" text="Observation notes and field records can be added here for FYP expansion." />;
}

function Placeholder({ title, text }: { title: string; text: string }) {
  return <main className="page"><section className="panel placeholder-page"><h1>{title}</h1><p>{text}</p></section></main>;
}
