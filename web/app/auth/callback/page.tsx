"use client";

import { useEffect } from "react";
import { useState } from "react";
import { getSupabaseClient } from "../../../lib/supabase";

export default function AuthCallbackPage() {
  const [recovery, setRecovery] = useState(false);
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const supabase = getSupabaseClient();
    if (!supabase) {
      window.location.replace("/login");
      return;
    }
    const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    if (hashParams.get("type") === "recovery") setRecovery(true);
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event) => {
      if (event === "PASSWORD_RECOVERY") setRecovery(true);
    });
    void supabase.auth.getSession().then(({ data: { session } }) => {
      if (hashParams.get("type") !== "recovery" && session) window.location.replace("/");
    });
    return () => subscription.unsubscribe();
  }, []);

  async function updatePassword() {
    const supabase = getSupabaseClient();
    if (!supabase) return;
    setError("");
    setMessage("");
    if (password.length < 6) {
      setError("Use a password with at least 6 characters.");
      return;
    }
    const { error: updateError } = await supabase.auth.updateUser({ password });
    if (updateError) setError(updateError.message);
    else {
      setMessage("Password updated. Redirecting to FINN…");
      window.setTimeout(() => window.location.replace("/"), 800);
    }
  }

  return <main className="auth-shell"><section className="auth-card"><div className="brand auth-brand"><span className="brand-mark">F</span><span>FINN</span></div>{recovery ? <><p className="section-kicker">ACCOUNT SECURITY</p><h1>Choose a new password</h1><p className="auth-subtitle">Set a new password for your FINN account.</p><div className="auth-form"><label>New password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} minLength={6} autoComplete="new-password" /></label><button className="primary-button auth-submit" onClick={() => void updatePassword()}>Update password<span>→</span></button></div>{error && <div className="auth-error">{error}</div>}{message && <div className="auth-message">{message}</div>}</> : <p className="auth-subtitle">Finishing your secure sign-in…</p>}</section></main>;
}
