import { Mail, MapPin, Users } from "lucide-react";

export default function ContactPage() {
  return (
    <main className="content-page">
      <section className="page-hero">
        <p className="eyebrow">Contact</p>
        <h1>Project team and support details.</h1>
        <p>Update these placeholders with your real names, emails, and institution details.</p>
      </section>

      <section className="contact-list">
        <article>
          <Users size={24} />
          <div>
            <h2>Development Team</h2>
            <p>Your Name, Your Partner, Your Supervisor</p>
          </div>
        </article>
        <article>
          <Mail size={24} />
          <div>
            <h2>Email</h2>
            <p>yourmail@gmail.com</p>
          </div>
        </article>
        <article>
          <MapPin size={24} />
          <div>
            <h2>Location</h2>
            <p>Your university or department name</p>
          </div>
        </article>
      </section>
    </main>
  );
}
