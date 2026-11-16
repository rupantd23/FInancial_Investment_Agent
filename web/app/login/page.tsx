"use client";

import { FormEvent, useEffect, useState } from "react";
import { getSupabaseClient } from "../../lib/supabase";

export default function LoginPage() {
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const supabase = getSupabaseClient();
    if (!supabase) return;
    void supabase.auth.getSession().then(({ data }) => {
      if (data.session) window.location.replace("/");
    });
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    const supabase = getSupabaseClient();
    if (!supabase) {
      setError("Supabase Auth is not configured. Add the NEXT_PUBLIC_SUPABASE values to web/.env.local.");
      setBusy(false);
      return;
    }

    const result = mode === "signin"
      ? await supabase.auth.signInWithPassword({ email, password })
      : await supabase.auth.signUp({ email, password });

    if (result.error) {
      setError(result.error.message);
    } else if (mode === "signup" && !result.data.session) {
      setMessage("Account created. Check your email to confirm it, then sign in.");
    } else {
      window.location.replace("/");
    }
    setBusy(false);
  }

  async function resetPassword() {
    setError("");
    setMessage("");
    const supabase = getSupabaseClient();
    if (!supabase) {
      setError("Supabase Auth is not configured yet.");
      return;
    }
    if (!email.trim()) {
      setError("Enter your email address first.");
      return;
    }
    const { error: resetError } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/auth/callback`,
    });
    if (resetError) setError(resetError.message);
    else setMessage("If that account exists, a password-reset email is on its way.");
  }

  return (
    <main className="auth-shell">
      <section className="auth-card">
        <div className="brand auth-brand"><span className="brand-mark">F</span><span>FINN</span></div>
        <p className="section-kicker">PRIVATE INVESTOR WORKSPACE</p>
        <h1>{mode === "signin" ? "Welcome back" : "Create your FINN account"}</h1>
        <p className="auth-subtitle">Keep your research workspace and network context private to you.</p>
        <form onSubmit={submit} className="auth-form">
          <label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required /></label>
          <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete={mode === "signin" ? "current-password" : "new-password"} minLength={6} required /></label>
          <button className="primary-button auth-submit" type="submit" disabled={busy}>{busy ? "Working…" : mode === "signin" ? "Sign in" : "Create account"}<span>→</span></button>
        </form>
        {mode === "signin" && <button className="text-button auth-reset" onClick={() => void resetPassword()}>Forgot password?</button>}
        {error && <div className="auth-error">{error}</div>}
        {message && <div className="auth-message">{message}</div>}
        <div className="auth-switch">
          <span>{mode === "signin" ? "New to FINN?" : "Already have an account?"}</span>
          <button className="text-button" onClick={() => { setMode(mode === "signin" ? "signup" : "signin"); setError(""); setMessage(""); }}>{mode === "signin" ? "Create an account" : "Sign in"}</button>
        </div>
      </section>
    </main>
  );
}
