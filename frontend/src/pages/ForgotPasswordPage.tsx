import { ArrowLeft, Check, KeyRound, Mail, ShieldCheck, Zap } from "lucide-react";
import { FormEvent, useState } from "react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { api, clearTokens } from "../api/client";

const passwordChecks = [
  ["10+ characters", (value: string) => value.length >= 10],
  ["Lowercase", (value: string) => /[a-z]/.test(value)],
  ["Uppercase", (value: string) => /[A-Z]/.test(value)],
  ["Number", (value: string) => /\d/.test(value)]
] as const;

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [sent, setSent] = useState(false);
  const [complete, setComplete] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [developmentUrl, setDevelopmentUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const passwordStrong = passwordChecks.every(([, check]) => check(password));

  async function requestReset(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await api.forgotPassword(email);
      setMessage(result.message);
      setDevelopmentUrl(result.verification_url);
      setSent(true);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to send reset email.");
    } finally {
      setBusy(false);
    }
  }

  async function resetWithCode(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!passwordStrong) {
      setError("Password does not meet all requirements.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      const result = await api.resetPasswordCode(email, code, password);
      clearTokens();
      setMessage(result.message);
      setComplete(true);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to reset password.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthRecoveryLayout>
      {complete ? (
        <div className="recovery-complete">
          <span><ShieldCheck size={26} /></span>
          <h1>Password changed</h1>
          <p>{message}</p>
          <a className="recovery-primary-link" href="/login">Sign in</a>
        </div>
      ) : !sent ? (
        <>
          <header><h1>Forgot password?</h1><p>Enter your account email and we will send a secure reset link and code.</p></header>
          <form className="recovery-form" onSubmit={requestReset}>
            <label>Email<span className="auth-input"><Mail size={17} /><input autoComplete="email" required type="email" value={email} onChange={(event) => setEmail(event.target.value)} /></span></label>
            {error && <div className="alert">{error}</div>}
            <button disabled={busy}><Mail size={16} />{busy ? "Sending..." : "Send reset instructions"}</button>
          </form>
          <Link className="recovery-back-link" to="/login"><ArrowLeft size={14} />Back to sign in</Link>
        </>
      ) : (
        <>
          <header><h1>Check your email</h1><p>{message}</p></header>
          {developmentUrl && <a className="development-reset-link" href={developmentUrl}>Open development reset link</a>}
          <div className="verification-divider"><span>or use the code</span></div>
          <form className="recovery-form" onSubmit={resetWithCode}>
            <label>Six-digit code<span className="auth-input"><ShieldCheck size={17} /><input autoComplete="one-time-code" inputMode="numeric" maxLength={6} pattern="\d{6}" placeholder="000000" required value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))} /></span></label>
            <label>New password<span className="auth-input"><KeyRound size={17} /><input autoComplete="new-password" required type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></span></label>
            <div className="password-check-list recovery-password-checks">
              {passwordChecks.map(([label, check]) => <span className={check(password) ? "met" : ""} key={label}><Check size={12} />{label}</span>)}
            </div>
            <label>Confirm password<span className="auth-input"><KeyRound size={17} /><input autoComplete="new-password" required type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} /></span></label>
            {error && <div className="alert">{error}</div>}
            <button disabled={busy || code.length !== 6 || !passwordStrong || password !== confirmPassword}>{busy ? "Resetting..." : "Reset password"}</button>
          </form>
          <button className="recovery-resend" disabled={busy} onClick={() => {
            setSent(false);
            setCode("");
            setPassword("");
            setConfirmPassword("");
            setError(null);
          }}>Use another email</button>
        </>
      )}
    </AuthRecoveryLayout>
  );
}

export function AuthRecoveryLayout({ children }: { children: ReactNode }) {
  return (
    <main className="recovery-screen">
      <Link className="brand recovery-brand" to="/login"><span className="brand-mark"><Zap size={19} fill="currentColor" /></span><strong>Momentum</strong></Link>
      <section className="recovery-panel">{children}</section>
    </main>
  );
}
