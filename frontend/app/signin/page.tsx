"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Bird, Lock, Mail } from "lucide-react";
import { isSignedIn, signIn } from "@/lib/auth";

export default function SignInPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (isSignedIn()) router.replace("/");
  }, [router]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (!signIn(email, password)) {
      setError("Invalid email or password.");
      return;
    }

    router.replace("/");
  }

  return (
    <main className="signin-page">
      <section className="signin-panel">
        <div className="signin-brand">
          <Bird size={44} />
          <div>
            <h1>AI Bird</h1>
            <p>Species Detection & Classification</p>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <h2>Sign in</h2>
          <p>Use your FYP account to access the dashboard.</p>

          <label>
            <span>Email</span>
            <div>
              <Mail size={18} />
              <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" placeholder="Enter email" autoComplete="email" />
            </div>
          </label>

          <label>
            <span>Password</span>
            <div>
              <Lock size={18} />
              <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" placeholder="Enter password" autoComplete="current-password" />
            </div>
          </label>

          {error && <strong className="signin-error">{error}</strong>}

          <button className="full-button" type="submit">Sign in</button>
        </form>
      </section>
    </main>
  );
}
